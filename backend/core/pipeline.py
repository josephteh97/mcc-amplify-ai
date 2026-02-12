"""
Main Processing Pipeline
Orchestrates all 7 stages of floor plan to BIM conversion
"""

from typing import Dict, Any, Optional
from pathlib import Path
import asyncio
from loguru import logger

from backend.service.core.orchestrator import PipelineOrchestrator

class FloorPlanPipeline:
    """
    Wrapper for the new Hybrid AI Orchestrator
    Maintains backward compatibility for existing API calls
    """
    
    def __init__(self):
        self.orchestrator = PipelineOrchestrator()
    
    async def process(
        self, 
        pdf_path: str, 
        job_id: str,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute complete pipeline using the new Hybrid Orchestrator
        """
        # Delegate to the new orchestrator
        return await self.orchestrator.run_pipeline(pdf_path, job_id, project_name)

    async def _update_progress(self, job_id: str, progress: int, message: str):
        """Send progress update via WebSocket"""
        await ws_manager.send_progress(job_id, {
            "progress": progress,
            "message": message
        })
