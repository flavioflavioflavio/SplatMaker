"""
Export — PLY/SPLAT export from trained model.
Stub implementation for Sprint 1.
"""
from pathlib import Path
from config import settings


async def export_splat(project_id: str, config, progress_callback):
    """Export trained model to .ply and/or .splat format."""
    output_dir = Path(settings.projects_dir) / project_id / "output"
    export_dir = Path(settings.projects_dir) / project_id / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # TODO: Full ns-export integration
    # cmd = [
    #     "ns-export", "gaussian-splat",
    #     "--load-config", str(output_dir / "config.yml"),
    #     "--output-dir", str(export_dir)
    # ]
    
    await progress_callback(50, "Exporting splat file (stub)...")
    await progress_callback(100, "Export complete (stub)")
    
    ply_path = str(export_dir / "splat.ply")
    
    return {
        "ply_path": ply_path,
        "note": "Stub implementation — ns-export integration pending"
    }
