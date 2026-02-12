"""
Stage 7: glTF Exporter
Exports 3D geometry to glTF format for web viewing
"""

import trimesh
import numpy as np
from pathlib import Path
from loguru import logger

class GltfExporter:
    async def export(self, geometry_data: dict, output_path: str) -> str:
        """Export geometry to glTF/GLB"""
        logger.info(f"Exporting glTF to {output_path}")
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        scene = trimesh.Scene()
        
        # Add walls
        for wall in geometry_data.get("walls", []):
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
            box.visual.face_colors = [200, 200, 200, 255]
            scene.add_geometry(box)
            
        # Add columns
        for col in geometry_data.get("columns", []):
            loc = col["location"]
            if col["shape"] == "circular":
                mesh = trimesh.creation.cylinder(radius=col["width"]/2, height=col["height"])
            else:
                mesh = trimesh.creation.box(extents=[col["width"], col["depth"], col["height"]])
                
            transform = trimesh.transformations.translation_matrix([
                loc["x"], loc["y"], col["height"]/2
            ])
            mesh.apply_transform(transform)
            mesh.visual.face_colors = [150, 150, 150, 255]
            scene.add_geometry(mesh)
            
        scene.export(output_path)
        return output_path
