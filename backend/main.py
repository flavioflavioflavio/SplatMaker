"""
SplatMaker Backend — FastAPI server for the Gaussian Splat pipeline.
Runs as a sidecar process managed by the Tauri desktop shell.
"""
import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings, detect_gpu
from models import ProjectCreate, PipelineConfig, HealthResponse, ProjectInfo
from ws_manager import WSManager
from pipeline.orchestrator import PipelineOrchestrator

import os
import json
import uuid
import shutil
from datetime import datetime
from pathlib import Path

app = FastAPI(title="SplatMaker Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ws_manager = WSManager()
orchestrator = PipelineOrchestrator(ws_manager)

# Serve project files statically for thumbnails, etc.
projects_path = Path(settings.projects_dir)
projects_path.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(projects_path)), name="project_files")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    gpu_info = detect_gpu()
    return HealthResponse(status="ok", gpu=gpu_info)


# ── Projects ──────────────────────────────────────────────────────────────────

@app.get("/api/projects")
async def list_projects():
    """List all projects with their metadata."""
    projects = []
    projects_dir = Path(settings.projects_dir)
    projects_dir.mkdir(parents=True, exist_ok=True)
    
    for proj_dir in projects_dir.iterdir():
        if proj_dir.is_dir() and proj_dir.name != ".gitkeep":
            meta_file = proj_dir / "meta.json"
            if meta_file.exists():
                with open(meta_file) as f:
                    meta = json.load(f)
                    projects.append(meta)
    
    # Sort by creation date descending
    projects.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return {"projects": projects}


@app.post("/api/project/create")
async def create_project(data: ProjectCreate):
    """Create a new project directory with metadata."""
    project_id = str(uuid.uuid4())[:8]
    proj_dir = Path(settings.projects_dir) / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    for sub in ["frames", "split", "masks", "sparse", "processed", "output", "export"]:
        (proj_dir / sub).mkdir(exist_ok=True)
    
    meta = {
        "id": project_id,
        "name": data.name,
        "video_path": data.video_path,
        "status": "created",
        "created_at": datetime.now().isoformat(),
        "frame_count": 0,
    }
    
    with open(proj_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    
    return meta


@app.post("/api/project/{project_id}/upload-video")
async def upload_video(project_id: str, file: UploadFile = File(...)):
    """Upload a video file to a project directory."""
    proj_dir = Path(settings.projects_dir) / project_id
    if not proj_dir.exists():
        return {"error": "Project not found"}
    
    video_path = proj_dir / file.filename
    with open(video_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Update meta with absolute video path
    meta_path = proj_dir / "meta.json"
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        meta["video_path"] = str(video_path)
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
    
    return {"video_path": str(video_path), "size": len(content)}


@app.post("/api/pipeline/start")
async def start_pipeline(config: PipelineConfig):
    """Start the processing pipeline (non-blocking — returns immediately)."""
    if orchestrator.running:
        return {"error": "Pipeline is already running"}
    
    # Resolve video path from project meta if not absolute
    proj_dir = Path(settings.projects_dir) / config.project_id
    meta_path = proj_dir / "meta.json"
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        video_path = meta.get("video_path", "")
        # If relative or just filename, resolve to project dir
        if not Path(video_path).is_absolute():
            video_path = str(proj_dir / video_path)
        config.video_path = video_path
    
    # Fire-and-forget — run pipeline in background
    asyncio.create_task(orchestrator.start(config))
    return {"status": "started", "project_id": config.project_id}


@app.post("/api/pipeline/stop")
async def stop_pipeline():
    """Stop the currently running pipeline."""
    orchestrator.stop()
    return {"status": "stopped"}


@app.get("/api/pipeline/status")
async def pipeline_status():
    """Get the current pipeline status."""
    return orchestrator.get_status()


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/pipeline")
async def pipeline_ws(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("type") == "pipeline_start":
                config = PipelineConfig(**msg.get("config", {}), project_id=msg["project_id"])
                asyncio.create_task(orchestrator.start(config))
            elif msg.get("type") == "pipeline_stop":
                orchestrator.stop()
            elif msg.get("type") == "mask_click":
                # Forward mask click to the masking step
                await orchestrator.handle_mask_click(msg)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ── System Check ──────────────────────────────────────────────────────────────

@app.get("/api/system/check")
async def system_check():
    """Check if all required system dependencies are available."""
    import subprocess
    
    tools = {
        "python": "python --version",
        "ffmpeg": "ffmpeg -version",
        "colmap": "colmap --version",
        "nvidia_smi": "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader",
    }
    
    results = {}
    for name, cmd in tools.items():
        try:
            proc = subprocess.run(
                cmd.split(), capture_output=True, text=True, timeout=10
            )
            results[name] = {
                "available": proc.returncode == 0,
                "output": proc.stdout.strip() or proc.stderr.strip()[:200],
            }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            results[name] = {"available": False, "output": "Not found"}
    
    return {"tools": results, "gpu": detect_gpu()}


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8420, log_level="info")
