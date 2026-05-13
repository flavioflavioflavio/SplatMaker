"""
Masking — SAM2 + YOLO for automatic object masking (tripod, operator removal).
Stub implementation for Sprint 1 — will be fully implemented with SAM2 in Sprint 4.
"""
from pathlib import Path
from config import settings


async def run_masking(project_id: str, config, progress_callback):
    """Run masking on split images. Currently a pass-through stub."""
    split_dir = Path(settings.projects_dir) / project_id / "split"
    masks_dir = Path(settings.projects_dir) / project_id / "masks"
    masks_dir.mkdir(parents=True, exist_ok=True)
    
    if config.mask_mode == "none":
        await progress_callback(100, "Masking skipped (mode: none)")
        return {"mask_count": 0, "mode": "none", "output_dir": str(masks_dir)}
    
    # TODO: Implement SAM2 + YOLO masking
    # For now, pass through without masking
    images = list(split_dir.glob("*.jpg"))
    total = len(images)
    
    await progress_callback(50, f"Masking: {total} images (stub — pass-through)")
    await progress_callback(100, f"Masking complete (stub): {total} images")
    
    return {
        "mask_count": 0,
        "mode": config.mask_mode,
        "output_dir": str(masks_dir),
        "note": "Stub implementation — SAM2 integration pending"
    }
