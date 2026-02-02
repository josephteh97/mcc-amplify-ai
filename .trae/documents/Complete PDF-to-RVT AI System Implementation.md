# Complete Implementation Plan for PDF-to-RVT AI System

This plan outlines the steps to tidy up the existing codebase, complete the 7-stage processing pipeline, and implement the specialized components for Revit generation and AI training.

## 1. Complete Linux Backend (7 Stages)
### Stage 5: Geometry Builder Implementation
- **File**: [geometry_builder.py](file:///c:/MyDocuments/mcc-amplify-ai/linux_server/backend/services/geometry_builder.py)
- **Task**: Implement the `build` method to convert 2D pixel coordinates to 3D architectural geometry in millimeters.
- **Features**: 
    - Extrude wall lines into 3D boxes with thickness and height.
    - Calculate precise coordinates for openings (doors/windows).
    - Generate floor/ceiling boundary polygons from room contours.
    - Export glTF for the web frontend viewer.

### Stage 6: Revit Transaction Generator
- **File**: [revit_transaction.py](file:///c:/MyDocuments/mcc-amplify-ai/linux_server/backend/services/revit_transaction.py)
- **Task**: Complete the mapping of 3D geometry to Revit API commands.
- **Features**:
    - Add command generators for Floors, Ceilings, and Rooms.
    - Implement a family mapping system to link detected elements to specific Revit families.
    - Ensure all metadata (materials, fire ratings) is included in the JSON.

## 2. Windows Revit Service Enhancement
### Revit Model Builder
- **File**: [ModelBuilder.cs](file:///c:/MyDocuments/mcc-amplify-ai/windows_server/RevitService/ModelBuilder.cs)
- **Task**: Complete the C# Revit API integration.
- **Features**:
    - Implement `CreateWindows`, `CreateFloors`, and `CreateRooms`.
    - Add `LoadFamily` logic to support custom `.rfa` files for specialized doors/windows.
    - Handle unit conversions (mm to feet) for Revit internal consistency.
    - Implement the "rendering" step mentioned in the workflow.

## 3. YOLOv11 Training System
### Training Script
- **File**: `linux_server/backend/ml/train_yolov11.py` (New File)
- **Task**: Create a production-ready training script for YOLOv11.
- **Features**:
    - Data loading from standardized floor plan datasets (e.g., CVC-FP).
    - Hyperparameter tuning for architectural symbols.
    - Export weights to the backend model directory.

## 4. Revit Family Customization
### Configuration & Mapping
- **Task**: Create a flexible mapping system for Revit families.
- **Implementation**: 
    - Use a JSON configuration to map detected categories (e.g., "Double Door") to specific Revit family files and symbols.
    - Allow users to specify their own library paths in the deployment config.

## 5. Integration & Verification
- **Task**: Ensure the end-to-end data flow.
- **Steps**:
    - Verify Stage 1-4 (PDF to Analysis) correctly feeds into Stage 5-6 (Geometry to JSON).
    - Mock the Windows service for local testing or provide a bridge for the Revit API.
    - Update the frontend [ThreeDViewer.jsx](file:///c:/MyDocuments/mcc-amplify-ai/linux_server/frontend/src/components/ThreeDViewer.jsx) to display the processed results.

Does this plan align with your vision for the "Pure Revit" workflow? Once confirmed, I will begin the implementation.