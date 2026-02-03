"""
Client to communicate with Windows Revit Server
"""

import httpx
import os
from pathlib import Path
from loguru import logger


class RevitClient:
    """Client for Windows Revit API service"""
    
    def __init__(self):
        self.server_url = os.getenv("WINDOWS_REVIT_SERVER", "http://localhost:5000")
        self.api_key = os.getenv("REVIT_SERVER_API_KEY", "")
        self.timeout = int(os.getenv("REVIT_TIMEOUT", 300))
    
    async def check_health(self) -> bool:
        """Check if Windows Revit server is available"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.server_url}/health",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Cannot connect to Revit server: {e}")
            return False
    
    async def build_model(self, transaction_path: str, job_id: str) -> str:
        """
        Send transaction to Windows server to build RVT
        
        Args:
            transaction_path: Path to transaction JSON
            job_id: Job identifier
            
        Returns:
            Path to generated RVT file
        """
        logger.info(f"Sending build request to Windows Revit server for job {job_id}")
        
        # Read transaction JSON
        with open(transaction_path, 'r') as f:
            transaction_json = f.read()
        
        # Send request
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.server_url}/build-model",
                json={
                    "job_id": job_id,
                    "transaction_json": transaction_json
                },
                headers={
                    "X-API-Key": self.api_key
                }
            )
        
        if response.status_code != 200:
            raise Exception(f"Revit server error: {response.text}")
        
        # Save received RVT file
        rvt_path = f"data/models/rvt/{job_id}.rvt"
        Path(rvt_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(rvt_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"RVT file saved to {rvt_path}")
        
        return rvt_path
