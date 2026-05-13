"""
Equirectangular → Perspective Split — converts 360° frames into multiple pinhole views.
"""
import numpy as np
from PIL import Image
from pathlib import Path
from config import settings
import math


VIEWS = [
    {"yaw": 0,   "pitch": 0, "name": "front"},
    {"yaw": 45,  "pitch": 0, "name": "front_right"},
    {"yaw": 90,  "pitch": 0, "name": "right"},
    {"yaw": 135, "pitch": 0, "name": "back_right"},
    {"yaw": 180, "pitch": 0, "name": "back"},
    {"yaw": 225, "pitch": 0, "name": "back_left"},
    {"yaw": 270, "pitch": 0, "name": "left"},
    {"yaw": 315, "pitch": 0, "name": "front_left"},
]


def equirect_to_perspective(equirect: np.ndarray, yaw_deg: float, pitch_deg: float,
                            fov_deg: float = 90, out_size: int = 800) -> np.ndarray:
    """Sample a perspective view from an equirectangular image."""
    h, w = equirect.shape[:2]
    
    fov = math.radians(fov_deg)
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    
    # Create perspective image pixel grid
    f = out_size / (2 * math.tan(fov / 2))
    
    u = np.arange(out_size) - out_size / 2
    v = np.arange(out_size) - out_size / 2
    uu, vv = np.meshgrid(u, v)
    
    # Direction vectors in camera space
    x = uu
    y = -vv
    z = np.full_like(uu, f, dtype=np.float64)
    
    # Normalize
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
    
    # Convert to equirectangular coordinates
    theta = np.arctan2(x, z)  # longitude
    phi = np.arcsin(np.clip(y, -1, 1))  # latitude
    
    # Map to pixel coordinates
    px = ((theta / math.pi + 1) / 2 * w).astype(np.float32)
    py = ((0.5 - phi / math.pi) * h).astype(np.float32)
    
    # Clamp
    px = np.clip(px, 0, w - 1).astype(int)
    py = np.clip(py, 0, h - 1).astype(int)
    
    return equirect[py, px]


async def split_to_perspective(project_id: str, config, progress_callback):
    """Split equirectangular frames into perspective views."""
    frames_dir = Path(settings.projects_dir) / project_id / "frames"
    output_dir = Path(settings.projects_dir) / project_id / "split"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    views = VIEWS[:config.views_per_frame] if config.views_per_frame < len(VIEWS) else VIEWS
    
    frames = sorted(frames_dir.glob("*.jpg"))
    total = len(frames) * len(views)
    count = 0
    
    for frame_path in frames:
        img = np.array(Image.open(frame_path))
        
        # Apply crop (top/bottom)
        if config.crop_top_bottom > 0:
            h = img.shape[0]
            crop_px = int(h * config.crop_top_bottom)
            img = img[crop_px:h - crop_px]
        
        frame_name = frame_path.stem
        
        for view in views:
            persp = equirect_to_perspective(
                img, view["yaw"], view["pitch"],
                fov_deg=90, out_size=800
            )
            
            out_path = output_dir / f"{frame_name}_{view['name']}.jpg"
            Image.fromarray(persp).save(str(out_path), quality=95)
            
            count += 1
            pct = int(count / total * 100)
            if count % max(1, total // 20) == 0:
                await progress_callback(pct, f"Splitting: {count}/{total} views")
    
    total_images = len(list(output_dir.glob("*.jpg")))
    await progress_callback(100, f"Generated {total_images} perspective views")
    
    return {"image_count": total_images, "output_dir": str(output_dir)}
