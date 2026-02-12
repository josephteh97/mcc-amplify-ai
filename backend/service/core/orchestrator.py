"""
Core Orchestrator: Manages the Dual-Track Pipeline
"""

import asyncio
from loguru import logger

# Import modules
from backend.service.security.secure_renderer import SecurePDFRenderer, ResourceMonitor
from backend.service.pdf_processing.processors import StreamingProcessor
from backend.service.fusion.pipeline import HybridFusionPipeline

# Wrappers for existing legacy services (to reuse YOLO/Claude logic)
from services.stage3_element_detector import Stage3ElementDetector
from services.stage4_semantic_analyzer import Stage4SemanticAnalyzer
from services.stage5_geometry_generator import Stage5GeometryGenerator
from services.stage7_exporters.rvt_exporter import RvtExporter
from services.stage7_exporters.gltf_exporter import GltfExporter

class PipelineOrchestrator:
    """
    Central brain of the Hybrid AI System.
    Orchestrates flow between Security -> PDF Proc -> Fusion -> Export
    """
    
    def __init__(self):
        # New Modules
        self.security = SecurePDFRenderer()
        self.fusion = HybridFusionPipeline()
        
        # Adapters for Legacy Services
        self.ml_detector = Stage3ElementDetector() # Acts as VisionModel
        self.semantic_ai = Stage4SemanticAnalyzer()
        self.geometry_gen = Stage5GeometryGenerator()
        
        # Processor needs ML detector
        self.pdf_processor = StreamingProcessor(self.ml_detector)
        
        self.rvt_exporter = RvtExporter()
        self.gltf_exporter = GltfExporter()

    async def run_pipeline(self, pdf_path: str, job_id: str, project_name: str = "Project"):
        """
        Main execution flow
        """
        logger.info(f"🚀 Starting Hybrid Pipeline for Job {job_id}")
        
        monitor = ResourceMonitor()
        monitor.start()
        
        try:
            # 1. Security Check & Strategy Determination
            logger.info("🔒 Stage 1: Security & Strategy Check")
            secure_context = await self.security.safe_render(pdf_path)
            
            # 2. Dual-Track Processing (Vectors + Raster ML)
            logger.info("⚡ Stage 2: Dual-Track Processing (Vector + Raster)")
            raw_results = await self.pdf_processor.process(
                secure_context["page"], 
                secure_context
            )
            
            # 3. Hybrid Fusion
            logger.info("🔗 Stage 3: Hybrid Fusion (Aligning Vector & ML)")
            fused_data = await self.fusion.fuse(
                raw_results["vectors"],
                raw_results["ml_detections"],
                raw_results["metadata"]
            )
            
            # 4. Semantic Enrichment (Claude)
            logger.info("🧠 Stage 4: Semantic AI Analysis")
            # Adapt fused data to what Stage 4 expects
            enriched_data = fused_data["elements"] # Placeholder pass-through
            
            # 5. Geometry Generation (Revit Recipe)
            logger.info("🏗️ Stage 5: 3D Geometry Generation")
            formatted_elements = self._format_for_geometry(enriched_data)
            recipe = await self.geometry_gen.generate(formatted_elements)
            
            # 6. Export
            logger.info("💾 Stage 6: BIM Export (RVT + GLTF)")
            rvt_path = await self.rvt_exporter.export(recipe, job_id)
            gltf_path = await self.gltf_exporter.export(recipe, job_id)
            
            logger.info(f"✅ Pipeline Complete. RVT: {rvt_path}")
            
            return {
                "job_id": job_id,
                "status": "completed",
                "files": {
                    "rvt": rvt_path,
                    "gltf": gltf_path
                },
                "stats": {
                    "method": secure_context["method"],
                    "dpi": secure_context["dpi"],
                    "element_count": len(enriched_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Pipeline Failed: {e}")
            raise e
        finally:
            monitor.stop()
            # Clean up PyMuPDF document if needed
            # secure_context["page"].parent.close()

    def _format_for_geometry(self, fused_elements):
        """Convert list of elements back to dict expected by Stage 5"""
        output = {"walls": [], "doors": [], "windows": [], "columns": []}
        for el in fused_elements:
            etype = el["type"] + "s" # wall -> walls
            if etype in output:
                # Stage 5 expects 'bbox' and 'confidence'
                # Our fused elements have 'bbox' in PDF points
                output[etype].append(el)
        return output
