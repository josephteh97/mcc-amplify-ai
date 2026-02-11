"""
Stage 4: Semantic Analysis with Google Gemini
Using the new google-genai package
"""

import os
import json
from typing import Dict
from loguru import logger
from PIL import Image
from google import genai
from google.genai import types


class Stage4SemanticAnalyzer:
    """Use Google Gemini for semantic understanding"""
    
    def __init__(self):
        # Read from google_key.txt
        api_key = None
        key_file_path = os.path.join(os.path.dirname(__file__), '..', 'google_key.txt')
        
        try:
            with open(key_file_path, 'r') as f:
                api_key = f.read().strip()
            logger.info(f"✓ Loaded Google API key from google_key.txt")
        except FileNotFoundError:
            logger.error(f"✗ Could not find {key_file_path}")
            raise ValueError("google_key.txt not found")
        except Exception as e:
            logger.error(f"✗ Error reading API key file: {e}")
            raise
        
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in google_key.txt")
        
        # Configure Gemini client
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.0-flash-exp"  # Latest model
        logger.info("✓ Google Gemini initialized")
    
    async def analyze(
        self,
        image_data: Dict,
        detected_elements: Dict,
        scale_info: Dict
    ) -> Dict:
        """
        Analyze floor plan with Google Gemini
        
        Args:
            image_data: Processed image
            detected_elements: Elements from YOLO
            scale_info: Scale calibration
            
        Returns:
            Enriched and validated data
        """
        logger.info("Analyzing with Google Gemini...")
        
        # Convert to PIL Image
        pil_image = Image.fromarray(image_data["image"])
        
        # Create analysis prompt
        prompt = self._create_prompt(detected_elements, scale_info)
        
        # Call Gemini API with image and text
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, pil_image],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4000,
                )
            )
            
            response_text = response.text
            
            # Clean and parse JSON
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            analysis = json.loads(response_text)
            
            # Merge with detected elements
            enriched = await self._merge_data(detected_elements, analysis)
            
            logger.info("✓ Gemini analysis complete")
            
            return enriched
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON output: {e}")
            logger.error(f"Raw output: {response_text}")
            # Fallback: return detected elements without enrichment
            return detected_elements
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    def _create_prompt(self, detected_elements: Dict, scale_info: Dict) -> str:
        """Create analysis prompt for Gemini"""
        
        return f"""You are an expert architectural analyst. Analyze this floor plan image and validate/enrich the detected elements.

Detected Data:
- Scale: {scale_info['scale_string']}
- Walls: {len(detected_elements['walls'])} detected
- Doors: {len(detected_elements['doors'])} detected
- Windows: {len(detected_elements['windows'])} detected
- Rooms: {len(detected_elements['rooms'])} detected

Task: Provide architectural analysis in strict JSON format.

Required JSON schema:
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

IMPORTANT: Respond with ONLY valid JSON. No preamble, no explanation, just the JSON object."""
    
    async def _merge_data(
        self,
        detected: Dict,
        analysis: Dict
    ) -> Dict:
        """Merge detected data with Gemini's analysis"""
        
        enriched = detected.copy()
        
        # Add Gemini's validations and inferences
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
        
        # Enrich doors
        validated_doors = analysis.get("validated_elements", {}).get("doors", [])
        for i, door in enumerate(enriched["doors"]):
            if i < len(validated_doors):
                door.update(validated_doors[i])
        
        # Enrich windows
        validated_windows = analysis.get("validated_elements", {}).get("windows", [])
        for i, window in enumerate(enriched["windows"]):
            if i < len(validated_windows):
                window.update(validated_windows[i])
        
        # Enrich rooms
        validated_rooms = analysis.get("validated_elements", {}).get("rooms", [])
        for i, room in enumerate(enriched["rooms"]):
            if i < len(validated_rooms):
                room.update(validated_rooms[i])
        
        return enriched