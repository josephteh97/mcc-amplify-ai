using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Serilog;

namespace RevitService
{
    public class ModelBuilder
    {
        private readonly Application _app;
        private readonly Config _config;
        private Document? _doc;

        public ModelBuilder(Application app, Config config)
        {
            _app = app;
            _config = config;
        }

        public async Task<string> BuildModel(RevitTransaction transaction, string outputPath)
        {
            return await Task.Run(() =>
            {
                try
                {
                    // Create new document
                    Log.Information("Creating new Revit document...");
                    _doc = _app.NewProjectDocument(_config.RevitSettings.TemplatePath);
                    
                    // Start transaction
                    using (Transaction trans = new Transaction(_doc, "Build Floor Plan Model"))
                    {
                        trans.Start();

                        try
                        {
                            // Build model components
                            if (transaction.Levels != null)
                                CreateLevels(transaction.Levels);
                            
                            if (transaction.Walls != null)
                                CreateWalls(transaction.Walls);
                            
                            if (transaction.Doors != null)
                                CreateDoors(transaction.Doors);
                            
                            if (transaction.Windows != null)
                                CreateWindows(transaction.Windows);
                            
                            if (transaction.Floors != null)
                                CreateFloors(transaction.Floors);

                            trans.Commit();
                            Log.Information("✓ Transaction committed successfully");
                        }
                        catch (Exception ex)
                        {
                            trans.RollBack();
                            Log.Error(ex, "Transaction failed, rolling back");
                            throw;
                        }
                    }

                    // Save document
                    Log.Information($"Saving document to: {outputPath}");
                    SaveAsOptions saveOptions = new SaveAsOptions
                    {
                        OverwriteExistingFile = true
                    };
                    _doc.SaveAs(outputPath, saveOptions);

                    // Close document
                    _doc.Close(false);
                    _doc = null;

                    Log.Information("✓ Model saved and closed");
                    return outputPath;
                }
                catch (Exception ex)
                {
                    Log.Error(ex, "Failed to build model");
                    if (_doc != null)
                    {
                        _doc.Close(false);
                        _doc = null;
                    }
                    throw;
                }
            });
        }

        private void CreateLevels(List<LevelCommand> levels)
        {
            Log.Information($"Creating {levels.Count} levels...");
            // Level creation logic here
        }

        private void CreateWalls(List<WallCommand> walls)
        {
            Log.Information($"Creating {walls.Count} walls...");
            
            foreach (var wallCmd in walls)
            {
                try
                {
                    if (wallCmd.Parameters?.Curve == null) continue;

                    // Get wall type
                    WallType? wallType = GetWallType(wallCmd.Parameters.WallType);
                    if (wallType == null) continue;

                    // Get level
                    Level? level = GetLevel(wallCmd.Parameters.Level);
                    if (level == null) continue;

                    // Create curve
                    XYZ start = new XYZ(
                        wallCmd.Parameters.Curve.Start!.X / 304.8, // mm to feet
                        wallCmd.Parameters.Curve.Start.Y / 304.8,
                        wallCmd.Parameters.Curve.Start.Z / 304.8
                    );

                    XYZ end = new XYZ(
                        wallCmd.Parameters.Curve.End!.X / 304.8,
                        wallCmd.Parameters.Curve.End.Y / 304.8,
                        wallCmd.Parameters.Curve.End.Z / 304.8
                    );

                    Line line = Line.CreateBound(start, end);

                    // Create wall
                    Wall.Create(
                        _doc!,
                        line,
                        wallType.Id,
                        level.Id,
                        wallCmd.Parameters.Height / 304.8, // mm to feet
                        0,
                        false,
                        wallCmd.Parameters.Structural
                    );
                }
                catch (Exception ex)
                {
                    Log.Warning(ex, $"Failed to create wall: {wallCmd.Id}");
                }
            }
        }

        private void CreateDoors(List<DoorCommand> doors)
        {
            Log.Information($"Creating {doors.Count} doors...");
            // Door creation logic
        }

        private void CreateWindows(List<WindowCommand> windows)
        {
            Log.Information($"Creating {windows.Count} windows...");
            // Window creation logic
        }

        private void CreateFloors(List<FloorCommand> floors)
        {
            Log.Information($"Creating {floors.Count} floors...");
            // Floor creation logic
        }

        private WallType? GetWallType(string typeName)
        {
            FilteredElementCollector collector = new FilteredElementCollector(_doc!);
            return collector.OfClass(typeof(WallType))
                .Cast<WallType>()
                .FirstOrDefault(wt => wt.Name == typeName);
        }

        private Level? GetLevel(string levelName)
        {
            FilteredElementCollector collector = new FilteredElementCollector(_doc!);
            return collector.OfClass(typeof(Level))
                .Cast<Level>()
                .FirstOrDefault(l => l.Name == levelName);
        }
    }
}
