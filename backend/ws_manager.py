"""
WebSocket manager — handles multiple connections and broadcasts progress events.
"""
from fastapi import WebSocket
from typing import List
import json


class WSManager:
    """Manages WebSocket connections and broadcasts messages to all clients."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Send a message to all connected WebSocket clients."""
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        
        for conn in dead:
            self.disconnect(conn)
    
    async def send_progress(self, step: str, status: str, progress: int,
                            message: str = "", elapsed: float = 0):
        """Convenience method to send a pipeline progress update."""
        await self.broadcast({
            "type": "pipeline_progress",
            "step": step,
            "status": status,
            "progress": progress,
            "message": message,
            "elapsed_seconds": round(elapsed, 1),
        })
    
    async def send_log(self, message: str, level: str = "info"):
        """Send a log message to all clients."""
        await self.broadcast({
            "type": "log",
            "level": level,
            "message": message,
        })
    
    async def send_complete(self, project_id: str, splat_path: str, total_time: float):
        """Send pipeline completion message."""
        await self.broadcast({
            "type": "pipeline_complete",
            "project_id": project_id,
            "splat_path": splat_path,
            "total_time_seconds": round(total_time, 1),
        })
