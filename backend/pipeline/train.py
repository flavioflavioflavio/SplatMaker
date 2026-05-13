"""
SplatMaker — Training Step
Runs nerfstudio splatfacto training with real-time progress parsing.
"""
import asyncio
import os
import re
import shutil
from pathlib import Path


async def run_training(project_id: str, config, progress_cb):
    """
    Train a Gaussian Splat model using nerfstudio's splatfacto.
    
    Requires:
      - {project_dir}/transforms.json (from split or SfM step)
      - {project_dir}/split/ directory with perspective images
      
    Produces:
      - {project_dir}/outputs/ (nerfstudio checkpoints + logs)
    """
    from config import settings
    project = Path(settings.projects_dir) / project_id
    transforms = project / "transforms.json"
    split_dir = project / "split"
    output_dir = project / "outputs"
    
    max_iters = getattr(config, 'max_iterations', 30000) if hasattr(config, 'max_iterations') else config.get("max_iterations", 30000)
    
    # ── Validate inputs ───────────────────────────────────────────────────
    if not transforms.exists():
        raise FileNotFoundError(f"transforms.json not found in {project}")
    
    if not split_dir.exists() or not list(split_dir.glob("*.jpg")):
        raise FileNotFoundError(f"No training images found in {split_dir}")
    
    image_count = len(list(split_dir.glob("*.jpg")))
    await progress_cb(5, f"Found {image_count} training images")
    
    # ── Check for ns-train ────────────────────────────────────────────────
    ns_train = shutil.which("ns-train")
    
    if ns_train:
        await _run_real_training(project, output_dir, max_iters, progress_cb)
    else:
        await progress_cb(10, "⚠ ns-train not found — running preview simulation")
        await _run_preview(max_iters, progress_cb)


async def _run_real_training(project: Path, output_dir: Path, max_iters: int, progress_cb):
    """Execute actual nerfstudio splatfacto training."""
    
    await progress_cb(5, f"Starting splatfacto training ({max_iters} iterations)")
    
    # Build the ns-train command
    cmd = [
        "ns-train", "splatfacto",
        "--data", str(project),
        "--output-dir", str(output_dir),
        "--max-num-iterations", str(max_iters),
        "--vis", "viewer",  # Enable browser viewer
        "--pipeline.datamanager.camera-optimizer.mode", "off",  # Synthetic poses are exact
        "nerfstudio-data",
    ]
    
    await progress_cb(8, f"Command: {' '.join(cmd)}")
    
    # Launch the training process
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(project),
    )
    
    # Parse progress from stderr (nerfstudio outputs training logs there)
    last_progress = 8
    iter_pattern = re.compile(r"Step \(% Done\)\s+(\d+)/(\d+)")
    loss_pattern = re.compile(r"loss[:\s]+([0-9.e+-]+)", re.IGNORECASE)
    viewer_pattern = re.compile(r"Use this link to visualize:\s*(https?://\S+)")
    
    async def parse_stream(stream):
        nonlocal last_progress
        async for raw in stream:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            
            # Check for viewer URL
            m = viewer_pattern.search(line)
            if m:
                await progress_cb(last_progress, f"📺 Viewer: {m.group(1)}")
            
            # Check for iteration progress
            m = iter_pattern.search(line)
            if m:
                current = int(m.group(1))
                total = int(m.group(2))
                pct = int(10 + (current / total) * 85)  # Map 0-100% to 10-95%
                pct = min(pct, 95)
                
                # Extract loss if present
                lm = loss_pattern.search(line)
                loss_str = f" | loss: {lm.group(1)}" if lm else ""
                
                if pct > last_progress + 1:  # Don't spam updates
                    last_progress = pct
                    await progress_cb(pct, f"Training: {current}/{total}{loss_str}")
    
    # Parse both stdout and stderr concurrently
    await asyncio.gather(
        parse_stream(process.stdout),
        parse_stream(process.stderr),
    )
    
    returncode = await process.wait()
    
    if returncode != 0:
        raise RuntimeError(f"ns-train failed with exit code {returncode}")
    
    await progress_cb(95, "Training complete — locating model checkpoint")
    
    # Find the latest checkpoint
    ckpt = _find_latest_checkpoint(output_dir)
    if ckpt:
        await progress_cb(100, f"Model saved: {ckpt}")
    else:
        await progress_cb(100, "Training complete (no checkpoint found — check outputs/)")


async def _run_preview(max_iters: int, progress_cb):
    """Simulate training progress for UI development."""
    steps = 20
    for i in range(steps):
        pct = int(10 + (i / steps) * 85)
        fake_loss = round(0.5 * (1 - i / steps) ** 2 + 0.001, 4)
        current = int((i / steps) * max_iters)
        await progress_cb(pct, f"[PREVIEW] Step {current}/{max_iters} | loss: {fake_loss}")
        await asyncio.sleep(0.3)
    
    await progress_cb(100, "[PREVIEW] Training simulation complete")


def _find_latest_checkpoint(output_dir: Path) -> str | None:
    """Find the most recent nerfstudio checkpoint in the output directory."""
    if not output_dir.exists():
        return None
    
    # nerfstudio saves checkpoints like: outputs/splatfacto/YYYY-MM-DD_HHMMSS/nerfstudio_models/
    ckpts = sorted(output_dir.rglob("step-*.ckpt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if ckpts:
        return str(ckpts[0])
    
    return None
