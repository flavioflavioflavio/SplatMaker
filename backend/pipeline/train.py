"""
Training — Nerfstudio splatfacto Gaussian Splat training.
Stub implementation for Sprint 1.
"""
import subprocess
import re
from pathlib import Path
from config import settings


async def run_training(project_id: str, config, progress_callback):
    """Train a Gaussian Splat model using Nerfstudio splatfacto."""
    data_dir = Path(settings.projects_dir) / project_id / "processed"
    output_dir = Path(settings.projects_dir) / project_id / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    max_iters = config.max_iterations
    
    # TODO: Full Nerfstudio integration
    # cmd = [
    #     "ns-train", "splatfacto",
    #     "--data", str(data_dir),
    #     "--output-dir", str(output_dir),
    #     "--max-num-iterations", str(max_iters),
    #     "--pipeline.model.num-downscales", "0",
    #     "--viewer.quit-on-train-completion", "True",
    # ]
    
    await progress_callback(25, f"Training: step 0/{max_iters} (stub)")
    await progress_callback(50, f"Training: step {max_iters//2}/{max_iters} (stub)")
    await progress_callback(75, f"Training: step {int(max_iters*0.75)}/{max_iters} (stub)")
    await progress_callback(100, f"Training complete: {max_iters}/{max_iters} (stub)")
    
    return {
        "output_dir": str(output_dir),
        "iterations": max_iters,
        "note": "Stub implementation — Nerfstudio integration pending"
    }
