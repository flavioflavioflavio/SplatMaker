"""
SplatMaker Backend Configuration — paths, defaults, GPU detection.
"""
import subprocess
import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Settings:
    """Application settings."""
    host: str = "127.0.0.1"
    port: int = 8420
    projects_dir: str = str(Path(__file__).parent / "projects")
    ffmpeg_path: str = "ffmpeg"
    colmap_path: str = "colmap"
    glomap_path: str = "glomap"
    default_fps: int = 2
    default_views_per_frame: int = 8
    default_crop_factor: float = 0.15
    default_max_iterations: int = 30000


settings = Settings()


def detect_gpu() -> dict:
    """Detect NVIDIA GPU info via nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            return {
                "available": True,
                "name": parts[0] if len(parts) > 0 else "Unknown",
                "memory_mb": int(parts[1]) if len(parts) > 1 else 0,
                "driver": parts[2] if len(parts) > 2 else "Unknown",
            }
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    
    return {"available": False, "name": None, "memory_mb": 0, "driver": None}
