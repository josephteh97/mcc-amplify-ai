# linux_server/backend/services/revit_transaction.py
"""
Stage 6: Revit Transaction Generator
Creates JSON with exact Revit API commands for Native Solid Modeling.
Aligned with Windows ModelBuilder.cs data structures.
"""

import json
from typing import Dict, List
from pathlib import Path
from datetime import datetime
from loguru import logger


class Stage6BIMEnrichment:
    """Generate Revit API transaction commands for native solid objects"""
    
    def __init__(self):
        self.revit_version = "2022"
        self.template = "Architectural Template"
        self.mapping = self._load_mapping()
    
    def _load_mapping(self) -> Dict:
        """Load family mapping configuration"""
        mapping_path = Path(__file__).parent.parent / "core" / "family_mapping.json"
        if mapping_path.exists():
            with open(mapping_path, 'r') as f:
                return json.load(f)
        return {}
    
    async def generate(self, geometry_data: Dict, project_name: str) -> Dict:
        """
        Generate complete Revit transaction.
        """
        logger.info(f"Generating Revit Native Transaction for {project_name}")
        
        transaction = {
            "version": self.revit_version,
            "template": self.template,
            "project_info": {
                "name": project_name,
                "author": "Amplify Floor Plan AI",
                "created_date": datetime.now().isoformat(),
                "description": "Auto-generated Native Revit Model"
            },
            "levels": [
                {"name": "Level 1", "elevation": 0},
                {"name": "Level 2", "elevation": 3000}
            ],
            "walls": await self._create_wall_commands(geometry_data['walls']),
            "doors": await self._create_door_commands(geometry_data['doors']),
            "windows": await self._create_window_commands(geometry_data['windows']),
            "columns": await self._create_column_commands(geometry_data.get('columns', [])),
            "floors": await self._create_floor_commands(geometry_data['floors']),
            "rooms": await self._create_room_commands(geometry_data['rooms']),
            "views": await self._create_view_commands()
        }
        
        return transaction

    async def _create_wall_commands(self, walls: List[Dict]) -> List[Dict]:
        """Commands for Wall.Create (Native Solid)"""
        commands = []
        for i, wall in enumerate(walls):
            wall_type = self._get_wall_type(wall)
            
            cmd = {
                "command": "Wall.Create",
                "parameters": {
                    "curve": {
                        "start": wall["start_point"],
                        "end": wall["end_point"]
                    },
                    "wall_type": wall_type,
                    "level": "Level 1",
                    "height": wall["height"],
                    "offset": 0,
                    "flip": False,
                    "structural": wall["is_structural"]
                },
                "properties": {
                    "function": wall["function"],
                    "material": wall["material"],
                    "fire_rating": ""
                }
            }
            commands.append(cmd)
        return commands

    def _get_wall_type(self, wall: Dict) -> str:
        """Map thickness to Revit Wall Type"""
        wall_function = wall.get('function', 'Interior')
        if wall_function.lower() == 'exterior':
            return self.mapping.get('walls', {}).get('exterior', "Generic - 300mm")
        return self.mapping.get('walls', {}).get('interior', "Generic - 200mm")

    async def _create_door_commands(self, doors: List[Dict]) -> List[Dict]:
        """Commands for FamilyInstance.Create (Native Doors)"""
        commands = []
        for i, door in enumerate(doors):
            family, symbol = self._get_family_info(door, "door")
            
            cmd = {
                "parameters": {
                    "family": family,
                    "symbol": symbol,
                    "location": door["location"],
                    "host_wall_id": f"wall_{door.get('host_wall_id', 0)}",
                    "level": "Level 1",
                    "rotation": 0
                }
            }
            commands.append(cmd)
        return commands

    async def _create_window_commands(self, windows: List[Dict]) -> List[Dict]:
        """Commands for FamilyInstance.Create (Native Windows)"""
        commands = []
        for i, window in enumerate(windows):
            family, symbol = self._get_family_info(window, "window")
            
            cmd = {
                "parameters": {
                    "family": family,
                    "symbol": symbol,
                    "location": window["location"],
                    "host_wall_id": f"wall_{window.get('host_wall_id', 0)}",
                    "level": "Level 1"
                }
            }
            commands.append(cmd)
        return commands

    async def _create_column_commands(self, columns: List[Dict]) -> List[Dict]:
        """Commands for Column.Create (Native Structural Columns)"""
        commands = []
        for i, column in enumerate(columns):
            family, symbol = self._get_column_family(column)
            
            cmd = {
                "id": f"column_{i}",
                "command": "Column.Create",
                "parameters": {
                    "family": family,
                    "symbol": symbol,
                    "location": column["location"],
                    "level": "Level 1",
                    "height": column.get("height", 2800),
                    "rotation": 0
                },
                "properties": {
                    "width": column.get("width", 300),
                    "depth": column.get("depth", 300),
                    "material": column.get("material", "Concrete")
                }
            }
            commands.append(cmd)
        return commands

    def _get_column_family(self, column: Dict) -> tuple:
        """Select Revit Column Family based on shape"""
        shape = column.get("shape", "rectangular")
        width = column.get("width", 300)
        depth = column.get("depth", 300)
        
        if shape == "circular":
            family = "M_Concrete-Round-Column"
            symbol = f"{int(width)}mm"
        else:
            family = "M_Concrete-Rectangular-Column"
            symbol = f"{int(width)} x {int(depth)}mm"
            
        return family, symbol

    def _get_family_info(self, element: Dict, e_type: str) -> tuple:
        """Get family and symbol from mapping"""
        type_name = element.get('type_name', 'Standard').lower()
        width = element.get('width', 900)
        
        type_map = self.mapping.get(f'{e_type}s', {}).get(type_name, {})
        family = type_map.get('family', "M_Single-Flush" if e_type == "door" else "M_Fixed")
        
        symbols = type_map.get('symbols', {})
        if symbols:
            widths = sorted([int(k) for k in symbols.keys()])
            closest = min(widths, key=lambda x: abs(x - width))
            symbol = symbols.get(str(closest))
        else:
            symbol = f"{int(width)}mm x 2100mm"
            
        return family, symbol

    async def _create_floor_commands(self, floors: List[Dict]) -> List[Dict]:
        """Commands for Floor.Create (Native Solid)"""
        commands = []
        for i, floor in enumerate(floors):
            cmd = {
                "parameters": {
                    "boundary": floor["boundary_points"],
                    "floor_type": "Generic - 200mm",
                    "level": "Level 1",
                    "structural": True
                }
            }
            commands.append(cmd)
        return commands

    async def _create_room_commands(self, rooms: List[Dict]) -> List[Dict]:
        """Commands for Room.Create (Native Revit Space)"""
        commands = []
        for i, room in enumerate(rooms):
            cmd = {
                "parameters": {
                    "name": room["name"],
                    "number": str(i + 1),
                    "level": "Level 1",
                    "point": room["center_point"]
                }
            }
            commands.append(cmd)
        return commands

    async def _create_view_commands(self) -> List[Dict]:
        """Commands for View.Create (Native Views)"""
        return [
            {"parameters": {"view_type": "3D", "name": "3D View"}},
            {"parameters": {"view_type": "FloorPlan", "name": "Level 1 Plan", "level": "Level 1"}}
        ]

    async def save(self, transaction: Dict, output_path: str):
        """Save transaction to JSON file"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(transaction, f, indent=2)
        logger.info(f"Native Revit Transaction saved to {output_path}")
