"""
Windows Revit API Service - Python Implementation
Alternative to C# service

Stage 6: Generate Revit Commands
    - JSON with exact API calls
    - Wall types, families, parameters

Stage 7: Execute in Revit (Windows)
    - Open Revit via API
    - Create elements
    - Save .RVT file
"""

import clr
import sys
import os
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_file
import threading

# Add Revit API references
revit_path = r'C:\Program Files\Autodesk\Revit 2022'
sys.path.append(revit_path)
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

from Autodesk.Revit.DB import *
from Autodesk.Revit.ApplicationServices import Application

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Flask app
app = Flask(__name__)

# Revit application (global)
revit_app = None


def init_revit():
    """Initialize Revit application"""
    global revit_app
    try:
        revit_app = Application()
        print("✓ Revit application initialized")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize Revit: {e}")
        return False


class RevitModelBuilder:
    """Build Revit model from transaction JSON"""
    
    def __init__(self, app):
        self.app = app
        self.doc = None
    
    def build(self, transaction: dict, output_path: str):
        """Execute transaction and build model"""
        
        # Create new document
        template_path = config['revit_settings']['template_path']
        self.doc = self.app.NewProjectDocument(template_path)
        
        try:
            # Start transaction
            trans = Transaction(self.doc, "Build Floor Plan Model")
            trans.Start()
            
            # Create levels
            self.create_levels(transaction['levels'])
            
            # Create walls
            self.create_walls(transaction['walls'])
            
            # Create doors
            self.create_doors(transaction['doors'])
            
            # Create windows
            self.create_windows(transaction['windows'])
            
            # Create floors
            self.create_floors(transaction['floors'])
            
            # Create rooms
            self.create_rooms(transaction['rooms'])
            
            # Commit transaction
            trans.Commit()
            
            # Save document
            save_options = SaveAsOptions()
            save_options.OverwriteExistingFile = True
            self.doc.SaveAs(output_path, save_options)
            
            # Close document
            self.doc.Close(False)
            
            print(f"✓ Model saved to {output_path}")
            return output_path
            
        except Exception as e:
            trans.RollBack()
            print(f"✗ Build failed: {e}")
            raise
    
    def create_walls(self, walls):
        """Create walls"""
        for wall_cmd in walls:
            params = wall_cmd['parameters']
            
            # Get wall type
            wall_type = self.get_wall_type(params['wall_type'])
            
            # Get level
            level = self.get_level(params['level'])
            
            # Create curve
            start = XYZ(
                params['curve']['start']['x'] / 304.8,  # mm to feet
                params['curve']['start']['y'] / 304.8,
                params['curve']['start']['z'] / 304.8
            )
            end = XYZ(
                params['curve']['end']['x'] / 304.8,
                params['curve']['end']['y'] / 304.8,
                params['curve']['end']['z'] / 304.8
            )
            
            line = Line.CreateBound(start, end)
            
            # Create wall
            Wall.Create(
                self.doc,
                line,
                wall_type.Id,
                level.Id,
                params['height'] / 304.8,  # mm to feet
                params['offset'],
                params['flip'],
                params['structural']
            )
    
    def create_doors(self, doors):
        """Create doors"""
        for door_cmd in doors:
            params = door_cmd['parameters']
            
            # Get door symbol
            door_symbol = self.get_door_symbol(
                params['family'],
                params['symbol']
            )
            
            # Activate if needed
            if not door_symbol.IsActive:
                door_symbol.Activate()
                self.doc.Regenerate()
            
            # Get level
            level = self.get_level(params['level'])
            
            # Get host wall
            host_wall = self.find_wall_by_id(params['host_wall_id'])
            
            # Create location
            location = XYZ(
                params['location']['x'] / 304.8,
                params['location']['y'] / 304.8,
                params['location']['z'] / 304.8
            )
            
            # Create door instance
            self.doc.Create.NewFamilyInstance(
                location,
                door_symbol,
                host_wall,
                level,
                StructuralType.NonStructural
            )
    
    def get_wall_type(self, type_name):
        """Find wall type by name"""
        collector = FilteredElementCollector(self.doc)
        collector.OfClass(WallType)
        
        for wall_type in collector:
            if wall_type.Name == type_name:
                return wall_type
        
        return collector.FirstElement()
    
    def get_level(self, level_name):
        """Find level by name"""
        collector = FilteredElementCollector(self.doc)
        collector.OfClass(Level)
        
        for level in collector:
            if level.Name == level_name:
                return level
        
        return collector.FirstElement()
    
    # Additional methods...


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Revit API Service",
        "version": "1.0.0",
        "revit_initialized": revit_app is not None
    })


@app.route('/build-model', methods=['POST'])
def build_model():
    """Build Revit model from transaction"""
    
    # Check API key
    api_key = request.headers.get('X-API-Key')
    if api_key != config['api_settings']['api_key']:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Get request data
    data = request.json
    job_id = data['job_id']
    transaction_json = data['transaction_json']
    
    print(f"Building model for job {job_id}")
    
    try:
        # Parse transaction
        transaction = json.loads(transaction_json)
        
        # Output path
        output_dir = config['revit_settings']['output_directory']
        output_path = os.path.join(output_dir, f"{job_id}.rvt")
        
        # Build model
        builder = RevitModelBuilder(revit_app)
        result_path = builder.build(transaction, output_path)
        
        # Return RVT file
        return send_file(
            result_path,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=f"{job_id}.rvt"
        )
        
    except Exception as e:
        print(f"Error building model: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("="*50)
    print("Revit API Service - Python Implementation")
    print("="*50)
    
    # Initialize Revit
    if not init_revit():
        print("Failed to initialize Revit. Exiting.")
        sys.exit(1)
    
    # Create output directory
    output_dir = config['revit_settings']['output_directory']
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Start Flask server
    host = config['api_settings']['host']
    port = config['api_settings']['port']
    
    print(f"\nStarting server on {host}:{port}")
    print("Ready to receive build requests!")
    print("="*50)
    
    app.run(host=host, port=port, threaded=False)
