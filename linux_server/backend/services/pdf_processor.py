"""
Stage 1: PDF Processing & Preprocessing
Converts PDF to high-resolution images
"""

import fitz  # PyMuPDF
from pdf2image import convert_from_path
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Dict, List
from loguru import logger
import os


class PDFProcessor:
    """Process PDF floor plans into analyzable images"""
    
    def __init__(self):
        self.dpi = int(os.getenv("PDF_DPI", 300))
        self.max_size = int(os.getenv("IMAGE_MAX_SIZE", 4096))
    
    async def process(self, pdf_path: str) -> Dict:
        """
        Convert PDF to high-resolution image
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dict with image data and metadata
        """
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Try to extract vector data first
        has_vector = await self._try_extract_vector(pdf_path)
        
        # Convert to raster image
        images = convert_from_path(
            pdf_path,
            dpi=self.dpi,
            fmt='png'
        )
        
        if not images:
            raise ValueError("Failed to convert PDF to image")
        
        # Use first page (support multi-page later)
        image = images[0]
        
        # Convert PIL to numpy
        image_np = np.array(image)
        
        # Preprocess image
        processed = await self._preprocess_image(image_np)
        
        return {
            "image": processed,
            "original_size": image_np.shape,
            "has_vector_data": has_vector,
            "dpi": self.dpi
        }
    
    async def _try_extract_vector(self, pdf_path: str) -> bool:
        """Try to extract vector data from PDF"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Check for vector paths
            paths = page.get_drawings()
            
            doc.close()
            
            return len(paths) > 0
            
        except Exception as e:
            logger.warning(f"Could not extract vector data: {e}")
            return False
    
    async def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance image quality for better detection
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Binarization (threshold)
        _, binary = cv2.threshold(
            enhanced, 
            0, 
            255, 
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        
        # Resize if too large
        h, w = binary.shape
        if max(h, w) > self.max_size:
            scale = self.max_size / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            binary = cv2.resize(binary, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        return binary
