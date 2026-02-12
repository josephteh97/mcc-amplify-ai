"""
Stage 7: RVT Exporter
Handles communication with Windows Revit Server to generate .RVT files
"""

from backend.services.revit_client import RevitClient

class RvtExporter:
    def __init__(self):
        self.client = RevitClient()
        
    async def export(self, transaction_path: str, job_id: str) -> str:
        """Build model on Windows server and return path to RVT"""
        return await self.client.build_model(transaction_path, job_id)
