"""
Stage 2: Scale Detection & Calibration
Detects drawing scale from annotations or estimates
"""

import cv2
import pytesseract
import re
from typing import Dict, Optional, Tuple
from loguru import logger
import os
import numpy as np


class Stage2ScaleDetector:
    """Detect scale and calibrate pixels-to-mm"""
    
    def __init__(self):
        self.default_scale = int(os.getenv("DEFAULT_SCALE", 100))
        self.enable_auto = os.getenv("ENABLE_AUTO_SCALE", "true").lower() == "true"
    
    async def detect(self, image_data: Dict) -> Dict:
        """
        Detect scale from floor plan
        
        Args:
            image_data: Processed image data
            
        Returns:
            Dict with scale information
        """
        image = image_data["image"]
        
        # Try OCR to find scale notation
        scale = await self._ocr_scale_detection(image)
        
        if scale is None and self.enable_auto:
            # Try pattern matching for scale bars
            scale = await self._pattern_scale_detection(image)
        
        if scale is None:
            logger.warning(f"Could not detect scale, using default: 1:{self.default_scale}")
            scale = self.default_scale
        
        # Calculate pixel to mm conversion
        # This is simplified - actual calculation needs dimension text
        pixels_per_mm = await self._calculate_conversion(image, scale)
        
        return {
            "scale": scale,
            "scale_string": f"1:{scale}",
            "pixels_per_mm": pixels_per_mm,
            "detection_method": "ocr" if scale else "default"
        }
    
    async def _ocr_scale_detection(self, image) -> Optional[int]:
        """Use OCR to find scale notation"""
        try:
            # Run OCR on image
            text = pytesseract.image_to_string(image)
            
            # Look for scale patterns
            patterns = [
                r'1:(\d+)',           # 1:100
                r'SCALE\s*1:(\d+)',   # SCALE 1:100
                r'(\d+)mm=1m',        # 10mm=1m (1:100)
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    scale = int(match.group(1))
                    logger.info(f"Detected scale from OCR: 1:{scale}")
                    return scale
            
            # Look for dimension annotations
            # If we find "5000" or "5.0m", we can calculate scale
            dim_pattern = r'(\d+(?:\.\d+)?)\s*m'
            dims = re.findall(dim_pattern, text)
            
            if dims:
                # Use first dimension to estimate
                # This is simplified - real implementation needs more logic
                pass
            
        except Exception as e:
            logger.warning(f"OCR scale detection failed: {e}")
        
        return None
    
    async def _pattern_scale_detection(self, image) -> Optional[int]:
        """Detect scale from scale bar patterns"""
        try:
            # Look for horizontal lines with markers (scale bars)
            # This is a simplified version
            
            edges = cv2.Canny(image, 50, 150)
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi/180,
                threshold=100,
                minLineLength=100,
                maxLineGap=10
            )
            
            if lines is not None:
                # Analyze lines to find scale bar
                # Complex logic needed here
                pass
            
        except Exception as e:
            logger.warning(f"Pattern scale detection failed: {e}")
        
        return None
    
    async def _calculate_conversion(self, image, scale: int) -> float:
        """
        Calculate pixels per millimeter
        This is simplified - needs actual dimension text
        """
        # For now, estimate based on DPI and scale
        # Actual: should use detected dimension text
        
        # Assuming A3 drawing at given scale
        # 1:100 means 1mm on paper = 100mm in reality
        
        dpi = 300  # from PDF conversion
        mm_per_inch = 25.4
        pixels_per_mm_paper = dpi / mm_per_inch
        
        # If scale is 1:100, then 1mm on paper = 100mm real
        # So pixels per mm real = pixels_per_mm_paper / scale
        pixels_per_mm_real = pixels_per_mm_paper / scale
        
        return pixels_per_mm_real
