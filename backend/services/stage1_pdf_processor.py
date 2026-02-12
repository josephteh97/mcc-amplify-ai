"""
Stage 1: PDF Processing
Converts PDF to high-resolution image
"""

import fitz  # PyMuPDF
from PIL import Image
import numpy as np
from typing import Dict
from loguru import logger
import os

# INCREASE PIL IMAGE SIZE LIMIT
# Image.MAX_IMAGE_PIXELS = None  # Remove limit entirely
# OR set a higher limit:
Image.MAX_IMAGE_PIXELS = 500000000  # 500 million pixels  normally 139493228 for A0 paper


class Stage1PDFProcessor:
    """Convert PDF to processable image format"""
    
    def __init__(self, dpi: int = 300):
        """
        Args:
            dpi: Resolution for PDF conversion (default 300)
                 Lower DPI = smaller images, faster processing
                 Higher DPI = more detail, slower processing
        """
        self.dpi = dpi
        # For very large PDFs, you might want to use 150 or 200 DPI
        self.max_dimension = 8000  # Maximum width or height in pixels
    
    async def process(self, pdf_path: str) -> Dict:
        """
        Convert PDF to image
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dict with image data and metadata
        """
        logger.info(f"Processing PDF: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Open PDF
        doc = fitz.open(pdf_path)
        
        if len(doc) == 0:
            raise ValueError("PDF has no pages")
        
        # Get first page (floor plans are usually single page)
        page = doc[0]
        
        # Calculate zoom based on DPI
        zoom = self.dpi / 72  # 72 is default PDF DPI
        mat = fitz.Matrix(zoom, zoom)
        
        # Render page to image
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Check if image is too large and resize if needed
        width, height = img.size
        max_dim = max(width, height)
        
        if max_dim > self.max_dimension:
            logger.warning(
                f"Image too large ({width}x{height}), resizing to fit {self.max_dimension}px"
            )
            scale = self.max_dimension / max_dim
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Resized to {new_width}x{new_height}")
        
        # Convert to numpy array
        image_array = np.array(img)
        
        doc.close()
        
        logger.info(f"PDF converted: {image_array.shape}")
        
        return {
            "image": image_array,
            "width": image_array.shape[1],
            "height": image_array.shape[0],
            "original_pdf": pdf_path
        }