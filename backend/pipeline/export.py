"""
SplatMaker — Export Step
Exports trained model to .ply splat file using nerfstudio ns-export.
"""
import asyncio
import json
import os
import re
import shutil
from pathlib import Path


async def export_splat(project_id: str, config, progress_cb):
    """
    Export the trained Gaussian Splat model to a .ply file.
    
    Looks for the latest nerfstudio checkpoint in {project_dir}/outputs/
    and runs ns-export gaussian-splat to produce a .ply file.
    """
    from config import settings
    project = Path(settings.projects_dir) / project_id
    output_dir = project / "outputs"
    export_dir = project / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    
    await progress_cb(5, "Looking for trained model checkpoint...")
    
    # ── Find the latest config.yml from training ──────────────────────────
    ns_export = shutil.which("ns-export")
    config_yml = _find_config_yml(output_dir)
    
    if ns_export and config_yml:
        await _run_real_export(config_yml, export_dir, progress_cb)
    else:
        if not ns_export:
            await progress_cb(10, "⚠ ns-export not found")
        elif not config_yml:
            await progress_cb(10, "⚠ No training config found in outputs/")
        
        await _generate_summary(project, export_dir, progress_cb)
    
    await progress_cb(100, "Export complete")


async def _run_real_export(config_yml: str, export_dir: Path, progress_cb):
    """Run ns-export gaussian-splat to produce a .ply file."""
    
    await progress_cb(10, "Exporting Gaussian Splat to PLY...")
    
    ply_path = export_dir / "splat.ply"
    
    cmd = [
        "ns-export", "gaussian-splat",
        "--load-config", str(config_yml),
        "--output-dir", str(export_dir),
    ]
    
    await progress_cb(20, f"Running: {' '.join(cmd)}")
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    # Parse export progress
    async for raw in process.stderr:
        line = raw.decode("utf-8", errors="replace").strip()
        if line:
            if "Saving" in line or "Export" in line:
                await progress_cb(60, line)
    
    stdout, _ = await process.communicate()
    returncode = process.returncode
    
    if returncode != 0:
        raise RuntimeError(f"ns-export failed with exit code {returncode}")
    
    # Check output
    ply_files = list(export_dir.glob("*.ply"))
    if ply_files:
        size_mb = ply_files[0].stat().st_size / (1024 * 1024)
        await progress_cb(90, f"Exported: {ply_files[0].name} ({size_mb:.1f} MB)")
    else:
        await progress_cb(90, "Export completed but no PLY file found")


async def _generate_summary(project: Path, export_dir: Path, progress_cb):
    """Generate a project summary when no trained model is available."""
    
    await progress_cb(20, "Generating project summary...")
    
    summary = {
        "project_dir": str(project),
        "status": "partial",
        "available_outputs": {},
    }
    
    # Check what's available
    transforms = project / "transforms.json"
    if transforms.exists():
        with open(transforms) as f:
            data = json.load(f)
        frame_count = len(data.get("frames", []))
        summary["available_outputs"]["transforms"] = {
            "path": str(transforms),
            "frames": frame_count,
            "camera_model": data.get("camera_model", "unknown"),
        }
        await progress_cb(40, f"transforms.json: {frame_count} camera poses")
    
    split_dir = project / "split"
    if split_dir.exists():
        images = list(split_dir.glob("*.jpg"))
        summary["available_outputs"]["split_images"] = {
            "path": str(split_dir),
            "count": len(images),
        }
        await progress_cb(50, f"Perspective views: {len(images)} images")
    
    frames_dir = project / "frames"
    if frames_dir.exists():
        frames = list(frames_dir.glob("*.jpg"))
        summary["available_outputs"]["frames"] = {
            "path": str(frames_dir),
            "count": len(frames),
        }
        await progress_cb(60, f"Extracted frames: {len(frames)}")
    
    thumb = project / "thumbnail.jpg"
    if thumb.exists():
        summary["available_outputs"]["thumbnail"] = str(thumb)
    
    # Write summary
    summary_path = export_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    await progress_cb(80, f"Summary written to {summary_path.name}")
    
    # If transforms exist but no model, still very useful
    if transforms.exists():
        await progress_cb(90, "✅ Camera poses ready — can be used with any 3DGS trainer")


def _find_config_yml(output_dir: Path) -> str | None:
    """Find the most recent nerfstudio config.yml in the output directory."""
    if not output_dir.exists():
        return None
    
    configs = sorted(
        output_dir.rglob("config.yml"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    return str(configs[0]) if configs else None
