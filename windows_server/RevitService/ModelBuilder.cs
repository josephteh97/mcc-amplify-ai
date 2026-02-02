// windows_server/RevitService/ModelBuilder.cs

using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace RevitService
{
    public class ModelBuilder
    {
        private Application revitApp;
        private Document doc;
        
        public ModelBuilder()
        {
            // Initialize Revit application
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
        
        private void CreateWalls(List<WallCommand> walls)
        {
            foreach (var wallCmd in walls)
            {
                // Get wall type
                WallType wallType = GetWallType(wallCmd.Parameters.WallType);
                
                // Get level
                Level level = GetLevel(wallCmd.Parameters.Level);
                
                // Create curve
                XYZ startPoint = new XYZ(
                    wallCmd.Parameters.Curve.Start.X,
                    wallCmd.Parameters.Curve.Start.Y,
                    wallCmd.Parameters.Curve.Start.Z
                );
                
                XYZ endPoint = new XYZ(
                    wallCmd.Parameters.Curve.End.X,
                    wallCmd.Parameters.Curve.End.Y,
                    wallCmd.Parameters.Curve.End.Z
                );
                
                Line wallLine = Line.CreateBound(startPoint, endPoint);
                
                // Create wall
                Wall wall = Wall.Create(
                    doc,
                    wallLine,
                    wallType.Id,
                    level.Id,
                    wallCmd.Parameters.Height / 304.8, // mm to feet
                    wallCmd.Parameters.Offset,
                    wallCmd.Parameters.Flip,
                    wallCmd.Parameters.Structural
                );
                
                // Set additional properties
                SetWallProperties(wall, wallCmd.Properties);
            }
        }
        
        private void CreateDoors(List<DoorCommand> doors)
        {
            foreach (var doorCmd in doors)
            {
                // Get door family symbol
                FamilySymbol doorSymbol = GetDoorSymbol(
                    doorCmd.Parameters.Family,
                    doorCmd.Parameters.Symbol
                );
                
                // Activate symbol if not active
                if (!doorSymbol.IsActive)
                {
                    doorSymbol.Activate();
                    doc.Regenerate();
                }
                
                // Get host wall
                Wall hostWall = doc.GetElement(new ElementId(doorCmd.Parameters.HostWallId)) as Wall;
                
                // Get level
                Level level = GetLevel(doorCmd.Parameters.Level);
                
                // Create location point
                XYZ location = new XYZ(
                    doorCmd.Parameters.Location.X,
                    doorCmd.Parameters.Location.Y,
                    doorCmd.Parameters.Location.Z
                );
                
                // Create door instance
                FamilyInstance door = doc.Create.NewFamilyInstance(
                    location,
                    doorSymbol,
                    hostWall,
                    level,
                    StructuralType.NonStructural
                );
                
                // Set rotation if specified
                if (doorCmd.Parameters.Rotation != 0)
                {
                    Line axis = Line.CreateBound(location, location + XYZ.BasisZ);
                    ElementTransformUtils.RotateElement(
                        doc,
                        door.Id,
                        axis,
                        doorCmd.Parameters.Rotation * Math.PI / 180
                    );
                }
                
                // Set door properties
                SetDoorProperties(door, doorCmd.Properties);
            }
        }
        
        private void SetWallProperties(Wall wall, WallProperties props)
        {
            // Set function parameter
            Parameter functionParam = wall.get_Parameter(BuiltInParameter.WALL_FUNCTION);
            if (functionParam != null)
            {
                functionParam.Set((int)GetWallFunction(props.Function));
            }
            
            // Set fire rating
            Parameter fireRatingParam = wall.get_Parameter(BuiltInParameter.DOOR_FIRE_RATING);
            if (fireRatingParam != null && !string.IsNullOrEmpty(props.FireRating))
            {
                fireRatingParam.Set(props.FireRating);
            }
            
            // Additional properties...
        }
        
        private WallType GetWallType(string wallTypeName)
        {
            // Find wall type by name
            FilteredElementCollector collector = new FilteredElementCollector(doc);
            collector.OfClass(typeof(WallType));
            
            foreach (WallType wallType in collector)
            {
                if (wallType.Name == wallTypeName)
                {
                    return wallType;
                }
            }
            
            // Return default if not found
            return collector.FirstElement() as WallType;
        }
        
        private Level GetLevel(string levelName)
        {
            FilteredElementCollector collector = new FilteredElementCollector(doc);
            collector.OfClass(typeof(Level));
            
            foreach (Level level in collector)
            {
                if (level.Name == levelName)
                {
                    return level;
                }
            }
            
            return collector.FirstElement() as Level;
        }
    }
    
    // Data models matching JSON structure
    public class RevitTransaction
    {
        public string Version { get; set; }
        public string Template { get; set; }
        public ProjectInfo ProjectInfo { get; set; }
        public List<LevelCommand> Levels { get; set; }
        public List<WallCommand> Walls { get; set; }
        public List<DoorCommand> Doors { get; set; }
        public List<WindowCommand> Windows { get; set; }
        public List<FloorCommand> Floors { get; set; }
        public List<RoomCommand> Rooms { get; set; }
        public List<ViewCommand> Views { get; set; }
    }
    
    public class WallCommand
    {
        public string Command { get; set; }
        public WallParameters Parameters { get; set; }
        public WallProperties Properties { get; set; }
    }
    
    public class WallParameters
    {
        public CurveData Curve { get; set; }
        public string WallType { get; set; }
        public string Level { get; set; }
        public double Height { get; set; }
        public double Offset { get; set; }
        public bool Flip { get; set; }
        public bool Structural { get; set; }
    }
}
