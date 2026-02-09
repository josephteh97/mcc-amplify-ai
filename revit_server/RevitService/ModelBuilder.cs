// windows_server/RevitService/ModelBuilder.cs
using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.DB.Structure;
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
                if (transaction == null)
                {
                    throw new ArgumentNullException(nameof(transactionJson), "Failed to deserialize transaction JSON");
                }

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

                    // Create columns
                    CreateColumns(transaction.Columns);

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

        private void CreateLevels(List<LevelCommand>? levels)
        {
            if (levels == null) return;
            foreach (var levelCmd in levels)
            {
                Level level = Level.Create(doc, levelCmd.Elevation * MM_TO_FEET);
                level.Name = levelCmd.Name;
            }
        }

        private void CreateWalls(List<WallCommand>? walls)
        {
            if (walls == null) return;
            foreach (var wallCmd in walls)
            {
                WallType? wallType = GetWallType(wallCmd.Parameters.WallType);
                if (wallType == null) continue;

                Level? level = GetLevel(wallCmd.Parameters.Level);
                if (level == null) continue;

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

        private void CreateDoors(List<DoorCommand>? doors)
        {
            if (doors == null) return;
            foreach (var doorCmd in doors)
            {
                FamilySymbol? doorSymbol = GetFamilySymbol(doorCmd.Parameters.Family, doorCmd.Parameters.Symbol);
                if (doorSymbol == null) continue;
                if (!doorSymbol.IsActive) doorSymbol.Activate();

                Wall? hostWall = GetElementById<Wall>(doorCmd.Parameters.HostWallId);
                if (hostWall == null) continue;

                Level? level = GetLevel(doorCmd.Parameters.Level);
                if (level == null) continue;

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

        private void CreateWindows(List<WindowCommand>? windows)
        {
            if (windows == null) return;
            foreach (var winCmd in windows)
            {
                FamilySymbol? winSymbol = GetFamilySymbol(winCmd.Parameters.Family, winCmd.Parameters.Symbol);
                if (winSymbol == null) continue;
                if (!winSymbol.IsActive) winSymbol.Activate();

                Wall? hostWall = GetElementById<Wall>(winCmd.Parameters.HostWallId);
                if (hostWall == null) continue;

                Level? level = GetLevel(winCmd.Parameters.Level);
                if (level == null) continue;

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

        private void CreateColumns(List<ColumnCommand>? columns)
        {
            if (columns == null) return;
            foreach (var colCmd in columns)
            {
                FamilySymbol? colSymbol = GetFamilySymbol(colCmd.Parameters.Family, colCmd.Parameters.Symbol);
                if (colSymbol == null) continue;
                if (!colSymbol.IsActive) colSymbol.Activate();

                Level? level = GetLevel(colCmd.Parameters.Level);
                if (level == null) continue;

                XYZ location = new XYZ(
                    colCmd.Parameters.Location.X * MM_TO_FEET,
                    colCmd.Parameters.Location.Y * MM_TO_FEET,
                    colCmd.Parameters.Location.Z * MM_TO_FEET
                );

                FamilyInstance column = doc.Create.NewFamilyInstance(
                    location,
                    colSymbol,
                    level,
                    StructuralType.Column
                );

                // Set top level and offset to match height (simplified example)
                Parameter? topLevelParam = column.get_Parameter(BuiltInParameter.FAMILY_TOP_LEVEL_PARAM);
                if (topLevelParam != null)
                {
                    Level? topLevel = GetLevel("Level 2"); // ← adjust logic as needed
                    if (topLevel != null)
                    {
                        topLevelParam.Set(topLevel.Id);
                    }
                }

                if (colCmd.Parameters.Rotation != 0)
                {
                    Line axis = Line.CreateBound(location, location + XYZ.BasisZ);
                    ElementTransformUtils.RotateElement(doc, column.Id, axis, colCmd.Parameters.Rotation * Math.PI / 180);
                }
            }
        }

        private void CreateFloors(List<FloorCommand>? floors)
        {
            if (floors == null) return;
            foreach (var floorCmd in floors)
            {
                if (floorCmd.Parameters.Boundary == null || floorCmd.Parameters.Boundary.Count < 3) continue;

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

                FloorType? floorType = GetFloorType(floorCmd.Parameters.FloorType);
                if (floorType == null) continue;

                Level? level = GetLevel(floorCmd.Parameters.Level);
                if (level == null) continue;

                doc.Create.NewFloor(profile, floorType, level, floorCmd.Parameters.Structural);
            }
        }

        private void CreateRooms(List<RoomCommand>? rooms)
        {
            if (rooms == null) return;
            foreach (var roomCmd in rooms)
            {
                Level? level = GetLevel(roomCmd.Parameters.Level);
                if (level == null) continue;

                UV point = new UV(
                    roomCmd.Parameters.Point.X * MM_TO_FEET,
                    roomCmd.Parameters.Point.Y * MM_TO_FEET
                );

                Room room = doc.Create.NewRoom(level, point);
                room.Name = roomCmd.Parameters.Name;
                room.Number = roomCmd.Parameters.Number;
            }
        }

        private void CreateViews(List<ViewCommand>? views)
        {
            if (views == null) return;
            foreach (var viewCmd in views)
            {
                if (viewCmd.Parameters.ViewType == "3D")
                {
                    ViewFamilyType? viewFamilyType = new FilteredElementCollector(doc)
                        .OfClass(typeof(ViewFamilyType))
                        .Cast<ViewFamilyType>()
                        .FirstOrDefault(x => x.ViewFamily == ViewFamily.ThreeDimensional);

                    if (viewFamilyType == null) continue;

                    View3D view3d = View3D.CreatePerspective(doc, viewFamilyType.Id);
                    view3d.Name = viewCmd.Parameters.Name;

                    // Set display style to Realistic for better visibility
                    view3d.get_Parameter(BuiltInParameter.MODEL_GRAPHICS_STYLE)?.Set(6); // 6 = Realistic
                }
            }
        }

        // Helper methods
        private T? GetElementById<T>(string? id) where T : Element
        {
            if (string.IsNullOrEmpty(id)) return null;
            // TODO: Implement proper lookup (e.g. using a dictionary of created elements or ElementId)
            // Example placeholder:
            // return doc.GetElement(new ElementId(long.Parse(id))) as T;
            return null;
        }

        private WallType? GetWallType(string? name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            return new FilteredElementCollector(doc)
                .OfClass(typeof(WallType))
                .Cast<WallType>()
                .FirstOrDefault(x => x.Name == name);
        }

        private FloorType? GetFloorType(string? name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            return new FilteredElementCollector(doc)
                .OfClass(typeof(FloorType))
                .Cast<FloorType>()
                .FirstOrDefault(x => x.Name == name);
        }

        private Level? GetLevel(string? name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            return new FilteredElementCollector(doc)
                .OfClass(typeof(Level))
                .Cast<Level>()
                .FirstOrDefault(x => x.Name == name);
        }

        private FamilySymbol? GetFamilySymbol(string? familyName, string? symbolName)
        {
            if (string.IsNullOrEmpty(familyName) || string.IsNullOrEmpty(symbolName)) return null;
            return new FilteredElementCollector(doc)
                .OfClass(typeof(FamilySymbol))
                .Cast<FamilySymbol>()
                .FirstOrDefault(x => x.Family?.Name == familyName && x.Name == symbolName);
        }

        private void SetWallProperties(Wall wall, WallProperties? props)
        {
            if (props == null) return;
            // Parameter setting logic...
            // Example:
            // wall.get_Parameter(BuiltInParameter.WALL_FUNCTION)?.Set(...);
        }
    }

    // Data Models (with nullability suppression for JSON deserialization)
    public class RevitTransaction
    {
        public List<LevelCommand> Levels { get; set; } = default!;
        public List<WallCommand> Walls { get; set; } = default!;
        public List<DoorCommand> Doors { get; set; } = default!;
        public List<WindowCommand> Windows { get; set; } = default!;
        public List<ColumnCommand> Columns { get; set; } = default!;
        public List<FloorCommand> Floors { get; set; } = default!;
        public List<RoomCommand> Rooms { get; set; } = default!;
        public List<ViewCommand> Views { get; set; } = default!;
    }

    public class LevelCommand { public string Name { get; set; } = default!; public double Elevation { get; set; } }
    public class WallCommand { public WallParameters Parameters { get; set; } = default!; public WallProperties Properties { get; set; } = default!; }
    public class WallParameters
    {
        public CurveData Curve { get; set; } = default!;
        public string WallType { get; set; } = default!;
        public string Level { get; set; } = default!;
        public double Height { get; set; }
        public double Offset { get; set; }
        public bool Flip { get; set; }
        public bool Structural { get; set; }
    }
    public class CurveData { public PointData Start { get; set; } = default!; public PointData End { get; set; } = default!; }
    public class PointData { public double X { get; set; } public double Y { get; set; } public double Z { get; set; } }
    public class WallProperties { public string Function { get; set; } = default!; public string FireRating { get; set; } = default!; }

    public class DoorCommand { public DoorParameters Parameters { get; set; } = default!; }
    public class DoorParameters
    {
        public string Family { get; set; } = default!;
        public string Symbol { get; set; } = default!;
        public PointData Location { get; set; } = default!;
        public string HostWallId { get; set; } = default!;
        public string Level { get; set; } = default!;
        public double Rotation { get; set; }
    }

    public class WindowCommand { public WindowParameters Parameters { get; set; } = default!; }
    public class WindowParameters
    {
        public string Family { get; set; } = default!;
        public string Symbol { get; set; } = default!;
        public PointData Location { get; set; } = default!;
        public string HostWallId { get; set; } = default!;
        public string Level { get; set; } = default!;
    }

    public class ColumnCommand { public ColumnParameters Parameters { get; set; } = default!; public ColumnProperties Properties { get; set; } = default!; }
    public class ColumnParameters
    {
        public string Family { get; set; } = default!;
        public string Symbol { get; set; } = default!;
        public PointData Location { get; set; } = default!;
        public string Level { get; set; } = default!;
        public double Height { get; set; }
        public double Rotation { get; set; }
    }
    public class ColumnProperties { public double Width { get; set; } public double Depth { get; set; } public string Material { get; set; } = default!; }

    public class FloorCommand { public FloorParameters Parameters { get; set; } = default!; }
    public class FloorParameters
    {
        public List<PointData> Boundary { get; set; } = default!;
        public string FloorType { get; set; } = default!;
        public string Level { get; set; } = default!;
        public bool Structural { get; set; }
    }

    public class RoomCommand { public RoomParameters Parameters { get; set; } = default!; }
    public class RoomParameters
    {
        public string Name { get; set; } = default!;
        public string Number { get; set; } = default!;
        public string Level { get; set; } = default!;
        public PointData Point { get; set; } = default!;
    }

    public class ViewCommand { public ViewParameters Parameters { get; set; } = default!; }
    public class ViewParameters { public string ViewType { get; set; } = default!; public string Name { get; set; } = default!; }
}