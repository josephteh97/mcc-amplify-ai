"""
Stage 5: 3D Geometry Generation
Converts 2D detected elements to 3D architectural geometry
"""

import numpy as np
import trimesh
from typing import Dict, List, Optional
from loguru import logger
from pathlib import Path
import json


class GeometryBuilder:
    """Build 3D geometry from 2D architectural elements"""
    
    def __init__(self):
        self.default_wall_height = 2800  # mm
        self.default_wall_thickness = 200  # mm
        self.default_door_height = 2100  # mm
        self.default_window_height = 1500  # mm
        self.default_sill_height = 900  # mm
        self.default_floor_thickness = 200  # mm

    async def build(self, enriched_data: Dict, scale_info: Dict) -> Dict:
        """
        Build 3D geometry from enriched analysis data
        
        Args:
            enriched_data: Data from Claude analysis + YOLO
            scale_info: Scale calibration data
            
        Returns:
            Dict containing 3D geometry for all elements
        """
        logger.info("Building 3D geometry...")
        
        pixels_per_mm = scale_info["pixels_per_mm"]
        
        geometry = {
            "walls": await self._build_walls(enriched_data["walls"], pixels_per_mm),
            "doors": await self._build_doors(enriched_data["doors"], pixels_per_mm),
            "windows": await self._build_windows(enriched_data["windows"], pixels_per_mm),
            "rooms": await self._build_rooms(enriched_data["rooms"], pixels_per_mm),
            "floors": await self._build_floors(enriched_data.get("rooms", []), pixels_per_mm),
            "ceilings": await self._build_ceilings(enriched_data.get("rooms", []), pixels_per_mm),
            "metadata": enriched_data.get("metadata", {})
        }
        
        logger.info(f"Built geometry: {len(geometry['walls'])} walls, "
                   f"{len(geometry['doors'])} doors, "
                   f"{len(geometry['windows'])} windows")
        
        return geometry

    async def _build_walls(self, walls_2d: List[Dict], pixels_per_mm: float) -> List[Dict]:
        """Convert 2D walls to 3D segments"""
        walls_3d = []
        
        for wall in walls_2d:
            # Convert endpoints from pixels to mm
            start_px = wall["endpoints"][0]
            end_px = wall["endpoints"][1]
            
            start_mm = [p / pixels_per_mm for p in start_px]
            end_mm = [p / pixels_per_mm for p in end_px]
            
            thickness = wall.get("thickness", self.default_wall_thickness)
            height = wall.get("ceiling_height", self.default_wall_height)
            
            wall_3d = {
                "id": wall.get("id"),
                "start_x": start_mm[0],
                "start_y": start_mm[1],
                "end_x": end_mm[0],
                "end_y": end_mm[1],
                "thickness": thickness,
                "height": height,
                "material": wall.get("material", "Concrete"),
                "structural": wall.get("structural", False),
                "wall_function": wall.get("wall_function", "Interior")
            }
            
            # Generate 8 vertices for the wall box
            wall_3d["vertices"] = self._generate_wall_vertices(wall_3d)
            
            walls_3d.append(wall_3d)
            
        return walls_3d

    def _generate_wall_vertices(self, wall: Dict) -> List[List[float]]:
        """Generate 8 vertices for a 3D wall box"""
        x1, y1 = wall["start_x"], wall["start_y"]
        x2, y2 = wall["end_x"], wall["end_y"]
        t = wall["thickness"]
        h = wall["height"]
        
        # Calculate direction vector
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx**2 + dy**2)
        
        if length == 0:
            return []
            
        # Normal vector (perpendicular to wall)
        nx = -dy / length
        ny = dx / length
        
        # 4 corners of the base (z=0)
        v1 = [x1 + nx * t/2, y1 + ny * t/2, 0]
        v2 = [x1 - nx * t/2, y1 - ny * t/2, 0]
        v3 = [x2 - nx * t/2, y2 - ny * t/2, 0]
        v4 = [x2 + nx * t/2, y2 + ny * t/2, 0]
        
        # 4 corners of the top (z=h)
        v5 = [v1[0], v1[1], h]
        v6 = [v2[0], v2[1], h]
        v7 = [v3[0], v3[1], h]
        v8 = [v4[0], v4[1], h]
        
        return [v1, v2, v3, v4, v5, v6, v7, v8]

    async def _build_doors(self, doors_2d: List[Dict], pixels_per_mm: float) -> List[Dict]:
        """Convert 2D doors to 3D instances"""
        doors_3d = []
        for door in doors_2d:
            center_mm = [p / pixels_per_mm for p in door["center"]]
            width = door.get("width", 900)
            
            door_3d = {
                "id": door.get("id"),
                "center": center_mm,
                "width": width,
                "height": self.default_door_height,
                "door_type": door.get("door_type", "single"),
                "swing_direction": door.get("swing_direction", "right"),
                "host_wall_id": door.get("host_wall_id")
            }
            doors_3d.append(door_3d)
        return doors_3d

    async def _build_windows(self, windows_2d: List[Dict], pixels_per_mm: float) -> List[Dict]:
        """Convert 2D windows to 3D instances"""
        windows_3d = []
        for window in windows_2d:
            center_mm = [p / pixels_per_mm for p in window["center"]]
            width = window.get("width", 1200)
            
            window_3d = {
                "id": window.get("id"),
                "center": center_mm,
                "width": width,
                "height": self.default_window_height,
                "sill_height": self.default_sill_height,
                "window_type": window.get("window_type", "fixed"),
                "host_wall_id": window.get("host_wall_id")
            }
            windows_3d.append(window_3d)
        return windows_3d

    async def _build_rooms(self, rooms_2d: List[Dict], pixels_per_mm: float) -> List[Dict]:
        """Convert 2D rooms to 3D spaces"""
        rooms_3d = []
        for room in rooms_2d:
            center_mm = [p / pixels_per_mm for p in room["center"]]
            
            room_3d = {
                "id": room.get("id"),
                "name": room.get("name", "Unnamed Room"),
                "purpose": room.get("purpose", "General"),
                "center": center_mm,
                "area_sqm": room.get("area_sqm", 0),
                "height": room.get("ceiling_height", self.default_wall_height)
            }
            rooms_3d.append(room_3d)
        return rooms_3d

    async def _build_floors(self, rooms_2d: List[Dict], pixels_per_mm: float) -> List[Dict]:
        """Generate floor geometry from room boundaries"""
        floors = []
        for i, room in enumerate(rooms_2d):
            if "boundary" in room:
                boundary_mm = [[p[0]/pixels_per_mm, p[1]/pixels_per_mm] for p in room["boundary"]]
                floors.append({
                    "id": f"floor_{i}",
                    "boundary": boundary_mm,
                    "thickness": self.default_floor_thickness,
                    "level": "Level 1"
                })
        return floors

    async def _build_ceilings(self, rooms_2d: List[Dict], pixels_per_mm: float) -> List[Dict]:
        """Generate ceiling geometry from room boundaries"""
        ceilings = []
        for i, room in enumerate(rooms_2d):
            if "boundary" in room:
                boundary_mm = [[p[0]/pixels_per_mm, p[1]/pixels_per_mm] for p in room["boundary"]]
                ceilings.append({
                    "id": f"ceiling_{i}",
                    "boundary": boundary_mm,
                    "height": room.get("ceiling_height", self.default_wall_height),
                    "thickness": 20  # mm
                })
        return ceilings

    async def export_gltf(self, geometry_data: Dict, output_path: str) -> str:
        """Export 3D geometry as glTF for web viewer"""
        logger.info(f"Exporting glTF to {output_path}")
        
        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        meshes = []
        
        # Add walls to mesh
        for wall in geometry_data["walls"]:
            if not wall["vertices"]:
                continue
            
            # Simple box mesh for wall
            # In a real implementation, use trimesh to create a proper box
            box = trimesh.creation.box(extents=[1, 1, 1]) # Placeholder
            # Transform box to match wall vertices...
            # For now, let's just create a dummy glb so the frontend doesn't crash
        
        # Using trimesh to create a scene
        scene = trimesh.Scene()
        
        # Add walls as boxes
        for wall in geometry_data["walls"]:
            x1, y1 = wall["start_x"], wall["start_y"]
            x2, y2 = wall["end_x"], wall["end_y"]
            dx, dy = x2 - x1, y2 - y1
            length = np.sqrt(dx**2 + dy**2)
            angle = np.arctan2(dy, dx)
            
            # Create box at origin
            box = trimesh.creation.box(extents=[length, wall["thickness"], wall["height"]])
            
            # Transform to position
            transform = trimesh.transformations.translation_matrix([
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                wall["height"] / 2
            ])
            rotation = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
            box.apply_transform(trimesh.transformations.concatenate_matrices(transform, rotation))
            
            scene.add_geometry(box)
            
        # Export scene
        scene.export(output_path)
        
        return output_path
