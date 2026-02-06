"""
Logging Configuration
"""

import sys
from loguru import logger
import os

def setup_logger():
    """Configure logging"""
    
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    # Add file handler
    log_file = os.getenv("LOG_FILE", "logs/app.log")
    logger.add(
        log_file,
        rotation="10 MB",
        retention="1 week",
        level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    return logger
