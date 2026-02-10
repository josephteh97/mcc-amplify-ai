"""
Main FastAPI Application
Amplify-Like Floor Plan to BIM System
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

from core.pipeline import FloorPlanPipeline
from api.routes import router as api_router
from api.websocket import manager as ws_manager
from utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Setup logging
setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting Amplify Floor Plan AI System")
    
    # Create necessary directories
    Path("data/uploads").mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    Path("data/models/revit_transactions").mkdir(parents=True, exist_ok=True)
    Path("data/models/rvt").mkdir(parents=True, exist_ok=True)
    Path("data/models/gltf").mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # Test Windows Revit server connection
    from services.revit_client import RevitClient
    revit_client = RevitClient()
    is_available = await revit_client.check_health()
    
    if is_available:
        logger.info(f"✓ Connected to Windows Revit server")
    else:
        logger.warning(f"✗ Cannot connect to Windows Revit server - RVT export will fail")
    
    logger.info("System ready!")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down Amplify Floor Plan AI System")
    await ws_manager.disconnect_all()


# Create FastAPI app with lifespan
app = FastAPI(
    title="Amplify Floor Plan AI",
    description="AI-powered PDF floor plan to native Revit (.RVT) conversion",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Serve static files (frontend build)
if Path("../frontend/dist").exists():
    app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")