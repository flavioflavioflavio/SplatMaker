"""
Export — PLY/SPLAT export from trained model.
Sprint 2: checks for ns-export, creates export artifacts info.
"""
import asyncio
import subprocess
import shutil
import json
from pathlib import Path
from config import settings


async def export_splat(project_id: str, config, progress_callback):
    """Export trained model to .ply and/or .splat format."""
    proj_dir = Path(settings.projects_dir) / project_id
    output_dir = proj_dir / "output"
    export_dir = proj_dir / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    
    await progress_callback(10, "Preparing export...")
    
    # Check for nerfstudio export
    ns_export = shutil.which("ns-export")
    
    # Look for trained model config
    config_path = None
    for yml in output_dir.rglob("config.yml"):
        config_path = yml
        break
    
    if ns_export and config_path:
        await progress_callback(20, "Exporting Gaussian Splat via ns-export...")
        
        cmd = [
            ns_export, "gaussian-splat",
            "--load-config", str(config_path),
            "--output-dir", str(export_dir),
        ]
        
        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True, timeout=600
        )
        
        if result.returncode != 0:
            await progress_callback(50, f"ns-export warning: {result.stderr[:200]}")
        else:
            await progress_callback(80, "Export successful")
    else:
        # No trained model or ns-export not available
        await progress_callback(30, "No trained model found — creating export summary...")
        
        # Generate an export summary with project info
        summary = {
            "project_id": project_id,
            "status": "pending_training",
            "note": "Complete the training step to generate exportable splat files.",
        }
        
        # Check what data we have
        transforms_path = proj_dir / "transforms.json"
        if transforms_path.exists():
            with open(transforms_path) as f:
                transforms = json.load(f)
            summary["camera_poses"] = len(transforms.get("frames", []))
        
        split_dir = proj_dir / "split"
        if split_dir.exists():
            summary["perspective_views"] = len(list(split_dir.glob("*.jpg")))
        
        frames_dir = proj_dir / "frames"
        if frames_dir.exists():
            summary["source_frames"] = len(list(frames_dir.glob("*.jpg")))
        
        with open(export_dir / "export_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        await progress_callback(80, "Export summary generated")
    
    # List all exportable files
    ply_files = list(export_dir.glob("*.ply"))
    splat_files = list(export_dir.glob("*.splat"))
    
    ply_path = str(ply_files[0]) if ply_files else None
    splat_path = str(splat_files[0]) if splat_files else None
    
    await progress_callback(100, "Export complete")
    
    return {
        "ply_path": ply_path,
        "splat_path": splat_path,
        "export_dir": str(export_dir),
        "has_model": bool(ply_files or splat_files),
    }
