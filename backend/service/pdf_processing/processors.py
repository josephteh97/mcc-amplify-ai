"""
PDF Processing Layer: Track A (Vector) & Track B (Streaming Raster)
"""

import fitz
import asyncio
import numpy as np
import math
import gc
from typing import Dict, List, Any
from loguru import logger

class VectorProcessor:
    """Track A: Extract precise vector geometry"""
    
    def extract(self, page) -> Dict[str, Any]:
        """Extract all vector paths from the page"""
        logger.info("Extracting vector data...")
        
        # Extract drawings (lines, rectangles, paths)
        paths = page.get_drawings()
        
        vector_data = {
            "paths": [],
            "text": []
        }
        
        for path in paths:
            # Simplify path structure
            simplified = {
                "type": path["type"],  # s (stroke), f (fill), etc.
                "items": path["items"], # List of (op, p1, p2, ...)
                "color": path["color"],
                "width": path["width"],
                "rect": path["rect"]
            }
            vector_data["paths"].append(simplified)
            
        # Extract text for semantic context
        text_blocks = page.get_text("dict")["blocks"]
        for block in text_blocks:
            if block["type"] == 0: # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        vector_data["text"].append({
                            "text": span["text"],
                            "bbox": span["bbox"],
                            "size": span["size"]
                        })
                        
        logger.info(f"✓ Extracted {len(vector_data['paths'])} vector paths and {len(vector_data['text'])} text elements")
        return vector_data


class TiledRenderer:
    """Handle very large floor plans via tiling"""
    
    def __init__(self, tile_size_px=2000, overlap_px=128): # Smaller default for safety
        self.tile_size = tile_size_px
        self.overlap = overlap_px
    
    async def render_tiled(self, page, target_dpi=72):
        """Yield tiles one by one"""
        width_px = (page.rect.width / 72.0) * target_dpi
        height_px = (page.rect.height / 72.0) * target_dpi
        
        tiles_x = math.ceil(width_px / (self.tile_size - self.overlap))
        tiles_y = math.ceil(height_px / (self.tile_size - self.overlap))
        
        logger.info(f"Tiling large plan into {tiles_x}x{tiles_y} = {tiles_x*tiles_y} tiles")
        
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                # Calculate tile bounds
                x0 = tx * (self.tile_size - self.overlap)
                y0 = ty * (self.tile_size - self.overlap)
                x1 = min(x0 + self.tile_size, width_px)
                y1 = min(y0 + self.tile_size, height_px)
                
                # Convert back to PDF points for clipping
                rect_pts = fitz.Rect(
                    (x0 / target_dpi) * 72.0,
                    (y0 / target_dpi) * 72.0,
                    (x1 / target_dpi) * 72.0,
                    (y1 / target_dpi) * 72.0
                )
                
                # Render
                pix = page.get_pixmap(dpi=target_dpi, clip=rect_pts)
                
                # Yield for processing
                yield {
                    "pixmap": pix,
                    "rect": rect_pts,
                    "grid_pos": (tx, ty)
                }
                
                # Cleanup
                del pix
                gc.collect()
                await asyncio.sleep(0) # Yield to event loop

class StreamingProcessor:
    """Track B: Streaming workflow for large files"""
    
    def __init__(self, ml_detector):
        self.ml_detector = ml_detector
        self.vector_processor = VectorProcessor()
        self.tiler = TiledRenderer()
        
    async def process(self, page, secure_context: Dict) -> Dict:
        """Process page using strategy determined by Security Layer"""
        
        # Always run Track A (Vectors) - it's cheap and precise
        vector_data = self.vector_processor.extract(page)
        
        method = secure_context["method"]
        dpi = secure_context["dpi"]
        
        ml_detections = []
        
        if method == "direct":
            logger.info(f"Processing with Direct Rendering at {dpi} DPI")
            pix = page.get_pixmap(dpi=dpi)
            
            # Convert to numpy for ML
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3
            )
            
            # Run ML
            detections = await self.ml_detector.detect(img_array, dpi)
            ml_detections.extend(detections)
            del pix
            
        elif method == "mandatory_tiling":
            logger.info(f"Processing with Tiling at {dpi} DPI")
            async for tile in self.tiler.render_tiled(page, target_dpi=dpi):
                pix = tile["pixmap"]
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                    pix.height, pix.width, 3
                )
                
                # Run ML on tile
                tile_dets = await self.ml_detector.detect(img_array, dpi)
                
                # Adjust coordinates to global space
                for det in tile_dets:
                    # det['bbox'] is [x1, y1, x2, y2] in pixels relative to tile
                    # Need to map to global PDF points? 
                    # Actually, usually ML returns pixels. We need to normalize later.
                    # For now, let's assume ML returns normalized or we adjust here.
                    
                    # Mapping tile-pixels to global-pixels
                    tile_x = tile["grid_pos"][0] * (self.tiler.tile_size - self.tiler.overlap)
                    tile_y = tile["grid_pos"][1] * (self.tiler.tile_size - self.tiler.overlap)
                    
                    global_bbox = [
                        det['bbox'][0] + tile_x,
                        det['bbox'][1] + tile_y,
                        det['bbox'][2] + tile_x,
                        det['bbox'][3] + tile_y
                    ]
                    
                    det['bbox'] = global_bbox
                    ml_detections.append(det)
                    
        return {
            "vectors": vector_data,
            "ml_detections": ml_detections,
            "metadata": {"dpi": dpi, "method": method}
        }
