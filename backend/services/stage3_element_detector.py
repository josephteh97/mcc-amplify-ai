"""
Stage 3: AI Element Detection
Uses YOLOv8 to detect walls, doors, windows, etc.
Supports dynamic model loading (single .pt vs specialized)
"""

from ultralytics import YOLO
import cv2
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
from loguru import logger
import os


class Stage3ElementDetector:
    """Detect architectural elements using YOLOv8 with dynamic model support"""
    
    def __init__(self):
        self.weights_dir = Path(os.getenv("YOLO_WEIGHTS_DIR", "ml_models/weights"))
        self.confidence = float(os.getenv("DETECTION_CONFIDENCE", 0.6))
        self.nms_threshold = float(os.getenv("NMS_THRESHOLD", 0.4))
        
        # Initialize models map
        self.models = {}
        self._load_models()
    
    def _load_models(self):
        """Load available YOLO models dynamically"""
        
        # Check for specialized models first
        specialized_found = False
        specialized_types = ['wall', 'door', 'window', 'column']
        
        for e_type in specialized_types:
            weight_path = self.weights_dir / f"{e_type}.pt"
            if weight_path.exists():
                logger.info(f"Loading specialized model for {e_type}: {weight_path}")
                self.models[e_type] = YOLO(str(weight_path))
                specialized_found = True
        
        # If no specialized models, or incomplete, check for monolithic model
        if not specialized_found:
            monolithic_path = self.weights_dir / "yolov8_floorplan.pt"
            if monolithic_path.exists():
                logger.info(f"Loading monolithic model: {monolithic_path}")
                self.models['all'] = YOLO(str(monolithic_path))
            else:
                logger.warning("No custom weights found. Using base YOLOv8n (will need fine-tuning)")
                self.models['all'] = YOLO('yolov8n.pt')
    
    async def detect(self, image_data: Dict, scale_info: Dict) -> Dict:
        """
        Detect architectural elements
        """
        image = image_data["image"]
        pixels_per_mm = scale_info["pixels_per_mm"]
        
        elements = {
            "walls": [], "doors": [], "windows": [], 
            "stairs": [], "rooms": [], "fixtures": [], "columns": []
        }
        
        # Run detection
        if 'all' in self.models:
            # Monolithic detection
            results = self.models['all'].predict(
                image, conf=self.confidence, iou=self.nms_threshold, verbose=False
            )
            await self._process_results(results, elements, image, pixels_per_mm)
        else:
            # Specialized detection
            for e_type, model in self.models.items():
                logger.info(f"Running detection for {e_type}...")
                results = model.predict(
                    image, conf=self.confidence, iou=self.nms_threshold, verbose=False
                )
                # Note: Specialized models usually output class 0 for their specific type
                # We need to map that correctly
                await self._process_results(results, elements, image, pixels_per_mm, override_type=e_type)
        
        # Post-processing
        elements = await self._post_process(elements, image, pixels_per_mm)
        
        logger.info(f"Detected: {len(elements['walls'])} walls, "
                   f"{len(elements['doors'])} doors, "
                   f"{len(elements['windows'])} windows")
        
        return elements
    
    async def _process_results(
        self, 
        results, 
        elements_dict: Dict, 
        image: np.ndarray, 
        pixels_per_mm: float,
        override_type: str = None
    ):
        """Process YOLO results and populate elements dict"""
        for result in results:
            boxes = result.boxes
            for box in boxes:
                confidence = float(box.conf[0])
                bbox = box.xyxy[0].cpu().numpy()
                
                if override_type:
                    element_type = override_type
                else:
                    class_id = int(box.cls[0])
                    element_type = self._map_class_to_type(class_id)
                
                if element_type:
                    element = await self._parse_element(
                        element_type, bbox, confidence, image, pixels_per_mm
                    )
                    # Append to correct list (pluralized key)
                    key = element_type + "s"
                    if key in elements_dict:
                        elements_dict[key].append(element)

    def _map_class_to_type(self, class_id: int) -> Optional[str]:
        """Map YOLO class ID to element type"""
        mapping = {
            0: "wall", 1: "door", 2: "window", 
            3: "stair", 4: "room", 5: "fixture", 6: "column"
        }
        return mapping.get(class_id)
    
    async def _parse_element(
        self,
        element_type: str,
        bbox: np.ndarray,
        confidence: float,
        image: np.ndarray,
        pixels_per_mm: float
    ) -> Dict:
        """Parse detected element into structured data"""
        
        x1, y1, x2, y2 = bbox
        width_px = x2 - x1
        height_px = y2 - y1
        
        width_mm = width_px / pixels_per_mm
        height_mm = height_px / pixels_per_mm
        
        element = {
            "type": element_type,
            "bbox": [int(x1), int(y1), int(x2), int(y2)],
            "confidence": confidence,
            "center": [int((x1 + x2) / 2), int((y1 + y2) / 2)],
            "dimensions": {
                "width_mm": width_mm,
                "height_mm": height_mm
            }
        }
        
        # Extract additional features based on type
        if element_type == "wall":
            element.update(await self._analyze_wall(bbox, image))
        elif element_type == "door":
            element.update(await self._analyze_door(bbox, image))
        elif element_type == "window":
            element.update(await self._analyze_window(bbox, image))
        elif element_type == "column":
            element.update(await self._analyze_column(bbox, image))
        
        return element
    
    async def _analyze_column(self, bbox, image) -> Dict:
        """Extract column-specific features"""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        width_px = x2 - x1
        height_px = y2 - y1
        
        aspect_ratio = width_px / height_px
        is_circular = 0.9 < aspect_ratio < 1.1 
        
        return {
            "column_shape": "circular" if is_circular else "rectangular",
            "material": "Concrete"
        }
    
    async def _analyze_wall(self, bbox, image) -> Dict:
        """Extract wall-specific features"""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        wall_region = image[y1:y2, x1:x2]
        thickness = await self._estimate_line_thickness(wall_region)
        is_exterior = thickness > 200  # mm
        
        return {
            "thickness": thickness,
            "wall_function": "exterior" if is_exterior else "interior",
            "endpoints": [
                [int(x1), int((y1 + y2) / 2)],
                [int(x2), int((y1 + y2) / 2)]
            ]
        }
    
    async def _analyze_door(self, bbox, image) -> Dict:
        """Extract door-specific features"""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        door_region = image[y1:y2, x1:x2]
        swing = await self._detect_door_swing(door_region)
        width = x2 - x1
        door_type = "double" if width > 1800 else "single"
        
        return {
            "door_type": door_type,
            "swing_direction": swing,
            "width": width
        }
    
    async def _analyze_window(self, bbox, image) -> Dict:
        return {"window_type": "fixed", "has_sill": True}
    
    async def _estimate_line_thickness(self, region: np.ndarray) -> float:
        return 200.0  # mm
    
    async def _detect_door_swing(self, region: np.ndarray) -> str:
        return "right"
    
    async def _post_process(self, elements: Dict, image: np.ndarray, pixels_per_mm: float) -> Dict:
        """Post-process detected elements"""
        # Simplified post-processing logic
        elements["walls"] = await self._connect_walls(elements["walls"])
        elements["doors"] = await self._assign_to_walls(elements["doors"], elements["walls"])
        elements["windows"] = await self._assign_to_walls(elements["windows"], elements["walls"])
        elements["rooms"] = await self._detect_rooms(elements["walls"], image)
        return elements
    
    async def _connect_walls(self, walls: List[Dict]) -> List[Dict]:
        return walls
    
    async def _assign_to_walls(self, openings: List[Dict], walls: List[Dict]) -> List[Dict]:
        for opening in openings:
            opening["host_wall_id"] = 0
        return openings
    
    async def _detect_rooms(self, walls: List[Dict], image: np.ndarray) -> List[Dict]:
        return []
