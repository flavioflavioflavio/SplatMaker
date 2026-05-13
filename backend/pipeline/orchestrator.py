"""
Pipeline Orchestrator — runs pipeline steps sequentially with WebSocket progress.
"""
import asyncio
import time
import json
from pathlib import Path

from models import PipelineConfig
from ws_manager import WSManager
from pipeline.extract import extract_frames
from pipeline.split import split_to_perspective
from pipeline.mask import run_masking
from pipeline.sfm import run_sfm
from pipeline.train import run_training
from pipeline.export import export_splat


STEPS = [
    ("extract", extract_frames),
    ("split", split_to_perspective),
    ("mask", run_masking),
    ("sfm", run_sfm),
    ("train", run_training),
    ("export", export_splat),
]


class PipelineOrchestrator:
    """Runs the full processing pipeline with real-time progress reporting."""
    
    def __init__(self, ws: WSManager):
        self.ws = ws
        self.running = False
        self.current_step = None
        self.current_task = None
        self.results = {}
    
    async def start(self, config: PipelineConfig):
        """Start the pipeline for a given project."""
        if self.running:
            return {"error": "Pipeline is already running"}
        
        self.running = True
        self.results = {}
        start_time = time.time()
        
        # Update project status
        self._update_project_status(config.project_id, "processing")
        
        for i, (name, func) in enumerate(STEPS):
            if not self.running:
                await self.ws.send_log("Pipeline stopped by user", "warning")
                break
            
            self.current_step = name
            step_start = time.time()
            
            await self.ws.send_progress(name, "running", 0,
                                        f"Starting {name}...")
            await self.ws.send_log(f"Starting step: {name}")
            
            try:
                async def progress_cb(pct, msg=""):
                    elapsed = time.time() - step_start
                    await self.ws.send_progress(name, "running", pct,
                                                msg or f"{name}: {pct}%",
                                                elapsed)
                
                result = await func(config.project_id, config, progress_cb)
                self.results[name] = result
                
                elapsed = time.time() - step_start
                await self.ws.send_progress(name, "done", 100,
                                            f"{name} complete", elapsed)
                await self.ws.send_log(
                    f"Step {name} complete in {elapsed:.1f}s: {json.dumps(result)}",
                    "info"
                )
            except Exception as e:
                elapsed = time.time() - step_start
                await self.ws.send_progress(name, "error", 0,
                                            str(e), elapsed)
                await self.ws.send_log(f"Step {name} failed: {e}", "error")
                await self.ws.send_error(name, str(e))
                self._update_project_status(config.project_id, "error")
                self.running = False
                return {"status": "error", "step": name, "error": str(e)}
        
        total_time = time.time() - start_time
        self.running = False
        self.current_step = None
        
        splat_path = self.results.get("export", {}).get("ply_path", "")
        self._update_project_status(config.project_id, "done")
        
        await self.ws.send_complete(config.project_id, splat_path, total_time)
        return {"status": "complete", "total_time": total_time, "results": self.results}
    
    def stop(self):
        """Stop the currently running pipeline."""
        self.running = False
    
    def get_status(self):
        """Get the current pipeline status."""
        return {
            "running": self.running,
            "current_step": self.current_step,
            "results": self.results,
        }
    
    async def handle_mask_click(self, msg: dict):
        """Handle an interactive mask click from the frontend."""
        # This will be wired up when the masking UI is built
        await self.ws.send_log(
            f"Mask click received: frame={msg.get('frame_index')}, "
            f"point={msg.get('point')}",
            "info"
        )
    
    def _update_project_status(self, project_id: str, status: str):
        """Update the project's meta.json status field."""
        from config import settings
        meta_path = Path(settings.projects_dir) / project_id / "meta.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            meta["status"] = status
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2)
