from pathlib import Path
from loguru import logger
import os
import sys
import torch
import numpy as np
from typing import Dict, List, Optional
from ultralytics import YOLO

# Add this before loading the model
torch.serialization.add_safe_globals([__import__('ultralytics.nn.tasks', fromlist=['DetectionModel']).DetectionModel])


class Stage3ElementDetector:
    """Detect architectural elements using YOLOv11 with dynamic model support"""

    def __init__(self):
        self.weights_dir = Path(os.getenv("YOLO_WEIGHTS_DIR", "ml/weights"))
        logger.info(f"YOLOv11_model_path_directory: {self.weights_dir}")

        self.confidence = float(os.getenv("DETECTION_CONFIDENCE", 0.6))
        self.nms_threshold = float(os.getenv("NMS_THRESHOLD", 0.4))

        # Initialize models map
        self.models = {}
        self._load_models()

    def _load_models(self):
        """
        Load YOLO model for element detection.
        Loads yolov11_floorplan.pt (monolithic model).
        If not found, prompts user whether to proceed with base model.
        """
        
        # Check for specialized models first (optional feature)
        specialized_found = False
        specialized_types = ['wall', 'door', 'window', 'column']

        for e_type in specialized_types:
            weight_path = self.weights_dir / f"{e_type}.pt"
            if weight_path.exists():
                logger.info(f"Loading specialized model for {e_type}: {weight_path}")
                self.models[e_type] = YOLO(str(weight_path))
                specialized_found = True

        # If no specialized models, load monolithic model (your main model)
        if not specialized_found:
            model_path = self.weights_dir / "yolov11_floorplan.pt"
            
            # logger.info(f"Looking for custom model at: {model_path}")
            # logger.info(f"Absolute path: {model_path.resolve()}")
            
            # Check if custom model exists
            if model_path.exists() and model_path.is_file():
                file_size_mb = model_path.stat().st_size / (1024 * 1024)
                logger.info(f"✓ Found custom model: {model_path.name} ({file_size_mb:.1f} MB)")
                
                try:
                    logger.info("Loading custom YOLO model...")
                    self.models['all'] = YOLO(str(model_path))
                    logger.success(f"✓ Successfully loaded custom model: yolov11_floorplan.pt")
                    # logger.info("Model ready for element detection (columns, beams, slabs, grid lines)")
                    return  # Success - exit method
                    
                except Exception as e:
                    logger.error(f"✗ Failed to load custom model: {e}")
                    logger.warning("The model file exists but cannot be loaded. It may be corrupted.")
                    # Fall through to user prompt
            else:
                logger.warning(f"✗ Custom model not found at: {model_path}")
                
                # Show what's in the weights directory
                if self.weights_dir.exists():
                    logger.info(f"Contents of {self.weights_dir}:")
                    weights_found = False
                    for item in self.weights_dir.iterdir():
                        logger.info(f"  - {item.name}")
                        weights_found = True
                    if not weights_found:
                        logger.info("  (directory is empty)")
                else:
                    logger.warning(f"Weights directory does not exist: {self.weights_dir}")
                    logger.info(f"Creating directory: {self.weights_dir}")
                    self.weights_dir.mkdir(parents=True, exist_ok=True)
            
            # Model not found or failed to load - ask user what to do
            logger.warning("=" * 70)
            logger.warning("CUSTOM MODEL NOT FOUND OR FAILED TO LOAD")
            logger.warning("=" * 70)
            logger.warning("")
            logger.warning("The trained model 'yolov11_floorplan.pt' was not found or is corrupted.")
            logger.warning("This model is required for accurate detection of:")
            logger.warning("  - Columns")
            logger.warning("  - Beams")
            logger.warning("  - Slabs")
            logger.warning("  - Grid Lines")
            logger.warning("")
            logger.warning("Options:")
            logger.warning("  1. Train the model first (RECOMMENDED)")
            logger.warning("     cd backend/training")
            logger.warning("     python train_yolo.py ./columns-and-ducts-detection-1")
            logger.warning("")
            logger.warning("  2. Use base YOLOv8n model (POOR ACCURACY - testing only)")
            logger.warning("=" * 70)
            logger.warning("")
            
            # Ask user for confirmation
            print("\n" + "⚠" * 35)
            print("WARNING: Custom model not found or failed to load!")
            print("⚠" * 35)
            
            try:
                response = input("\nDo you want to proceed with base YOLOv8n model? (yes/no): ").strip().lower()
                
                if response in ['yes', 'y']:
                    logger.warning("User chose to proceed with base YOLOv8n model")
                    logger.warning("⚠ WARNING: Base model is NOT trained for construction elements!")
                    logger.warning("⚠ Detection accuracy will be VERY POOR until you train a custom model.")
                    
                    try:
                        logger.info("Loading base YOLOv8n model...")
                        self.models['all'] = YOLO('yolov8n.pt')
                        logger.warning("✓ Loaded base YOLOv8n (UNTRAINED - for testing only)")
                        
                    except Exception as e:
                        logger.error(f"✗ Failed to load base model: {e}")
                        logger.error("Cannot proceed without a model. Exiting.")
                        sys.exit(1)
                else:
                    logger.info("User chose not to proceed without custom model")
                    logger.info("\nPlease train the model first:")
                    logger.info("  1. cd backend/training")
                    logger.info("  2. python download_data.py YOUR_ROBOFLOW_API_KEY")
                    logger.info("  3. python train_yolo.py ./columns-and-ducts-detection-1")
                    logger.info("  4. cp runs/detect/train/weights/best.pt ../ml/weights/yolov11_floorplan.pt")
                    logger.info("\nExiting...")
                    sys.exit(0)
                    
            except KeyboardInterrupt:
                logger.info("\n\nInterrupted by user. Exiting...")
                sys.exit(0)

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
        override_type: Optional[str] = None
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

        aspect_ratio = width_px / height_px if height_px > 0 else 1
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