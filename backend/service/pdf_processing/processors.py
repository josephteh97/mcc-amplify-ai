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
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """Extract all vector paths from PDF file"""
        logger.info("Extracting vector data...")
        
        # Open document HERE - keep it alive during extraction
        doc = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]  # Get first page
            
            # Extract drawings (lines, rectangles, paths)
            paths = page.get_drawings()
            
            vector_data = {
                "paths": [],
                "text": []
            }
            
            for path in paths:
                # Simplify path structure
                simplified = {
                    "type": path.get("type", ""),
                    "items": path.get("items", []),
                    "color": path.get("color"),
                    "width": path.get("width", 0),
                    "rect": path.get("rect")
                }
                vector_data["paths"].append(simplified)
                
            # Extract text for semantic context
            text_blocks = page.get_text("dict")["blocks"]
            for block in text_blocks:
                if block["type"] == 0:  # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            vector_data["text"].append({
                                "text": span["text"],
                                "bbox": span["bbox"],
                                "size": span["size"],
                                "font": span["font"]
                            })
            
            logger.info(f"Extracted {len(vector_data['paths'])} paths, {len(vector_data['text'])} text blocks")
            return vector_data
            
        except Exception as e:
            logger.error(f"Vector extraction failed: {e}")
            raise
        finally:
            # Close document after extraction
            if doc is not None:
                doc.close()


class StreamingProcessor:
    """Track B: Safe rendering with memory management"""
    
    def __init__(self, ml_detector=None):
        self.ml_detector = ml_detector
        self.vector_processor = VectorProcessor()
    
    async def extract(self, pdf_path: str) -> Dict[str, Any]:
        """Extract vector data (wrapper for VectorProcessor)"""
        return self.vector_processor.extract(pdf_path)
    
    async def render_safe(self, pdf_path: str, dpi: int = 300) -> Dict[str, Any]:
        """Render PDF page to image safely"""
        logger.info(f"Rendering PDF at {dpi} DPI...")
        
        doc = None
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Get page dimensions
            width_inches = page.rect.width / 72.0
            height_inches = page.rect.height / 72.0
            
            # Calculate safe DPI
            max_pixels = 25_000_000  # 25MP limit
            pixel_width = width_inches * dpi
            pixel_height = height_inches * dpi
            total_pixels = pixel_width * pixel_height
            
            if total_pixels > max_pixels:
                # Reduce DPI to stay within limits
                safe_dpi = int(math.sqrt(max_pixels / (width_inches * height_inches)))
                logger.warning(f"Reducing DPI from {dpi} to {safe_dpi} for safety")
                dpi = safe_dpi
            
            # Render page
            pix = page.get_pixmap(dpi=dpi)
            
            # Convert to numpy array BEFORE closing doc
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3
            )
            
            result = {
                "image": img_array.copy(),  # Copy to detach from pixmap
                "width": pix.width,
                "height": pix.height,
                "dpi": dpi
            }
            
            # Clean up pixmap
            pix = None
            gc.collect()
            
            logger.info(f"Rendered image: {result['width']}x{result['height']} at {dpi} DPI")
            return result
            
        except Exception as e:
            logger.error(f"Rendering failed: {e}")
            raise
        finally:
            if doc is not None:
                doc.close()
