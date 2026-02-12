"""
Security & DoS Prevention Layer
"""

import os
import fitz  # PyMuPDF
import asyncio
import psutil
import gc
from typing import Dict, Optional
from loguru import logger
from async_timeout import timeout

class SecurityError(Exception):
    pass

class SecurePDFRenderer:
    """AGGRESSIVE DoS prevention for massive floor plans"""
    
    # REALISTIC HARD LIMITS (Based on typical server RAM)
    MAX_PIXEL_COUNT = 25_000_000      # 25MP (5000x5000) - MUCH LOWER
    MAX_MEMORY_MB = 512               # 512MB per page - CONSERVATIVE
    MAX_FILE_SIZE_MB = 100            # Reject huge PDFs upfront
    TIMEOUT_SECONDS = 30              # Kill if taking too long
    
    # DPI limits
    ABSOLUTE_MIN_DPI = 72             # Bare minimum (screen resolution)
    ABSOLUTE_MAX_DPI = 300            # No higher than this, ever
    
    def __init__(self):
        self.rejected_count = 0
        self.tiling_forced_count = 0
    
    async def safe_render(self, pdf_path: str) -> Dict:
        """Multi-layer defense against DoS"""
        
        # LAYER 1: File size check (BEFORE opening)
        if not os.path.exists(pdf_path):
             raise FileNotFoundError(f"File not found: {pdf_path}")

        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            raise SecurityError(
                f"File too large: {file_size_mb:.1f}MB > {self.MAX_FILE_SIZE_MB}MB limit"
            )
        
        # LAYER 2: Open with timeout
        try:
            async with timeout(self.TIMEOUT_SECONDS):
                doc = fitz.open(pdf_path)
                page = doc[0]
        except asyncio.TimeoutError:
            raise SecurityError("PDF parsing timeout - possible malicious file")
        except Exception as e:
             raise SecurityError(f"Failed to open PDF: {str(e)}")
        
        # LAYER 3: Page dimension check
        width_inches = page.rect.width / 72.0
        height_inches = page.rect.height / 72.0
        area_sq_ft = (width_inches * height_inches) / 144
        
        logger.info(f"📐 Page size: {width_inches:.1f}\" x {height_inches:.1f}\" ({area_sq_ft:.1f} sq ft)")
        
        # LAYER 4: Calculate SAFE DPI (with aggressive limits)
        safe_dpi = self._calculate_forced_dpi(page)
        
        if safe_dpi is None:
            # Even minimum DPI would exceed limits - MUST tile
            logger.warning("🔴 Page too large even at 72 DPI - mandatory tiling required")
            return {"method": "mandatory_tiling", "page": page, "dpi": 72}
        
        # LAYER 5: Pre-render memory check
        estimated_memory_mb = self._estimate_memory(page, safe_dpi)
        if estimated_memory_mb > self.MAX_MEMORY_MB:
            logger.warning(f"⚠️ Estimated {estimated_memory_mb:.1f}MB > {self.MAX_MEMORY_MB}MB - forcing tiles")
            return {"method": "mandatory_tiling", "page": page, "dpi": safe_dpi}
        
        # Safe to direct render
        return {"method": "direct", "page": page, "dpi": safe_dpi}

    def _calculate_forced_dpi(self, page) -> Optional[int]:
        """Calculate DPI that MUST fit within limits"""
        width_inches = page.rect.width / 72.0
        height_inches = page.rect.height / 72.0
        
        # Try DPI levels from high to low
        for candidate_dpi in [300, 200, 150, 100, 72]:
            pixels = (width_inches * candidate_dpi) * (height_inches * candidate_dpi)
            memory_mb = (pixels * 3) / (1024 * 1024)  # RGB
            
            if pixels <= self.MAX_PIXEL_COUNT and memory_mb <= self.MAX_MEMORY_MB:
                if candidate_dpi < 150:
                    logger.warning(f"⚠️ Large plan detected - DPI reduced to {candidate_dpi}")
                return candidate_dpi
        
        return None
    
    def _estimate_memory(self, page, dpi) -> float:
        """Conservative memory estimation"""
        width_px = (page.rect.width / 72.0) * dpi
        height_px = (page.rect.height / 72.0) * dpi
        
        # RGB image: 3 bytes per pixel
        # Add 50% overhead for PyMuPDF internal structures
        memory_bytes = (width_px * height_px * 3) * 1.5
        memory_mb = memory_bytes / (1024 * 1024)
        
        return memory_mb


class ResourceMonitor:
    """Active monitoring during processing"""
    
    def __init__(self):
        self.peak_memory_mb = 0
        self.monitoring = False
    
    def start(self):
        """Monitor memory usage in background"""
        self.monitoring = True
        asyncio.create_task(self._monitor_loop())
    
    def stop(self):
        self.monitoring = False

    async def _monitor_loop(self):
        """Check memory every 5 seconds"""
        while self.monitoring:
            try:
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / (1024 * 1024)
                
                self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)
                
                if memory_mb > 1024:  # 1GB limit
                    logger.error(f"🔴 MEMORY EXCEEDED: {memory_mb:.0f}MB")
                    # In a real app, you might want to signal a cancellation token here
                    # rather than raising an error in a background loop which might get swallowed
                    pass 
                
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                break
