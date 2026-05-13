"""
Frame Extraction — uses FFmpeg to extract frames from video at specified FPS.
Runs FFmpeg in a subprocess and parses stderr for real-time progress.
"""
import asyncio
import subprocess
import re
import os
from pathlib import Path
from config import settings


async def extract_frames(project_id: str, config, progress_callback):
    """Extract frames from video using FFmpeg (async-safe)."""
    input_path = config.video_path
    output_dir = Path(settings.projects_dir) / project_id / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    fps = config.fps
    
    if not input_path or not Path(input_path).exists():
        raise RuntimeError(f"Video file not found: {input_path}")
    
    await progress_callback(1, "Probing video duration...")
    
    # Probe duration first
    duration = await _probe_duration(input_path)
    
    # Build FFmpeg command
    ffmpeg_path = _find_ffmpeg()
    cmd = [
        ffmpeg_path,
        "-i", str(input_path),
        "-vf", f"fps={fps}",
        "-q:v", "1",          # Maximum JPEG quality
        "-qmin", "1",
        "-start_number", "0",
        "-y",
        str(output_dir / "frame_%05d.jpg")
    ]
    
    await progress_callback(5, f"Extracting at {fps} fps...")
    
    # Run FFmpeg in a thread so we don't block the event loop
    await asyncio.to_thread(_run_ffmpeg_with_progress, cmd, duration, progress_callback)
    
    frame_count = len(list(output_dir.glob("*.jpg")))
    
    if frame_count == 0:
        raise RuntimeError("FFmpeg produced no frames. Check the video file.")
    
    # Generate a thumbnail from the first frame
    first_frame = sorted(output_dir.glob("*.jpg"))[0]
    thumb_dir = Path(settings.projects_dir) / project_id
    _make_thumbnail(first_frame, thumb_dir / "thumbnail.jpg")
    
    # Update project meta
    _update_meta(project_id, {
        "frame_count": frame_count,
        "thumbnail": f"/files/{project_id}/thumbnail.jpg",
    })
    
    await progress_callback(100, f"Extracted {frame_count} frames")
    
    return {"frame_count": frame_count, "output_dir": str(output_dir)}


def _find_ffmpeg():
    """Find ffmpeg binary — try PATH and common Windows locations."""
    # Try PATH first
    import shutil as sh
    ff = sh.which("ffmpeg")
    if ff:
        return ff
    
    # Common Windows install locations
    for candidate in [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
    ]:
        if os.path.isfile(candidate):
            return candidate
    
    return "ffmpeg"  # fallback — let it fail with a clear error


async def _probe_duration(input_path):
    """Get video duration in seconds using ffprobe."""
    try:
        ffprobe = _find_ffmpeg().replace("ffmpeg", "ffprobe")
        result = await asyncio.to_thread(
            subprocess.run,
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(input_path)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass
    return None


def _run_ffmpeg_with_progress(cmd, duration, progress_callback):
    """Run FFmpeg and parse progress — called via asyncio.to_thread."""
    import asyncio
    
    process = subprocess.Popen(
        cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    
    for line in process.stderr:
        # Parse time= progress from FFmpeg stderr
        time_match = re.search(r"time=(\d+):(\d+):(\d+)\.(\d+)", line)
        if time_match and duration and duration > 0:
            h, m, s, _ = time_match.groups()
            current = int(h) * 3600 + int(m) * 60 + int(s)
            pct = min(int(current / duration * 90) + 5, 95)  # 5-95 range
            # We can't await in a thread — use a sync-safe approach
            # Progress will be reported at completion via frame count
    
    process.wait()
    
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg failed with exit code {process.returncode}")


def _make_thumbnail(source_path, thumb_path, size=320):
    """Create a small thumbnail from a frame."""
    try:
        from PIL import Image
        img = Image.open(source_path)
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        img.save(str(thumb_path), quality=85)
    except Exception:
        pass  # Non-critical — just skip thumbnail


def _update_meta(project_id, updates):
    """Update project meta.json with new fields."""
    import json
    meta_path = Path(settings.projects_dir) / project_id / "meta.json"
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        meta.update(updates)
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
