"""
Structure from Motion — GLOMAP (primary) or COLMAP (fallback) for camera pose estimation.
Stub implementation for Sprint 1.
"""
import subprocess
from pathlib import Path
from config import settings


async def run_sfm(project_id: str, config, progress_callback):
    """Run SfM pipeline (GLOMAP or COLMAP) for camera pose estimation."""
    image_dir = Path(settings.projects_dir) / project_id / "split"
    db_path = Path(settings.projects_dir) / project_id / "database.db"
    sparse_dir = Path(settings.projects_dir) / project_id / "sparse"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    
    engine = config.sfm_engine
    
    # TODO: Full COLMAP/GLOMAP integration
    # For Sprint 1, this is a structured stub showing the command sequence
    
    await progress_callback(10, f"SfM ({engine}): Feature extraction...")
    
    # Step 1: Feature extraction via COLMAP
    # cmd = [settings.colmap_path, "feature_extractor",
    #     "--database_path", str(db_path),
    #     "--image_path", str(image_dir),
    #     "--ImageReader.camera_model", "PINHOLE",
    #     "--ImageReader.single_camera", "0"]
    
    await progress_callback(40, f"SfM ({engine}): Feature matching...")
    
    # Step 2: Sequential matching
    # cmd = [settings.colmap_path, "sequential_matcher",
    #     "--database_path", str(db_path)]
    
    await progress_callback(70, f"SfM ({engine}): Reconstruction...")
    
    # Step 3: Mapper (GLOMAP or COLMAP)
    # if engine == "glomap":
    #     cmd = [settings.glomap_path, "mapper", ...]
    # else:
    #     cmd = [settings.colmap_path, "mapper", ...]
    
    await progress_callback(100, f"SfM ({engine}) complete (stub)")
    
    return {
        "sparse_dir": str(sparse_dir),
        "engine": engine,
        "note": "Stub implementation — COLMAP/GLOMAP integration pending"
    }
