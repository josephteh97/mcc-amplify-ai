"""
Stage 5: Semantic 3D Generation
Converts 2D detected elements to Semantic 3D parameters for Revit Solid Modeling.
This stage focuses on building instructions for Revit, not boundary representation meshes.
"""

import numpy as np
import trimesh
from typing import Dict, List, Optional
from loguru import logger
from pathlib import Path
import json


class GeometryBuilder:
    """Build Semantic 3D parameters for native Revit solid objects"""
    
    def __init__(self):
        # Default architectural standards (mm)
        self.default_wall_height = 2800  
        self.default_wall_thickness = 200  
        self.default_door_height = 2100  
        self.default_window_height = 1500  
        self.default_sill_height = 900  
        self.default_floor_thickness = 200  

    async def build(self, enriched_data: Dict, scale_info: Dict) -> Dict:
        """
        Build Semantic 3D parameters from enriched analysis data.
        
        Args:
            enriched_data: Data from Claude analysis + YOLO
            scale_info: Scale calibration data
            
        Returns:
            Dict containing semantic parameters for Revit Solid Modeling
        """
        logger.info("Generating Semantic 3D parameters for Revit...")
        
        pixels_per_mm = scale_info["pixels_per_mm"]
        
        # We focus on parameters (Location, Direction, Type) instead of Mesh data
        geometry = {
            "walls": await self._build_wall_parameters(enriched_data["walls"], pixels_per_mm),
            "doors": await self._build_opening_parameters(enriched_data["doors"], pixels_per_mm, "door"),
            "windows": await self._build_opening_parameters(enriched_data["windows"], pixels_per_mm, "window"),
            "rooms": await self._build_room_parameters(enriched_data["rooms"], pixels_per_mm),
            "floors": await self._build_slab_parameters(enriched_data.get("rooms", []), pixels_per_mm, "floor"),
            "ceilings": await self._build_slab_parameters(enriched_data.get("rooms", []), pixels_per_mm, "ceiling"),
            "metadata": enriched_data.get("metadata", {})
        }
        
        logger.info(f"Generated instructions for: {len(geometry['walls'])} Native Walls, "
                   f"{len(geometry['doors'])} Native Doors, "
                   f"{len(geometry['windows'])} Native Windows")
        
        return geometry

    async def _build_wall_parameters(self, walls_2d: List[Dict], pixels_per_mm: float) -> List[Dict]:
        """Generate parameters for Revit Wall.Create (Solid Modeling)"""
        walls_params = []
        
        for wall in walls_2d:
            # Convert pixel coordinates to real-world mm coordinates
            start_px = wall["endpoints"][0]
            end_px = wall["endpoints"][1]
            
            # Revit uses a Cartesian coordinate system
            start_mm = [p / pixels_per_mm for p in start_px]
            end_mm = [p / pixels_per_mm for p in end_px]
            
            wall_param = {
                "id": wall.get("id"),
                "start_point": {"x": start_mm[0], "y": start_mm[1], "z": 0},
                "end_point": {"x": end_mm[0], "y": end_mm[1], "z": 0},
                "thickness": wall.get("thickness", self.default_wall_thickness),
                "height": wall.get("ceiling_height", self.default_wall_height),
                "material": wall.get("material", "Concrete"),
                "is_structural": wall.get("structural", False),
                "function": wall.get("wall_function", "Interior")
            }
            walls_params.append(wall_param)
            
        return walls_params

    async def _build_opening_parameters(self, openings_2d: List[Dict], pixels_per_mm: float, o_type: str) -> List[Dict]:
        """Generate parameters for FamilyInstance creation (Doors/Windows)"""
        opening_params = []
        for op in openings_2d:
            center_mm = [p / pixels_per_mm for p in op["center"]]
            
            param = {
                "id": op.get("id"),
                "location": {"x": center_mm[0], "y": center_mm[1], "z": 0 if o_type == "door" else self.default_sill_height},
                "width": op.get("width", 900 if o_type == "door" else 1200),
                "height": op.get("height", self.default_door_height if o_type == "door" else self.default_window_height),
                "type_name": op.get("door_type" if o_type == "door" else "window_type", "Standard"),
                "host_wall_id": op.get("host_wall_id")
            }
            
            if o_type == "door":
                param["swing_direction"] = op.get("swing_direction", "Right")
                
            opening_params.append(param)
        return opening_params

    async def _build_room_parameters(self, rooms_2d: List[Dict], pixels_per_mm: float) -> List[Dict]:
        """Generate parameters for Revit Room creation"""
        room_params = []
        for room in rooms_2d:
            center_mm = [p / pixels_per_mm for p in room["center"]]
            
            param = {
                "id": room.get("id"),
                "name": room.get("name", "Unnamed Room"),
                "purpose": room.get("purpose", "General"),
                "center_point": {"x": center_mm[0], "y": center_mm[1], "z": 0},
                "area_sqm": room.get("area_sqm", 0),
                "target_height": room.get("ceiling_height", self.default_wall_height)
            }
            room_params.append(param)
        return room_params

    async def _build_slab_parameters(self, rooms_2d: List[Dict], pixels_per_mm: float, s_type: str) -> List[Dict]:
        """Generate parameters for Revit Floor/Ceiling creation (Solid Slabs)"""
        slab_params = []
        for i, room in enumerate(rooms_2d):
            if "boundary" in room:
                boundary_mm = [{"x": p[0]/pixels_per_mm, "y": p[1]/pixels_per_mm} for p in room["boundary"]]
                param = {
                    "id": f"{s_type}_{i}",
                    "boundary_points": boundary_mm,
                    "thickness": self.default_floor_thickness if s_type == "floor" else 20,
                    "elevation": 0 if s_type == "floor" else room.get("ceiling_height", self.default_wall_height)
                }
                slab_params.append(param)
        return slab_params

    async def export_gltf(self, geometry_data: Dict, output_path: str) -> str:
        """
        Export a lightweight glTF for the web viewer.
        NOTE: This is NOT the RVT file. This is only for the human user's visual feedback in the UI.
        The RVT file is generated by the Windows Revit Service using the semantic parameters.
        """
        logger.info(f"Creating visual preview (glTF) at {output_path}")
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        scene = trimesh.Scene()
        
        # Simple visual representation of walls
        for wall in geometry_data["walls"]:
            s, e = wall["start_point"], wall["end_point"]
            dx, dy = e["x"] - s["x"], e["y"] - s["y"]
            length = np.sqrt(dx**2 + dy**2)
            angle = np.arctan2(dy, dx)
            
            box = trimesh.creation.box(extents=[length, wall["thickness"], wall["height"]])
            transform = trimesh.transformations.translation_matrix([
                (s["x"] + e["x"]) / 2,
                (s["y"] + e["y"]) / 2,
                wall["height"] / 2
            ])
            rotation = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
            box.apply_transform(trimesh.transformations.concatenate_matrices(transform, rotation))
            
            # Add some color for visualization
            box.visual.face_colors = [200, 200, 200, 255]
            scene.add_geometry(box)
            
        scene.export(output_path)
        return output_path
