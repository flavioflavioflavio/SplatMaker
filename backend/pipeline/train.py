"""
Training — Gaussian Splat training via Nerfstudio splatfacto or gsplat.
Sprint 2: checks for nerfstudio availability, structured for real integration.
"""
import asyncio
import subprocess
import re
import shutil
import json
from pathlib import Path
from config import settings


async def run_training(project_id: str, config, progress_callback):
    """Train a Gaussian Splat model."""
    proj_dir = Path(settings.projects_dir) / project_id
    processed_dir = proj_dir / "processed"
    output_dir = proj_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    max_iters = config.max_iterations
    transforms_path = processed_dir / "transforms.json"
    
    # Check if transforms.json exists
    if not transforms_path.exists():
        # Try project root
        transforms_path = proj_dir / "transforms.json"
    
    if not transforms_path.exists():
        raise RuntimeError("No transforms.json found. Run SfM step first.")
    
    # Verify transforms
    with open(transforms_path) as f:
        transforms = json.load(f)
    frame_count = len(transforms.get("frames", []))
    await progress_callback(5, f"Found {frame_count} camera poses")
    
    # Check for nerfstudio
    ns_train = shutil.which("ns-train")
    
    if ns_train:
        await progress_callback(10, "Nerfstudio found — starting splatfacto training...")
        await _run_nerfstudio(ns_train, proj_dir, processed_dir, output_dir, 
                              max_iters, progress_callback)
    else:
        # Nerfstudio not available — simulate training with progress
        await progress_callback(10, "Nerfstudio not installed — running in preview mode")
        await progress_callback(15, f"To enable real training, install nerfstudio:")
        await progress_callback(15, "  pip install nerfstudio")
        
        # Simulate training progress for UI development
        steps = 10
        for i in range(steps):
            await asyncio.sleep(0.5)
            pct = int((i + 1) / steps * 80) + 15
            iter_num = int(max_iters * (i + 1) / steps)
            await progress_callback(pct, f"[Preview] Training: step {iter_num}/{max_iters}")
        
        # Create a placeholder output
        placeholder = {
            "model": "splatfacto",
            "iterations": max_iters,
            "frames": frame_count,
            "status": "preview_mode",
            "note": "Install nerfstudio for real training"
        }
        with open(output_dir / "training_info.json", "w") as f:
            json.dump(placeholder, f, indent=2)
    
    await progress_callback(100, f"Training complete: {max_iters} iterations")
    
    return {
        "output_dir": str(output_dir),
        "iterations": max_iters,
        "frames": frame_count,
        "engine": "nerfstudio" if ns_train else "preview",
    }


async def _run_nerfstudio(ns_train, proj_dir, data_dir, output_dir, max_iters, progress_callback):
    """Run nerfstudio splatfacto training with progress parsing."""
    cmd = [
        ns_train, "splatfacto",
        "--data", str(data_dir),
        "--output-dir", str(output_dir),
        "--max-num-iterations", str(max_iters),
        "--pipeline.model.num-downscales", "0",
        "--viewer.quit-on-train-completion", "True",
        "nerfstudio-data",
        "--data", str(data_dir),
    ]
    
    await progress_callback(15, f"ns-train splatfacto --max-num-iterations {max_iters}")
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    # Parse training output for progress
    async for line in process.stderr:
        text = line.decode("utf-8", errors="replace").strip()
        if not text:
            continue
        
        # Parse iteration progress: "Step 1000/30000"
        step_match = re.search(r"Step\s+(\d+)/(\d+)", text)
        if step_match:
            current = int(step_match.group(1))
            total = int(step_match.group(2))
            pct = min(int(current / total * 80) + 15, 95)
            
            # Parse loss if available
            loss_match = re.search(r"loss[:\s]+([\d.]+)", text, re.IGNORECASE)
            loss_str = f" | loss: {loss_match.group(1)}" if loss_match else ""
            
            await progress_callback(pct, f"Training: step {current}/{total}{loss_str}")
    
    await process.wait()
    
    if process.returncode != 0:
        stderr = await process.stderr.read()
        raise RuntimeError(f"Nerfstudio training failed (exit {process.returncode})")
