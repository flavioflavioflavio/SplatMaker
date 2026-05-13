"""
Equirectangular → Perspective Split — converts 360° frames into multiple pinhole views.
Uses pure NumPy for the reprojection, PIL for I/O. Runs in a thread pool.
"""
import asyncio
import numpy as np
from PIL import Image
from pathlib import Path
from config import settings
import math
import json


# Camera views around the equirectangular sphere
# Each view has a yaw (azimuth), pitch (elevation), and descriptive name
VIEWS_8 = [
    {"yaw": 0,   "pitch": 0,  "name": "front"},
    {"yaw": 45,  "pitch": 0,  "name": "front_right"},
    {"yaw": 90,  "pitch": 0,  "name": "right"},
    {"yaw": 135, "pitch": 0,  "name": "back_right"},
    {"yaw": 180, "pitch": 0,  "name": "back"},
    {"yaw": 225, "pitch": 0,  "name": "back_left"},
    {"yaw": 270, "pitch": 0,  "name": "left"},
    {"yaw": 315, "pitch": 0,  "name": "front_left"},
]

VIEWS_6 = [
    {"yaw": 0,   "pitch": 0,  "name": "front"},
    {"yaw": 60,  "pitch": 0,  "name": "front_right"},
    {"yaw": 120, "pitch": 0,  "name": "right"},
    {"yaw": 180, "pitch": 0,  "name": "back"},
    {"yaw": 240, "pitch": 0,  "name": "left"},
    {"yaw": 300, "pitch": 0,  "name": "front_left"},
]

VIEWS_10 = VIEWS_8 + [
    {"yaw": 0,   "pitch": -30, "name": "up_front"},
    {"yaw": 180, "pitch": -30, "name": "up_back"},
]

VIEWS_MAP = {6: VIEWS_6, 8: VIEWS_8, 10: VIEWS_10}

# Default FOV and output resolution
DEFAULT_FOV = 90
DEFAULT_SIZE = 800


def equirect_to_perspective(equirect: np.ndarray, yaw_deg: float, pitch_deg: float,
                            fov_deg: float = DEFAULT_FOV, out_size: int = DEFAULT_SIZE) -> np.ndarray:
    """Sample a perspective view from an equirectangular image using inverse mapping."""
    h, w = equirect.shape[:2]
    
    fov = math.radians(fov_deg)
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    
    # Focal length in pixels
    f = out_size / (2 * math.tan(fov / 2))
    
    # Create perspective image pixel grid (camera coordinates)
    u = np.arange(out_size, dtype=np.float64) - out_size / 2
    v = np.arange(out_size, dtype=np.float64) - out_size / 2
    uu, vv = np.meshgrid(u, v)
    
    # Direction vectors in camera space (x=right, y=up, z=forward)
    x = uu
    y = -vv
    z = np.full_like(uu, f, dtype=np.float64)
    
    # Normalize to unit sphere
    norm = np.sqrt(x**2 + y**2 + z**2)
    x, y, z = x / norm, y / norm, z / norm
    
    # Rotate by pitch (around x-axis)
    cos_p, sin_p = math.cos(pitch), math.sin(pitch)
    y2 = y * cos_p - z * sin_p
    z2 = y * sin_p + z * cos_p
    y, z = y2, z2
    
    # Rotate by yaw (around y-axis)
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    x2 = x * cos_y + z * sin_y
    z2 = -x * sin_y + z * cos_y
    x, z = x2, z2
    
    # Convert to spherical coordinates (equirectangular mapping)
    theta = np.arctan2(x, z)       # longitude [-π, π]
    phi = np.arcsin(np.clip(y, -1, 1))  # latitude [-π/2, π/2]
    
    # Map to equirectangular pixel coordinates
    px = ((theta / math.pi + 1) / 2 * w).astype(np.float32)
    py = ((0.5 - phi / math.pi) * h).astype(np.float32)
    
    # Clamp (nearest-neighbor sampling)
    px = np.clip(px, 0, w - 1).astype(int)
    py = np.clip(py, 0, h - 1).astype(int)
    
    return equirect[py, px]


def _get_camera_intrinsics(fov_deg: float, out_size: int):
    """Compute camera intrinsic matrix for a perspective view."""
    fov = math.radians(fov_deg)
    f = out_size / (2 * math.tan(fov / 2))
    cx = out_size / 2.0
    cy = out_size / 2.0
    return {"fl_x": f, "fl_y": f, "cx": cx, "cy": cy, "w": out_size, "h": out_size}


def _yaw_pitch_to_c2w(yaw_deg: float, pitch_deg: float):
    """Convert yaw/pitch angles to a 4x4 camera-to-world transform matrix.
    
    This produces the exact camera pose for each perspective view,
    eliminating the need for COLMAP when working with equirectangular source.
    """
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    
    # Rotation: first pitch (around x), then yaw (around y)
    # R = Ry @ Rx
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    
    # Camera-to-world rotation matrix (OpenGL convention: -Z forward)
    R = np.array([
        [cy,      sy * sp,   sy * cp,  ],
        [0,       cp,        -sp,      ],
        [-sy,     cy * sp,   cy * cp,  ],
    ], dtype=np.float64)
    
    # Camera position at origin (all views look outward from center)
    t = np.array([0.0, 0.0, 0.0])
    
    # Build 4x4 transform
    c2w = np.eye(4, dtype=np.float64)
    c2w[:3, :3] = R
    c2w[:3, 3] = t
    
    return c2w.tolist()


def _process_single_frame(frame_path, output_dir, views, crop_factor, fov_deg, out_size):
    """Process a single equirectangular frame into multiple perspective views."""
    img = np.array(Image.open(frame_path))
    
    # Apply top/bottom crop to remove zenith/nadir artifacts
    if crop_factor > 0:
        h = img.shape[0]
        crop_px = int(h * crop_factor)
        img = img[crop_px:h - crop_px]
    
    frame_name = frame_path.stem
    results = []
    
    for view in views:
        persp = equirect_to_perspective(
            img, view["yaw"], view["pitch"],
            fov_deg=fov_deg, out_size=out_size
        )
        
        out_name = f"{frame_name}_{view['name']}.jpg"
        out_path = output_dir / out_name
        Image.fromarray(persp).save(str(out_path), quality=95)
        
        results.append({
            "file": out_name,
            "yaw": view["yaw"],
            "pitch": view["pitch"],
            "frame": frame_name,
        })
    
    return results


async def split_to_perspective(project_id: str, config, progress_callback):
    """Split equirectangular frames into perspective views (async with thread pool)."""
    frames_dir = Path(settings.projects_dir) / project_id / "frames"
    output_dir = Path(settings.projects_dir) / project_id / "split"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    views = VIEWS_MAP.get(config.views_per_frame, VIEWS_8)
    fov_deg = DEFAULT_FOV
    out_size = DEFAULT_SIZE
    
    frames = sorted(frames_dir.glob("*.jpg"))
    total_frames = len(frames)
    
    if total_frames == 0:
        raise RuntimeError("No frames found to split. Run extraction first.")
    
    total_images = total_frames * len(views)
    all_results = []
    
    await progress_callback(1, f"Splitting {total_frames} frames × {len(views)} views...")
    
    for i, frame_path in enumerate(frames):
        results = await asyncio.to_thread(
            _process_single_frame, frame_path, output_dir, views,
            config.crop_top_bottom, fov_deg, out_size
        )
        all_results.extend(results)
        
        pct = int((i + 1) / total_frames * 95) + 2
        if (i + 1) % max(1, total_frames // 10) == 0 or i == total_frames - 1:
            await progress_callback(pct, f"Splitting: {i+1}/{total_frames} frames ({len(all_results)} views)")
    
    # Generate transforms.json with synthetic camera poses
    intrinsics = _get_camera_intrinsics(fov_deg, out_size)
    transforms = {
        "camera_model": "OPENCV",
        **intrinsics,
        "frames": [],
    }
    
    for r in all_results:
        c2w = _yaw_pitch_to_c2w(r["yaw"], r["pitch"])
        transforms["frames"].append({
            "file_path": f"./split/{r['file']}",
            "transform_matrix": c2w,
        })
    
    # Save transforms.json to project root (Nerfstudio format)
    transforms_path = Path(settings.projects_dir) / project_id / "transforms.json"
    with open(transforms_path, "w") as f:
        json.dump(transforms, f, indent=2)
    
    total_written = len(list(output_dir.glob("*.jpg")))
    await progress_callback(100, f"Generated {total_written} views + transforms.json")
    
    return {
        "image_count": total_written,
        "output_dir": str(output_dir),
        "transforms_path": str(transforms_path),
        "views_per_frame": len(views),
    }
