"""
Stage 3: AI Element Detection
Uses YOLOv8 to detect walls, doors, windows, etc.
"""

from ultralytics import YOLO
import cv2
import numpy as np
from typing import Dict, List
from pathlib import Path
from loguru import logger
import os


class ElementDetector:
    """Detect architectural elements using YOLOv8"""
    
    def __init__(self):
        weights_path = os.getenv(
            "YOLO_WEIGHTS_PATH",
            "ml_models/weights/yolov8_floorplan.pt"
        )
        
        # Load YOLO model
        if Path(weights_path).exists():
            self.model = YOLO(weights_path)
            logger.info(f"Loaded custom YOLO model from {weights_path}")
        else:
            # Use pre-trained model (will need fine-tuning)
            self.model = YOLO('yolov8n.pt')
            logger.warning("Using base YOLOv8 model - consider training custom model")
        
        self.confidence = float(os.getenv("DETECTION_CONFIDENCE", 0.6))
        self.nms_threshold = float(os.getenv("NMS_THRESHOLD", 0.4))
    
    async def detect(self, image_data: Dict, scale_info: Dict) -> Dict:
        """
        Detect architectural elements
        
        Args:
            image_data: Preprocessed image
            scale_info: Scale calibration data
            
        Returns:
            Dict with detected elements
        """
        image = image_data["image"]
        pixels_per_mm = scale_info["pixels_per_mm"]
        
        # Run YOLO detection
        results = self.model.predict(
            image,
            conf=self.confidence,
            iou=self.nms_threshold,
            verbose=False
        )
        
        # Parse results
        elements = {
            "walls": [],
            "doors": [],
            "windows": [],
            "stairs": [],
            "rooms": [],
            "fixtures": []
        }
        
        for result in results:
            boxes = result.boxes
            
            for i, box in enumerate(boxes):
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                bbox = box.xyxy[0].cpu().numpy()
                
                # Map class ID to element type
                element_type = self._map_class_to_type(class_id)
                
                if element_type:
                    element = await self._parse_element(
                        element_type,
                        bbox,
                        confidence,
                        image,
                        pixels_per_mm
                    )
                    
                    elements[element_type + "s"].append(element)
        
        # Post-processing
        elements = await self._post_process(elements, image, pixels_per_mm)
        
        logger.info(f"Detected: {len(elements['walls'])} walls, "
                   f"{len(elements['doors'])} doors, "
                   f"{len(elements['windows'])} windows")
        
        return elements
    
    def _map_class_to_type(self, class_id: int) -> Optional[str]:
        """Map YOLO class ID to element type"""
        # This mapping depends on your trained model
        # Example mapping:
        mapping = {
            0: "wall",
            1: "door",
            2: "window",
            3: "stair",
            4: "room",
            5: "fixture"
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
        
        # Calculate real-world dimensions
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
        
        return element
    
    async def _analyze_wall(self, bbox, image) -> Dict:
        """Extract wall-specific features"""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        wall_region = image[y1:y2, x1:x2]
        
        # Estimate thickness from line width
        thickness = await self._estimate_line_thickness(wall_region)
        
        # Determine if exterior or interior (based on thickness)
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
        
        # Detect swing direction from arc
        swing = await self._detect_door_swing(door_region)
        
        width = x2 - x1
        
        # Classify door type
        if width > 1800:
            door_type = "double"
        else:
            door_type = "single"
        
        return {
            "door_type": door_type,
            "swing_direction": swing,
            "width": width
        }
    
    async def _analyze_window(self, bbox, image) -> Dict:
        """Extract window-specific features"""
        # Similar to door analysis
        return {
            "window_type": "fixed",  # Simplified
            "has_sill": True
        }
    
    async def _estimate_line_thickness(self, region: np.ndarray) -> float:
        """Estimate wall thickness from line width"""
        # Simplified - actual implementation more complex
        return 200.0  # mm
    
    async def _detect_door_swing(self, region: np.ndarray) -> str:
        """Detect door swing direction"""
        # Look for arc pattern
        # Simplified
        return "right"
    
    async def _post_process(
        self,
        elements: Dict,
        image: np.ndarray,
        pixels_per_mm: float
    ) -> Dict:
        """Post-process detected elements"""
        
        # Connect walls that should be continuous
        elements["walls"] = await self._connect_walls(elements["walls"])
        
        # Find which wall each door/window belongs to
        elements["doors"] = await self._assign_to_walls(
            elements["doors"],
            elements["walls"]
        )
        elements["windows"] = await self._assign_to_walls(
            elements["windows"],
            elements["walls"]
        )
        
        # Detect rooms from wall boundaries
        elements["rooms"] = await self._detect_rooms(elements["walls"], image)
        
        return elements
    
    async def _connect_walls(self, walls: List[Dict]) -> List[Dict]:
        """Connect wall segments that form continuous walls"""
        # Complex geometry logic here
        return walls
    
    async def _assign_to_walls(self, openings: List[Dict], walls: List[Dict]) -> List[Dict]:
        """Assign doors/windows to their host walls"""
        for opening in openings:
            # Find nearest wall
            opening["host_wall_id"] = 0  # Simplified
        return openings
    
    async def _detect_rooms(self, walls: List[Dict], image: np.ndarray) -> List[Dict]:
        """Detect rooms from wall boundaries"""
        # Use contour detection to find enclosed spaces
        rooms = []
        # Complex logic here
        return rooms

