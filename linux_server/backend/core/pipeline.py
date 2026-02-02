"""
Main Processing Pipeline
Orchestrates all 7 stages of floor plan to BIM conversion
"""

from typing import Dict, Any, Optional
from pathlib import Path
import asyncio
from loguru import logger

from services.pdf_processor import PDFProcessor
from services.scale_detector import ScaleDetector
from services.element_detector import ElementDetector
from services.claude_analyzer import ClaudeAnalyzer
from services.geometry_builder import GeometryBuilder
from services.revit_transaction import RevitTransactionGenerator
from services.revit_client import RevitClient
from api.websocket import manager as ws_manager


class FloorPlanPipeline:
    """
    Complete processing pipeline from PDF to RVT
    """
    
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.scale_detector = ScaleDetector()
        self.element_detector = ElementDetector()
        self.claude_analyzer = ClaudeAnalyzer()
        self.geometry_builder = GeometryBuilder()
        self.revit_transaction = RevitTransactionGenerator()
        self.revit_client = RevitClient()
    
    async def process(
        self, 
        pdf_path: str, 
        job_id: str,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute complete pipeline
        
        Args:
            pdf_path: Path to uploaded PDF
            job_id: Unique job identifier
            project_name: Optional project name
            
        Returns:
            Dict with paths to generated files
        """
        try:
            logger.info(f"[{job_id}] Starting pipeline for {pdf_path}")
            
            # Stage 1: PDF Processing
            await self._update_progress(job_id, 10, "Processing PDF...")
            image_data = await self.pdf_processor.process(pdf_path)
            logger.info(f"[{job_id}] Stage 1 complete: PDF converted to image")
            
            # Stage 2: Scale Detection
            await self._update_progress(job_id, 20, "Detecting scale...")
            scale_info = await self.scale_detector.detect(image_data)
            logger.info(f"[{job_id}] Stage 2 complete: Scale = {scale_info['scale']}")
            
            # Stage 3: Element Detection (YOLOv8)
            await self._update_progress(job_id, 35, "Detecting walls, doors, windows...")
            detected_elements = await self.element_detector.detect(
                image_data,
                scale_info
            )
            logger.info(f"[{job_id}] Stage 3 complete: Detected {len(detected_elements['walls'])} walls")
            
            # Stage 4: Semantic Analysis (Claude AI)
            await self._update_progress(job_id, 50, "Analyzing with AI...")
            enriched_data = await self.claude_analyzer.analyze(
                image_data,
                detected_elements,
                scale_info
            )
            logger.info(f"[{job_id}] Stage 4 complete: AI analysis done")
            
            # Stage 5: 3D Geometry Generation
            await self._update_progress(job_id, 65, "Generating 3D geometry...")
            geometry_data = await self.geometry_builder.build(
                enriched_data,
                scale_info
            )
            logger.info(f"[{job_id}] Stage 5 complete: 3D geometry created")
            
            # Export glTF for web viewer
            await self._update_progress(job_id, 75, "Creating web preview...")
            gltf_path = await self.geometry_builder.export_gltf(
                geometry_data,
                f"data/models/gltf/{job_id}.glb"
            )
            
            # Stage 6: Generate Revit Transaction
            await self._update_progress(job_id, 80, "Preparing Revit model...")
            revit_transaction = await self.revit_transaction.generate(
                geometry_data,
                project_name or f"FloorPlan_{job_id}"
            )
            
            # Save transaction JSON
            transaction_path = f"data/models/revit_transactions/{job_id}.json"
            await self.revit_transaction.save(revit_transaction, transaction_path)
            logger.info(f"[{job_id}] Stage 6 complete: Revit transaction generated")
            
            # Stage 7: Build RVT on Windows Server
            await self._update_progress(job_id, 85, "Building Revit model on Windows server...")
            rvt_path = await self.revit_client.build_model(
                transaction_path,
                job_id
            )
            logger.info(f"[{job_id}] Stage 7 complete: RVT file created")
            
            # Complete
            await self._update_progress(job_id, 100, "Complete!")
            
            return {
                "job_id": job_id,
                "status": "completed",
                "files": {
                    "rvt": rvt_path,
                    "gltf": gltf_path,
                    "transaction": transaction_path,
                    "analysis": enriched_data
                },
                "metadata": {
                    "scale": scale_info['scale'],
                    "walls_count": len(geometry_data['walls']),
                    "doors_count": len(geometry_data['doors']),
                    "windows_count": len(geometry_data['windows']),
                    "rooms_count": len(geometry_data['rooms'])
                }
            }
            
        except Exception as e:
            logger.error(f"[{job_id}] Pipeline failed: {str(e)}")
            await self._update_progress(job_id, -1, f"Error: {str(e)}")
            raise
    
    async def _update_progress(self, job_id: str, progress: int, message: str):
        """Send progress update via WebSocket"""
        await ws_manager.send_progress(job_id, {
            "progress": progress,
            "message": message
        })
