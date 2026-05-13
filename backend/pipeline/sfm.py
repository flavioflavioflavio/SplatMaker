"""
Structure from Motion — generates camera poses for Gaussian Splat training.

For equirectangular 360° input, we use SYNTHETIC poses derived from the known
split angles (yaw/pitch). This is more accurate than COLMAP for controlled
equirectangular captures because the camera geometry is known exactly.

For non-360 input, COLMAP or GLOMAP can be used as a fallback.
"""
import asyncio
import subprocess
import json
import shutil
from pathlib import Path
from config import settings


async def run_sfm(project_id: str, config, progress_callback):
    """Run Structure from Motion or verify synthetic camera poses."""
    proj_dir = Path(settings.projects_dir) / project_id
    image_dir = proj_dir / "split"
    sparse_dir = proj_dir / "sparse"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    transforms_path = proj_dir / "transforms.json"
    
    engine = config.sfm_engine
    
    # Check if we already have synthetic transforms from the split step
    if transforms_path.exists():
        await progress_callback(10, "Found synthetic transforms.json from equirect split...")
        
        with open(transforms_path) as f:
            transforms = json.load(f)
        
        frame_count = len(transforms.get("frames", []))
        await progress_callback(30, f"Validating {frame_count} camera poses...")
        
        # Verify all referenced images exist
        missing = 0
        for frame in transforms["frames"]:
            img_path = proj_dir / frame["file_path"]
            if not img_path.exists():
                missing += 1
        
        if missing > 0:
            await progress_callback(50, f"Warning: {missing} referenced images not found")
        
        # Create COLMAP-compatible sparse model if needed
        await progress_callback(60, "Generating Nerfstudio-compatible data structure...")
        
        # Build the processed directory structure for nerfstudio
        processed_dir = proj_dir / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy transforms.json to processed dir
        proc_transforms = processed_dir / "transforms.json"
        shutil.copy2(str(transforms_path), str(proc_transforms))
        
        # Symlink or copy images to processed/split/
        proc_images = processed_dir / "split"
        if not proc_images.exists():
            # On Windows, use copy instead of symlink (requires admin)
            shutil.copytree(str(image_dir), str(proc_images), dirs_exist_ok=True)
        
        await progress_callback(90, f"Camera poses ready: {frame_count} frames, synthetic (equirect)")
        await progress_callback(100, f"SfM complete: {frame_count} synthetic camera poses")
        
        return {
            "sparse_dir": str(sparse_dir),
            "transforms_path": str(proc_transforms),
            "engine": "synthetic_equirect",
            "frame_count": frame_count,
            "missing_images": missing,
        }
    
    # Fallback: Run COLMAP/GLOMAP for non-equirect input
    await progress_callback(10, f"SfM ({engine}): No synthetic transforms found, running {engine}...")
    
    colmap_bin = shutil.which("colmap")
    if not colmap_bin and engine == "colmap":
        raise RuntimeError(
            "COLMAP not found. Install COLMAP or use equirectangular input "
            "(which generates synthetic camera poses automatically)."
        )
    
    db_path = proj_dir / "database.db"
    
    if colmap_bin:
        await _run_colmap_pipeline(colmap_bin, str(image_dir), str(db_path), 
                                    str(sparse_dir), engine, progress_callback)
    else:
        raise RuntimeError(
            f"SfM engine '{engine}' not available. "
            "For equirectangular 360° video, synthetic poses are generated automatically. "
            "For other video types, install COLMAP."
        )
    
    # Generate transforms.json from COLMAP output
    await progress_callback(95, "Generating transforms.json from COLMAP...")
    # TODO: colmap_to_nerfstudio conversion
    
    await progress_callback(100, "SfM complete")
    return {
        "sparse_dir": str(sparse_dir),
        "engine": engine,
    }


async def _run_colmap_pipeline(colmap_bin, image_dir, db_path, sparse_dir, engine, progress_callback):
    """Run full COLMAP pipeline: feature extraction → matching → reconstruction."""
    
    # Step 1: Feature extraction
    await progress_callback(15, f"SfM ({engine}): Extracting features...")
    cmd = [
        colmap_bin, "feature_extractor",
        "--database_path", db_path,
        "--image_path", image_dir,
        "--ImageReader.camera_model", "PINHOLE",
        "--ImageReader.single_camera", "0",
        "--SiftExtraction.use_gpu", "1",
    ]
    result = await asyncio.to_thread(
        subprocess.run, cmd, capture_output=True, text=True, timeout=600
    )
    if result.returncode != 0:
        raise RuntimeError(f"COLMAP feature extraction failed: {result.stderr[:500]}")
    
    # Step 2: Feature matching
    await progress_callback(40, f"SfM ({engine}): Matching features...")
    cmd = [
        colmap_bin, "sequential_matcher",
        "--database_path", db_path,
        "--SiftMatching.use_gpu", "1",
    ]
    result = await asyncio.to_thread(
        subprocess.run, cmd, capture_output=True, text=True, timeout=1200
    )
    if result.returncode != 0:
        raise RuntimeError(f"COLMAP matching failed: {result.stderr[:500]}")
    
    # Step 3: Sparse reconstruction
    await progress_callback(70, f"SfM ({engine}): Reconstructing sparse model...")
    
    if engine == "glomap":
        glomap_bin = shutil.which("glomap")
        if glomap_bin:
            cmd = [
                glomap_bin, "mapper",
                "--database_path", db_path,
                "--image_path", image_dir,
                "--output_path", sparse_dir,
            ]
        else:
            # Fallback to COLMAP mapper
            cmd = [
                colmap_bin, "mapper",
                "--database_path", db_path,
                "--image_path", image_dir,
                "--output_path", sparse_dir,
            ]
    else:
        cmd = [
            colmap_bin, "mapper",
            "--database_path", db_path,
            "--image_path", image_dir,
            "--output_path", sparse_dir,
        ]
    
    result = await asyncio.to_thread(
        subprocess.run, cmd, capture_output=True, text=True, timeout=3600
    )
    if result.returncode != 0:
        raise RuntimeError(f"COLMAP reconstruction failed: {result.stderr[:500]}")
    
    await progress_callback(90, f"SfM ({engine}): Sparse reconstruction complete")
