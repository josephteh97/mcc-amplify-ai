"""
Stage 4: Local Qwen2.5-VL Analysis
Uses local Qwen2.5-VL-7B-Instruct model for semantic analysis and control
"""

import os
import torch
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from PIL import Image
from typing import Dict, Any
from loguru import logger
import json
import io

class Stage4LocalQwenAnalyzer:
    """Use local Qwen2.5-VL for semantic understanding and recipe generation"""
    
    def __init__(self):
        # Switch to lighter model as per user request to avoid OOM
        # Default: "Qwen/Qwen2.5-VL-3B-Instruct"
        self.model_path = os.getenv("Qwen_MODEL_PATH", "Qwen/Qwen2.5-VL-3B-Instruct")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        try:
            logger.info(f"Loading Qwen2.5-VL from {self.model_path} on {self.device}...")
            
            # Load Model with memory optimization
            # 1. Use float16 (half precision)
            # 2. device_map="auto" allows offloading to CPU if GPU is full
            self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto",
                low_cpu_mem_usage=True
            )
            
            # Load Processor
            self.processor = AutoProcessor.from_pretrained(self.model_path)
            
            logger.info("Qwen2.5-VL loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Qwen2.5-VL: {str(e)}")
            raise

    async def analyze(
        self,
        image_data: Dict,
        detected_elements: Dict,
        scale_info: Dict
    ) -> Dict:
        """
        Analyze floor plan with Qwen2.5-VL
        """
        logger.info("Analyzing with Local Qwen2.5-VL...")
        
        # Prepare Image
        pil_image = Image.fromarray(image_data["image"])
        
        # Create Prompt
        prompt = self._create_prompt(detected_elements, scale_info)
        
        # Prepare Inputs
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.device)

        # Generate
        generated_ids = self.model.generate(**inputs, max_new_tokens=4096)
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        
        # Parse JSON
        try:
            # Extract JSON from code block if present
            if "```json" in output_text:
                output_text = output_text.split("```json")[1].split("```")[0].strip()
            elif "```" in output_text:
                output_text = output_text.split("```")[1].strip()
                
            analysis = json.loads(output_text)
            
            # Merge
            enriched = await self._merge_data(detected_elements, analysis)
            logger.info("Qwen analysis complete")
            return enriched
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Qwen JSON output: {e}")
            logger.error(f"Raw Output: {output_text}")
            # Fallback: return detected elements without enrichment
            return detected_elements

    def _create_prompt(self, detected_elements: Dict, scale_info: Dict) -> str:
        return f"""You are an expert architectural analyst. Analyze this floor plan image and the detected data below.
        
Data:
- Scale: {scale_info['scale_string']}
- Walls: {len(detected_elements['walls'])}
- Doors: {len(detected_elements['doors'])}
- Windows: {len(detected_elements['windows'])}

Task:
1. Validate the element types (e.g., is it a bedroom or bathroom?).
2. Infer materials (e.g., bathrooms have tiles, bedrooms have wood).
3. Identify structural logic (thick walls are concrete, thin are partition).

Output strictly valid JSON matching this schema:
{{
  "validated_elements": {{
    "walls": [
      {{ "id": 0, "material": "Concrete/Brick/Gypsum", "function": "Exterior/Interior" }}
    ],
    "rooms": [
      {{ "id": 0, "purpose": "Living/Bedroom/Bath", "flooring": "Wood/Tile/Carpet" }}
    ]
  }},
  "design_intent": "Modern/Classic"
}}
"""

    async def _merge_data(self, detected: Dict, analysis: Dict) -> Dict:
        enriched = detected.copy()
        enriched["metadata"] = {"design_intent": analysis.get("design_intent", "Unknown")}
        
        # Merge logic (simplified)
        validated_walls = analysis.get("validated_elements", {}).get("walls", [])
        for i, wall in enumerate(enriched["walls"]):
            if i < len(validated_walls):
                wall.update(validated_walls[i])
                
        return enriched

# Helper for Qwen vision processing (standard boilerplate)
from qwen_vl_utils import process_vision_info

