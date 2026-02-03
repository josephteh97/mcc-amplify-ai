// windows_server/RevitService/ModelBuilder.cs

using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;

namespace RevitService
{
    public class ModelBuilder
    {
        private Application revitApp;
        private Document doc;
        private const double MM_TO_FEET = 1.0 / 304.8;
        
        public ModelBuilder()
        {
            // Initialize Revit application
            // In a real Revit plugin, this would be provided by the IExternalCommand context
            revitApp = new Application();
        }
        
        public string BuildModel(string transactionJson, string outputPath)
        {
            try
            {
                // Parse transaction JSON
                var transaction = JsonConvert.DeserializeObject<RevitTransaction>(transactionJson);
                
                // Create new document from template
                string templatePath = @"C:\ProgramData\Autodesk\RVT 2022\Templates\Architectural Template.rte";
                doc = revitApp.NewProjectDocument(templatePath);
                
                using (Transaction trans = new Transaction(doc, "Build Floor Plan Model"))
                {
                    trans.Start();
                    
                    // Create levels
                    CreateLevels(transaction.Levels);
                    
                    // Create walls
                    CreateWalls(transaction.Walls);
                    
                    // Create doors
                    CreateDoors(transaction.Doors);
                    
                    // Create windows
                    CreateWindows(transaction.Windows);
                    
                    // Create floors
                    CreateFloors(transaction.Floors);
                    
                    // Create rooms
                    CreateRooms(transaction.Rooms);
                    
                    // Create views
                    CreateViews(transaction.Views);
                    
                    trans.Commit();
                }
                
                // Save as RVT
                SaveAsOptions saveOptions = new SaveAsOptions();
                saveOptions.OverwriteExistingFile = true;
                doc.SaveAs(outputPath, saveOptions);
                
                // Close document
                doc.Close(false);
                
                return outputPath;
            }
            catch (Exception ex)
            {
                throw new Exception($"Revit model building failed: {ex.Message}");
            }
        }
        
        private void CreateLevels(List<LevelCommand> levels)
        {
            foreach (var levelCmd in levels)
            {
                Level level = Level.Create(doc, levelCmd.Elevation * MM_TO_FEET);
                level.Name = levelCmd.Name;
            }
        }

        private void CreateWalls(List<WallCommand> walls)
        {
            foreach (var wallCmd in walls)
            {
                WallType wallType = GetWallType(wallCmd.Parameters.WallType);
                Level level = GetLevel(wallCmd.Parameters.Level);
                
                XYZ startPoint = new XYZ(
                    wallCmd.Parameters.Curve.Start.X * MM_TO_FEET,
                    wallCmd.Parameters.Curve.Start.Y * MM_TO_FEET,
                    wallCmd.Parameters.Curve.Start.Z * MM_TO_FEET
                );
                
                XYZ endPoint = new XYZ(
                    wallCmd.Parameters.Curve.End.X * MM_TO_FEET,
                    wallCmd.Parameters.Curve.End.Y * MM_TO_FEET,
                    wallCmd.Parameters.Curve.End.Z * MM_TO_FEET
                );
                
                Line wallLine = Line.CreateBound(startPoint, endPoint);
                
                Wall wall = Wall.Create(
                    doc,
                    wallLine,
                    wallType.Id,
                    level.Id,
                    wallCmd.Parameters.Height * MM_TO_FEET,
                    wallCmd.Parameters.Offset * MM_TO_FEET,
                    wallCmd.Parameters.Flip,
                    wallCmd.Parameters.Structural
                );
                
                SetWallProperties(wall, wallCmd.Properties);
            }
        }
        
        private void CreateDoors(List<DoorCommand> doors)
        {
            foreach (var doorCmd in doors)
            {
                FamilySymbol doorSymbol = GetFamilySymbol(doorCmd.Parameters.Family, doorCmd.Parameters.Symbol);
                
                if (!doorSymbol.IsActive) doorSymbol.Activate();
                
                Wall hostWall = GetElementById<Wall>(doorCmd.Parameters.HostWallId);
                Level level = GetLevel(doorCmd.Parameters.Level);
                
                XYZ location = new XYZ(
                    doorCmd.Parameters.Location.X * MM_TO_FEET,
                    doorCmd.Parameters.Location.Y * MM_TO_FEET,
                    doorCmd.Parameters.Location.Z * MM_TO_FEET
                );
                
                FamilyInstance door = doc.Create.NewFamilyInstance(
                    location,
                    doorSymbol,
                    hostWall,
                    level,
                    StructuralType.NonStructural
                );
                
                if (doorCmd.Parameters.Rotation != 0)
                {
                    Line axis = Line.CreateBound(location, location + XYZ.BasisZ);
                    ElementTransformUtils.RotateElement(doc, door.Id, axis, doorCmd.Parameters.Rotation * Math.PI / 180);
                }
            }
        }

        private void CreateWindows(List<WindowCommand> windows)
        {
            foreach (var winCmd in windows)
            {
                FamilySymbol winSymbol = GetFamilySymbol(winCmd.Parameters.Family, winCmd.Parameters.Symbol);
                if (!winSymbol.IsActive) winSymbol.Activate();

                Wall hostWall = GetElementById<Wall>(winCmd.Parameters.HostWallId);
                Level level = GetLevel(winCmd.Parameters.Level);
                
                XYZ location = new XYZ(
                    winCmd.Parameters.Location.X * MM_TO_FEET,
                    winCmd.Parameters.Location.Y * MM_TO_FEET,
                    winCmd.Parameters.Location.Z * MM_TO_FEET
                );

                FamilyInstance window = doc.Create.NewFamilyInstance(
                    location,
                    winSymbol,
                    hostWall,
                    level,
                    StructuralType.NonStructural
                );
            }
        }

        private void CreateFloors(List<FloorCommand> floors)
        {
            foreach (var floorCmd in floors)
            {
                CurveArray profile = new CurveArray();
                for (int i = 0; i < floorCmd.Parameters.Boundary.Count; i++)
                {
                    var p1 = floorCmd.Parameters.Boundary[i];
                    var p2 = floorCmd.Parameters.Boundary[(i + 1) % floorCmd.Parameters.Boundary.Count];
                    profile.Append(Line.CreateBound(
                        new XYZ(p1.X * MM_TO_FEET, p1.Y * MM_TO_FEET, 0),
                        new XYZ(p2.X * MM_TO_FEET, p2.Y * MM_TO_FEET, 0)
                    ));
                }

                FloorType floorType = GetFloorType(floorCmd.Parameters.FloorType);
                Level level = GetLevel(floorCmd.Parameters.Level);

                doc.Create.NewFloor(profile, floorType, level, floorCmd.Parameters.Structural);
            }
        }

        private void CreateRooms(List<RoomCommand> rooms)
        {
            foreach (var roomCmd in rooms)
            {
                Level level = GetLevel(roomCmd.Parameters.Level);
                UV point = new UV(roomCmd.Parameters.Point.X * MM_TO_FEET, roomCmd.Parameters.Point.Y * MM_TO_FEET);
                
                Room room = doc.Create.NewRoom(level, point);
                room.Name = roomCmd.Parameters.Name;
                room.Number = roomCmd.Parameters.Number;
            }
        }

        private void CreateViews(List<ViewCommand> views)
        {
            foreach (var viewCmd in views)
            {
                if (viewCmd.Parameters.ViewType == "3D")
                {
                    ViewFamilyType viewFamilyType = new FilteredElementCollector(doc)
                        .OfClass(typeof(ViewFamilyType))
                        .Cast<ViewFamilyType>()
                        .FirstOrDefault(x => x.ViewFamily == ViewFamily.ThreeDimensional);
                    
                    View3D view3d = View3D.CreatePerspective(doc, viewFamilyType.Id);
                    view3d.Name = viewCmd.Parameters.Name;
                    
                    // Set display style to Realistic for better visibility
                    view3d.get_Parameter(BuiltInParameter.MODEL_GRAPHICS_STYLE).Set(6); // 6 = Realistic
                }
            }
        }

        // Helper methods
        private T GetElementById<T>(string id) where T : Element
        {
            // Implementation depends on how IDs are tracked
            return null; 
        }

        private WallType GetWallType(string name)
        {
            return new FilteredElementCollector(doc).OfClass(typeof(WallType)).Cast<WallType>().FirstOrDefault(x => x.Name == name);
        }

        private FloorType GetFloorType(string name)
        {
            return new FilteredElementCollector(doc).OfClass(typeof(FloorType)).Cast<FloorType>().FirstOrDefault(x => x.Name == name);
        }

        private Level GetLevel(string name)
        {
            return new FilteredElementCollector(doc).OfClass(typeof(Level)).Cast<Level>().FirstOrDefault(x => x.Name == name);
        }

        private FamilySymbol GetFamilySymbol(string familyName, string symbolName)
        {
            return new FilteredElementCollector(doc)
                .OfClass(typeof(FamilySymbol))
                .Cast<FamilySymbol>()
                .FirstOrDefault(x => x.Family.Name == familyName && x.Name == symbolName);
        }

        private void SetWallProperties(Wall wall, WallProperties props)
        {
            // Parameter setting logic...
        }
    }

    // Data Models (Simplified)
    public class RevitTransaction {
        public List<LevelCommand> Levels { get; set; }
        public List<WallCommand> Walls { get; set; }
        public List<DoorCommand> Doors { get; set; }
        public List<WindowCommand> Windows { get; set; }
        public List<FloorCommand> Floors { get; set; }
        public List<RoomCommand> Rooms { get; set; }
        public List<ViewCommand> Views { get; set; }
    }

    public class LevelCommand { public string Name { get; set; } public double Elevation { get; set; } }
    public class WallCommand { public WallParameters Parameters { get; set; } public WallProperties Properties { get; set; } }
    public class WallParameters { public CurveData Curve { get; set; } public string WallType { get; set; } public string Level { get; set; } public double Height { get; set; } public double Offset { get; set; } public bool Flip { get; set; } public bool Structural { get; set; } }
    public class CurveData { public PointData Start { get; set; } public PointData End { get; set; } }
    public class PointData { public double X { get; set; } public double Y { get; set; } public double Z { get; set; } }
    public class WallProperties { public string Function { get; set; } public string FireRating { get; set; } }
    public class DoorCommand { public DoorParameters Parameters { get; set; } }
    public class DoorParameters { public string Family { get; set; } public string Symbol { get; set; } public PointData Location { get; set; } public string HostWallId { get; set; } public string Level { get; set; } public double Rotation { get; set; } }
    public class WindowCommand { public WindowParameters Parameters { get; set; } }
    public class WindowParameters { public string Family { get; set; } public string Symbol { get; set; } public PointData Location { get; set; } public string HostWallId { get; set; } public string Level { get; set; } }
    public class FloorCommand { public FloorParameters Parameters { get; set; } }
    public class FloorParameters { public List<PointData> Boundary { get; set; } public string FloorType { get; set; } public string Level { get; set; } public bool Structural { get; set; } }
    public class RoomCommand { public RoomParameters Parameters { get; set; } }
    public class RoomParameters { public string Name { get; set; } public string Number { get; set; } public string Level { get; set; } public PointData Point { get; set; } }
    public class ViewCommand { public ViewParameters Parameters { get; set; } }
    public class ViewParameters { public string ViewType { get; set; } public string Name { get; set; } }
}
