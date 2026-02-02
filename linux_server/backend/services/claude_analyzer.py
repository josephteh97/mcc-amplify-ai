"""
Stage 4: Semantic Analysis with Claude AI
Validates and enriches detected data
"""

import anthropic
import os
import base64
import json
from typing import Dict
from loguru import logger
from PIL import Image
import io


class ClaudeAnalyzer:
    """Use Claude AI for semantic understanding"""
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
    
    async def analyze(
        self,
        image_data: Dict,
        detected_elements: Dict,
        scale_info: Dict
    ) -> Dict:
        """
        Analyze floor plan with Claude AI
        
        Args:
            image_data: Processed image
            detected_elements: Elements from YOLO
            scale_info: Scale calibration
            
        Returns:
            Enriched and validated data
        """
        logger.info("Analyzing with Claude AI...")
        
        # Convert image to base64
        image = image_data["image"]
        image_b64 = await self._image_to_base64(image)
        
        # Create analysis prompt
        prompt = self._create_prompt(detected_elements, scale_info)
        
        # Call Claude API
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )
        
        # Parse response
        response_text = message.content[0].text
        
        # Clean and parse JSON
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        analysis = json.loads(response_text)
        
        # Merge with detected elements
        enriched = await self._merge_data(detected_elements, analysis)
        
        logger.info("Claude analysis complete")
        
        return enriched
    
    async def _image_to_base64(self, image) -> str:
        """Convert numpy image to base64"""
        pil_image = Image.fromarray(image)
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode()
    
    def _create_prompt(self, detected_elements: Dict, scale_info: Dict) -> str:
        """Create analysis prompt for Claude"""
        
        return f"""You are an expert architectural analyst. Analyze this floor plan and validate/enrich the detected elements.

Detected Data:
- Scale: {scale_info['scale_string']}
- Walls: {len(detected_elements['walls'])} detected
- Doors: {len(detected_elements['doors'])} detected
- Windows: {len(detected_elements['windows'])} detected
- Rooms: {len(detected_elements['rooms'])} detected

Please provide analysis in JSON format:

{{
  "building_type": "residential/commercial/mixed",
  "construction_type": "concrete/timber/steel",
  "floor_count": 1,
  "validated_elements": {{
    "walls": [
      {{
        "id": 0,
        "type": "exterior/interior",
        "material": "concrete/brick/gypsum",
        "structural": true/false,
        "fire_rating": "1HR/2HR/none"
      }}
    ],
    "doors": [
      {{
        "id": 0,
        "purpose": "main_entrance/bedroom/bathroom",
        "fire_rated": true/false,
        "accessibility": "compliant/non-compliant"
      }}
    ],
    "windows": [
      {{
        "id": 0,
        "orientation": "north/south/east/west",
        "operable": true/false
      }}
    ],
    "rooms": [
      {{
        "id": 0,
        "name": "Living Room",
        "purpose": "living/bedroom/kitchen/bathroom",
        "area_sqm": 25.5,
        "ceiling_height": 2800
      }}
    ]
  }},
  "inferred_properties": {{
    "total_floor_area": 120.5,
    "building_code_compliance": "compliant/check_required",
    "suggested_improvements": ["list of suggestions"]
  }},
  "quality_checks": {{
    "walls_form_closed_rooms": true/false,
    "doors_properly_placed": true/false,
    "structural_integrity": "good/check_required",
    "issues_found": ["list of issues"]
  }}
}}

Respond ONLY with valid JSON, no preamble."""
    
    async def _merge_data(
        self,
        detected: Dict,
        analysis: Dict
    ) -> Dict:
        """Merge detected data with Claude's analysis"""
        
        enriched = detected.copy()
        
        # Add Claude's validations and inferences
        enriched["metadata"] = {
            "building_type": analysis.get("building_type"),
            "construction_type": analysis.get("construction_type"),
            "total_floor_area": analysis.get("inferred_properties", {}).get("total_floor_area")
        }
        
        # Enrich walls
        validated_walls = analysis.get("validated_elements", {}).get("walls", [])
        for i, wall in enumerate(enriched["walls"]):
            if i < len(validated_walls):
                wall.update(validated_walls[i])
        
        # Similar for doors, windows, rooms
        
        return enriched
