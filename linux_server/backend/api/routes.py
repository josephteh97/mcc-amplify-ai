"""
API Routes
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uuid
from pathlib import Path
from loguru import logger

from core.pipeline import FloorPlanPipeline
from utils.file_handler import save_upload_file

router = APIRouter()

# Store job status in memory (use Redis for production)
job_status = {}

pipeline = FloorPlanPipeline()


class ProcessRequest(BaseModel):
    """Request model for processing"""
    project_name: Optional[str] = None


@router.post("/upload")
async def upload_floor_plan(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload PDF floor plan
    """
    # Validate file type
    if not file.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
        raise HTTPException(400, "Only PDF, JPG, PNG files are supported")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    file_path = await save_upload_file(file, job_id)
    
    # Initialize job status
    job_status[job_id] = {
        "status": "uploaded",
        "progress": 0,
        "message": "File uploaded",
        "filename": file.filename
    }
    
    logger.info(f"File uploaded: {file.filename} -> Job ID: {job_id}")
    
    return {
        "job_id": job_id,
        "filename": file.filename,
        "message": "File uploaded successfully"
    }


@router.post("/process/{job_id}")
async def process_floor_plan(
    job_id: str,
    request: ProcessRequest,
    background_tasks: BackgroundTasks
):
    """
    Start processing uploaded floor plan
    """
    if job_id not in job_status:
        raise HTTPException(404, "Job not found")
    
    # Get uploaded file path
    file_path = f"data/uploads/{job_id}.pdf"  # Simplified - adjust based on actual storage
    
    if not Path(file_path).exists():
        raise HTTPException(404, "Uploaded file not found")
    
    # Update status
    job_status[job_id]["status"] = "processing"
    job_status[job_id]["progress"] = 5
    
    # Start processing in background
    background_tasks.add_task(
        run_pipeline,
        job_id,
        file_path,
        request.project_name
    )
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Processing started"
    }


async def run_pipeline(job_id: str, file_path: str, project_name: Optional[str]):
    """Background task to run pipeline"""
    try:
        result = await pipeline.process(file_path, job_id, project_name)
        job_status[job_id] = {
            **job_status[job_id],
            "status": "completed",
            "progress": 100,
            "result": result
        }
    except Exception as e:
        logger.error(f"Pipeline failed for {job_id}: {str(e)}")
        job_status[job_id] = {
            **job_status[job_id],
            "status": "failed",
            "progress": -1,
            "error": str(e)
        }


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """
    Get processing status
    """
    if job_id not in job_status:
        raise HTTPException(404, "Job not found")
    
    return job_status[job_id]


@router.get("/download/rvt/{job_id}")
async def download_rvt(job_id: str):
    """
    Download generated RVT file
    """
    if job_id not in job_status:
        raise HTTPException(404, "Job not found")
    
    if job_status[job_id]["status"] != "completed":
        raise HTTPException(400, "Job not completed yet")
    
    rvt_path = job_status[job_id]["result"]["files"]["rvt"]
    
    if not Path(rvt_path).exists():
        raise HTTPException(404, "RVT file not found")
    
    return FileResponse(
        rvt_path,
        media_type="application/octet-stream",
        filename=f"{job_id}.rvt"
    )


@router.get("/download/gltf/{job_id}")
async def download_gltf(job_id: str):
    """
    Download glTF file for web viewer
    """
    if job_id not in job_status:
        raise HTTPException(404, "Job not found")
    
    if job_status[job_id]["status"] != "completed":
        raise HTTPException(400, "Job not completed yet")
    
    gltf_path = job_status[job_id]["result"]["files"]["gltf"]
    
    if not Path(gltf_path).exists():
        raise HTTPException(404, "glTF file not found")
    
    return FileResponse(
        gltf_path,
        media_type="model/gltf-binary",
        filename=f"{job_id}.glb"
    )


@router.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}
