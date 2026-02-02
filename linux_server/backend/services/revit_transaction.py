# linux_server/backend/services/revit_transaction.py
"""
Stage 6: Revit Transaction Generator
Creates JSON with exact Revit API commands

Generates precise Revit API commands from detected geometry
No conversion - direct native Revit instructions

"""

import json
from typing import Dict, List
from pathlib import Path
from datetime import datetime
from loguru import logger


class RevitTransactionGenerator:
    """Generate Revit API transaction commands"""
    
    def __init__(self):
        self.revit_version = "2022"
        self.template = "Architectural Template"
    
    async def generate(self, geometry_data: Dict, project_name: str) -> Dict:
        """
        Generate complete Revit transaction
        
        Args:
            geometry_data: 3D geometry from GeometryBuilder
            project_name: Name for the project
            
        Returns:
            Complete transaction JSON
        """
        logger.info(f"Generating Revit transaction for {project_name}")
        
        transaction = {
            "version": self.revit_version,
            "template": self.template,
            "project_info": {
                "name": project_name,
                "author": "Amplify Floor Plan AI",
                "created_date": datetime.now().isoformat(),
                "description": "Auto-generated from floor plan PDF"
            },
            "units": {
                "length": "millimeters",
                "area": "square_meters"
            },
            "levels": await self._create_levels(geometry_data),
            "walls": await self._create_walls(geometry_data['walls']),
            "doors": await self._create_doors(geometry_data['doors']),
            "windows": await self._create_windows(geometry_data['windows']),
            "floors": await self._create_floors(geometry_data['floors']),
            "ceilings": await self._create_ceilings(geometry_data.get('ceilings', [])),
            "rooms": await self._create_rooms(geometry_data['rooms']),
            "views": await self._create_views()
        }
        
        return transaction
    
    async def _create_levels(self, geometry_data: Dict) -> List[Dict]:
        """Create level definitions"""
        levels = [
            {
                "name": "Level 1",
                "elevation": 0,
                "create_plan_view": True,
                "create_ceiling_plan": True
            },
            {
                "name": "Level 2",
                "elevation": 3000,  # mm
                "create_plan_view": False,
                "create_ceiling_plan": False
            }
        ]
        
        return levels
    
    async def _create_walls(self, walls: List[Dict]) -> List[Dict]:
        """Generate wall creation commands"""
        wall_commands = []
        
        for i, wall in enumerate(walls):
            # Determine wall type based on properties
            wall_type = self._get_wall_type(wall)
            
            wall_cmd = {
                "id": f"wall_{i}",
                "command": "Wall.Create",
                "parameters": {
                    "curve": {
                        "type": "Line",
                        "start": {
                            "x": wall['start_x'],
                            "y": wall['start_y'],
                            "z": 0
                        },
                        "end": {
                            "x": wall['end_x'],
                            "y": wall['end_y'],
                            "z": 0
                        }
                    },
                    "wall_type": wall_type,
                    "level": "Level 1",
                    "height": wall.get('height', 2800),
                    "offset": 0,
                    "flip": False,
                    "structural": wall.get('structural', False)
                },
                "properties": {
                    "function": wall.get('wall_function', 'Interior'),
                    "material": wall.get('material', 'Concrete'),
                    "thickness": wall.get('thickness', 200),
                    "fire_rating": wall.get('fire_rating', ''),
                    "comments": f"Auto-generated wall {i}"
                }
            }
            
            wall_commands.append(wall_cmd)
        
        return wall_commands
    
    def _get_wall_type(self, wall: Dict) -> str:
        """Map wall properties to Revit wall type"""
        thickness = wall.get('thickness', 200)
        
        if thickness >= 300:
            return "Generic - 300mm"
        elif thickness >= 200:
            return "Generic - 200mm"
        elif thickness >= 150:
            return "Generic - 150mm"
        else:
            return "Generic - 100mm"
    
    async def _create_doors(self, doors: List[Dict]) -> List[Dict]:
        """Generate door creation commands"""
        door_commands = []
        
        for i, door in enumerate(doors):
            family, symbol = self._get_door_family(door)
            
            door_cmd = {
                "id": f"door_{i}",
                "command": "FamilyInstance.Create",
                "parameters": {
                    "family": family,
                    "symbol": symbol,
                    "location": {
                        "x": door['center'][0],
                        "y": door['center'][1],
                        "z": 0
                    },
                    "host_wall_id": f"wall_{door.get('host_wall_id', 0)}",
                    "level": "Level 1",
                    "rotation": door.get('rotation', 0)
                },
                "properties": {
                    "width": door.get('width', 900),
                    "height": door.get('height', 2100),
                    "swing_direction": door.get('swing_direction', 'right'),
                    "fire_rating": door.get('fire_rating', ''),
                    "material": door.get('material', 'Wood')
                }
            }
            
            door_commands.append(door_cmd)
        
        return door_commands
    
    def _get_door_family(self, door: Dict) -> tuple:
        """Select appropriate Revit door family"""
        width = door.get('width', 900)
        door_type = door.get('door_type', 'single')
        
        if door_type == 'double':
            family = "M_Double-Flush"
            symbol = f"{int(width)}mm x 2100mm"
        elif door_type == 'sliding':
            family = "M_Sliding"
            symbol = f"{int(width)}mm x 2100mm"
        else:
            family = "M_Single-Flush"
            if width >= 1000:
                symbol = "1000mm x 2100mm"
            elif width >= 900:
                symbol = "900mm x 2100mm"
            else:
                symbol = "800mm x 2100mm"
        
        return family, symbol
    
    async def _create_windows(self, windows: List[Dict]) -> List[Dict]:
        """Generate window creation commands"""
        window_commands = []
        
        for i, window in enumerate(windows):
            family, symbol = self._get_window_family(window)
            
            window_cmd = {
                "id": f"window_{i}",
                "command": "FamilyInstance.Create",
                "parameters": {
                    "family": family,
                    "symbol": symbol,
                    "location": {
                        "x": window['center'][0],
                        "y": window['center'][1],
                        "z": window.get('sill_height', 900)
                    },
                    "host_wall_id": f"wall_{window.get('host_wall_id', 0)}",
                    "level": "Level 1"
                },
                "properties": {
                    "width": window.get('width', 1200),
                    "height": window.get('height', 1500),
                    "sill_height": window.get('sill_height', 900),
                    "window_type": window.get('window_type', 'Fixed')
                }
            }
            
            window_commands.append(window_cmd)
        
        return window_commands
    
    def _get_window_family(self, window: Dict) -> tuple:
        """Select appropriate Revit window family"""
        window_type = window.get('window_type', 'fixed')
        width = window.get('width', 1200)
        height = window.get('height', 1500)
        
        if window_type == 'casement':
            family = "M_Casement"
        elif window_type == 'sliding':
            family = "M_Sliding"
        else:
            family = "M_Fixed"
        
        symbol = f"{int(width)}mm x {int(height)}mm"
        
        return family, symbol
    
    async def _create_floors(self, floors: List[Dict]) -> List[Dict]:
        """Generate floor creation commands"""
        floor_commands = []
        
        for i, floor in enumerate(floors):
            floor_cmd = {
                "id": f"floor_{i}",
                "command": "Floor.Create",
                "parameters": {
                    "boundary": floor['boundary'],  # List of points
                    "floor_type": "Generic - 200mm",
                    "level": "Level 1",
                    "structural": True
                },
                "properties": {
                    "thickness": 200,
                    "material": "Concrete"
                }
            }
            
            floor_commands.append(floor_cmd)
        
        return floor_commands
    
    async def _create_ceilings(self, ceilings: List[Dict]) -> List[Dict]:
        """Generate ceiling creation commands"""
        # Similar to floors
        return []
    
    async def _create_rooms(self, rooms: List[Dict]) -> List[Dict]:
        """Generate room creation commands"""
        room_commands = []
        
        for i, room in enumerate(rooms):
            room_cmd = {
                "id": f"room_{i}",
                "command": "Room.Create",
                "parameters": {
                    "name": room.get('name', f'Room {i+1}'),
                    "number": str(i + 1),
                    "level": "Level 1",
                    "point": {
                        "x": room['center'][0],
                        "y": room['center'][1]
                    }
                },
                "properties": {
                    "department": room.get('purpose', 'General'),
                    "area": room.get('area_sqm', 0),
                    "comments": room.get('comments', '')
                }
            }
            
            room_commands.append(room_cmd)
        
        return room_commands
    
    async def _create_views(self) -> List[Dict]:
        """Generate view creation commands"""
        views = [
            {
                "command": "View.Create",
                "parameters": {
                    "view_type": "FloorPlan",
                    "name": "Ground Floor Plan",
                    "level": "Level 1"
                }
            },
            {
                "command": "View.Create",
                "parameters": {
                    "view_type": "3D",
                    "name": "3D View"
                }
            }
        ]
        
        return views
    
    async def save(self, transaction: Dict, output_path: str):
        """Save transaction to JSON file"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(transaction, f, indent=2)
        
        logger.info(f"Revit transaction saved to {output_path}")
