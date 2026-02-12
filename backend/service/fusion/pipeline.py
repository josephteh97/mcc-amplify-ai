"""
Hybrid Fusion Layer: Combining Vector Precision with ML Intelligence
"""

import numpy as np
from typing import Dict, List, Any
from loguru import logger

class SpatialAlignmentEngine:
    """Ensures alignment between vector (PDF points) and raster (Pixels) space"""
    
    def __init__(self):
        self.dpi = 72 # Default PDF DPI
        self.scale_factor = 1.0

    def set_dpi(self, dpi: int):
        self.dpi = dpi
        self.scale_factor = dpi / 72.0

    def pixel_to_point(self, pixel_coords):
        """Convert [x, y] pixels to PDF points"""
        return [c / self.scale_factor for c in pixel_coords]

    def point_to_pixel(self, point_coords):
        """Convert [x, y] points to pixels"""
        return [c * self.scale_factor for c in point_coords]
    
    def bbox_pixel_to_point(self, bbox):
        """Convert [x1, y1, x2, y2] pixels to PDF points"""
        return [c / self.scale_factor for c in bbox]


class HybridFusionPipeline:
    """3-Level Fusion Strategy"""
    
    def __init__(self):
        self.aligner = SpatialAlignmentEngine()
    
    async def fuse(self, vector_data: Dict, ml_detections: List[Dict], metadata: Dict) -> Dict:
        """
        Main fusion entry point
        """
        dpi = metadata.get("dpi", 72)
        self.aligner.set_dpi(dpi)
        
        logger.info(f"Fusing {len(vector_data['paths'])} vectors with {len(ml_detections)} ML detections")
        
        # LEVEL 1: Normalize ML detections to PDF space
        normalized_detections = self._normalize_detections(ml_detections)
        
        # LEVEL 2: Geometric refinement (Snap ML boxes to nearest Vectors)
        refined_elements = self._refine_with_vectors(normalized_detections, vector_data)
        
        # LEVEL 3: Semantic enrichment (handled by Stage 4 later, but we prepare data here)
        
        return {
            "elements": refined_elements,
            "raw_vectors": vector_data,
            "metadata": metadata
        }

    def _normalize_detections(self, detections):
        """Convert all ML pixel coordinates to PDF point coordinates"""
        normalized = []
        for det in detections:
            # Assume det['bbox'] is [x1, y1, x2, y2] in pixels
            bbox_points = self.aligner.bbox_pixel_to_point(det['bbox'])
            normalized.append({
                "type": det['type'], # wall, door, etc.
                "confidence": det['confidence'],
                "bbox": bbox_points
            })
        return normalized

    def _refine_with_vectors(self, detections, vector_data):
        """
        Map "fuzzy" ML bounding boxes to precise Vector lines/rects.
        Simple heuristic: Find vector lines inside or near the ML bbox.
        """
        refined = []
        
        # Index vectors for faster search (QuadTree in production, simple loop for now)
        # For simplicity, we just pass through detections but 'snap' them if we find a matching vector line
        
        for det in detections:
            # Logic: If this is a wall, look for parallel lines in vector_data within this bbox
            # For this MVP, we will just keep the ML detection but mark it as 'unrefined' 
            # if no vector match found. In full version, we replace bbox with exact vector coords.
            
            # Placeholder for complex geometric matching
            det["geometry_source"] = "ml_approximate" 
            refined.append(det)
            
        return refined
