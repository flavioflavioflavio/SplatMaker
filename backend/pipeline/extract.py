"""
Frame Extraction — uses FFmpeg to extract frames from video at specified FPS.
"""
import subprocess
import re
import os
from pathlib import Path
from config import settings


async def extract_frames(project_id: str, config, progress_callback):
    """Extract frames from video using FFmpeg."""
    input_path = config.video_path
    output_dir = Path(settings.projects_dir) / project_id / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    fps = config.fps
    
    # First, get video duration
    probe_cmd = [
        settings.ffmpeg_path, "-i", str(input_path),
        "-f", "null", "-"
    ]
    
    cmd = [
        settings.ffmpeg_path,
        "-i", str(input_path),
        "-vf", f"fps={fps}",
        "-q:v", "1",
        "-y",
        str(output_dir / "frame_%05d.jpg")
    ]
    
    process = subprocess.Popen(
        cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    
    # Parse FFmpeg stderr for duration and progress
    duration = None
    for line in process.stderr:
        # Try to extract duration
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", line)
        if dur_match and duration is None:
            h, m, s, _ = dur_match.groups()
            duration = int(h) * 3600 + int(m) * 60 + int(s)
        
        # Try to extract current time
        time_match = re.search(r"time=(\d+):(\d+):(\d+)\.(\d+)", line)
        if time_match and duration and duration > 0:
            h, m, s, _ = time_match.groups()
            current = int(h) * 3600 + int(m) * 60 + int(s)
            pct = min(int(current / duration * 100), 99)
            await progress_callback(pct, f"Extracting frames... {pct}%")
    
    process.wait()
    
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg failed with code {process.returncode}")
    
    frame_count = len(list(output_dir.glob("*.jpg")))
    await progress_callback(100, f"Extracted {frame_count} frames")
    
    # Update project meta with frame count
    return {"frame_count": frame_count, "output_dir": str(output_dir)}
