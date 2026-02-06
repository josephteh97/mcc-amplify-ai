"""
File Handling Utilities
"""

import aiofiles
import os
from pathlib import Path
from fastapi import UploadFile
from loguru import logger

async def save_upload_file(file: UploadFile, job_id: str) -> Path:
    """
    Save uploaded file to disk
    
    Args:
        file: FastAPI UploadFile object
        job_id: Unique job identifier
        
    Returns:
        Path to saved file
    """
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine extension
    ext = Path(file.filename).suffix
    if not ext:
        ext = ".pdf" # Default to PDF
        
    file_path = upload_dir / f"{job_id}{ext}"
    
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
            
        logger.info(f"Saved upload to {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Failed to save upload: {e}")
        raise
