"""
SplatMaker Pydantic models for API request/response validation.
"""
from pydantic import BaseModel
from typing import Optional


class HealthResponse(BaseModel):
    status: str
    gpu: dict


class ProjectCreate(BaseModel):
    name: str
    video_path: str


class ProjectInfo(BaseModel):
    id: str
    name: str
    video_path: str
    status: str  # created | processing | done | error
    created_at: str
    frame_count: int = 0
    thumbnail: Optional[str] = None


class PipelineConfig(BaseModel):
    project_id: str
    fps: int = 2
    views_per_frame: int = 8
    crop_top_bottom: float = 0.15
    mask_mode: str = "auto"  # auto | interactive | none
    sfm_engine: str = "glomap"  # glomap | colmap
    max_iterations: int = 30000
