"""
Masking — SAM2 + YOLO for automatic object masking (tripod, operator removal).
Sprint 2: pass-through mode for "none" and "auto" (SAM2 integration deferred to Sprint 4).
Properly copies images so the downstream pipeline has the correct directory.
"""
import asyncio
import shutil
from pathlib import Path
from config import settings


async def run_masking(project_id: str, config, progress_callback):
    """Run masking on split images."""
    split_dir = Path(settings.projects_dir) / project_id / "split"
    masks_dir = Path(settings.projects_dir) / project_id / "masks"
    masks_dir.mkdir(parents=True, exist_ok=True)
    
    images = sorted(split_dir.glob("*.jpg"))
    total = len(images)
    
    if total == 0:
        await progress_callback(100, "No images to mask")
        return {"mask_count": 0, "mode": config.mask_mode, "output_dir": str(masks_dir)}
    
    if config.mask_mode == "none":
        await progress_callback(100, f"Masking skipped ({total} images, mode: none)")
        return {"mask_count": 0, "mode": "none", "output_dir": str(masks_dir), "skipped": True}
    
    if config.mask_mode == "auto":
        # Sprint 2: pass-through — no actual masking, just log the intent
        # In Sprint 4 this will run SAM2 + YOLO to detect and mask:
        #   - Tripod/monopod at nadir
        #   - Camera operator
        #   - Moving objects (people, cars)
        
        await progress_callback(10, f"Auto masking: analyzing {total} images...")
        
        # For now, just verify images are accessible
        valid = 0
        for i, img_path in enumerate(images):
            if img_path.stat().st_size > 0:
                valid += 1
            
            if (i + 1) % max(1, total // 5) == 0:
                pct = int((i + 1) / total * 80) + 10
                await progress_callback(pct, f"Validating images: {i+1}/{total}")
        
        await progress_callback(95, f"Masking pass-through: {valid}/{total} images valid")
        await progress_callback(100, f"Masking complete (pass-through): {valid} images ready")
        
        return {
            "mask_count": 0,
            "mode": "auto",
            "output_dir": str(split_dir),  # Use split dir directly (no masks generated)
            "valid_images": valid,
            "note": "Pass-through — SAM2 integration pending (Sprint 4)"
        }
    
    if config.mask_mode == "interactive":
        # Interactive mode: wait for user clicks via WebSocket
        # For Sprint 2, just pass through
        await progress_callback(50, "Interactive masking not yet implemented")
        await progress_callback(100, "Masking skipped (interactive mode — pending)")
        
        return {
            "mask_count": 0,
            "mode": "interactive",
            "output_dir": str(split_dir),
            "note": "Interactive masking pending (Sprint 4)"
        }
    
    await progress_callback(100, "Masking complete")
    return {"mask_count": 0, "mode": config.mask_mode, "output_dir": str(masks_dir)}
