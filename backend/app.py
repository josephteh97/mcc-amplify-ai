"""
Main FastAPI Application
Amplify-Like Floor Plan to BIM System
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Create FastAPI app
app = FastAPI(
    title="Amplify Floor Plan AI",
    description="AI-powered PDF floor plan to native Revit (.RVT) conversion",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
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


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
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


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Amplify Floor Plan AI System")
    await ws_manager.disconnect_all()


@app.get("/")
async def root():
    """Root endpoint - serves frontend"""
    return FileResponse("../frontend/dist/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Amplify Floor Plan AI",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", 8000))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
