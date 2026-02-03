"""
Main Processing Pipeline
Orchestrates all 7 stages of floor plan to BIM conversion
"""

from typing import Dict, Any, Optional
from pathlib import Path
import asyncio
from loguru import logger

from services.stage1_pdf_processor import Stage1PDFProcessor
from services.stage2_scale_detector import Stage2ScaleDetector
from services.stage3_element_detector import Stage3ElementDetector
from services.stage4_semantic_analyzer import Stage4SemanticAnalyzer
from services.stage5_geometry_generator import Stage5GeometryGenerator
from services.stage6_bim_enrichment import Stage6BIMEnrichment
from services.stage7_exporters.rvt_exporter import RVTExporter
from services.stage7_exporters.gltf_exporter import GLTFExporter
from services.revit_client import RevitClient
from api.websocket import manager as ws_manager


class FloorPlanPipeline:
    """
    Complete processing pipeline from PDF to RVT
    """
    
    def __init__(self):
        self.pdf_processor = Stage1PDFProcessor()
        self.scale_detector = Stage2ScaleDetector()
        self.element_detector = Stage3ElementDetector()
        self.semantic_analyzer = Stage4SemanticAnalyzer()
        self.geometry_generator = Stage5GeometryGenerator()
        self.bim_enrichment = Stage6BIMEnrichment()
        self.rvt_exporter = RVTExporter()
        self.gltf_exporter = GLTFExporter()
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
            await self._update_progress(job_id, 35, "Detecting walls, doors, windows, columns...")
            detected_elements = await self.element_detector.detect(
                image_data,
                scale_info
            )
            logger.info(f"[{job_id}] Stage 3 complete: Detected {len(detected_elements['walls'])} walls, {len(detected_elements['columns'])} columns")
            
            # Stage 4: Semantic Analysis (Claude AI)
            await self._update_progress(job_id, 50, "Analyzing with AI...")
            enriched_data = await self.semantic_analyzer.analyze(
                image_data,
                detected_elements,
                scale_info
            )
            logger.info(f"[{job_id}] Stage 4 complete: AI analysis done")
            
            # Stage 5: 3D Geometry Generation
            await self._update_progress(job_id, 65, "Generating 3D geometry...")
            geometry_data = await self.geometry_generator.build(
                enriched_data,
                scale_info
            )
            logger.info(f"[{job_id}] Stage 5 complete: 3D geometry created")
            
            # Stage 7: Export to Multiple Formats
            await self._update_progress(job_id, 75, "Creating web preview...")
            gltf_path = await self.gltf_exporter.export(
                geometry_data,
                f"data/models/gltf/{job_id}.glb"
            )
            
            # Stage 6: BIM Enrichment & Revit Transaction
            await self._update_progress(job_id, 80, "Preparing BIM data...")
            revit_transaction = await self.bim_enrichment.generate(
                geometry_data,
                project_name or f"FloorPlan_{job_id}"
            )
            
            # Save transaction JSON
            transaction_path = f"data/models/revit_transactions/{job_id}.json"
            await self.bim_enrichment.save(revit_transaction, transaction_path)
            logger.info(f"[{job_id}] Stage 6 complete: BIM data enriched")
            
            # Stage 7 (Continued): Build RVT on Windows Server
            await self._update_progress(job_id, 85, "Building Revit model on Windows server...")
            rvt_path = await self.rvt_exporter.export(
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
                    "rooms_count": len(geometry_data['rooms']),
                    "columns_count": len(geometry_data.get('columns', []))
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
