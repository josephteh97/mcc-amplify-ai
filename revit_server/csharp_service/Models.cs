using System.Collections.Generic;

namespace RevitService
{
    public class Config
    {
        public RevitSettings RevitSettings { get; set; } = new();
        public ApiSettings ApiSettings { get; set; } = new();
        public LoggingSettings LoggingSettings { get; set; } = new();
    }

    public class RevitSettings
    {
        public string Version { get; set; } = "2023";
        public string TemplatePath { get; set; } = @"C:\ProgramData\Autodesk\RVT 2023\Templates\Architectural Template.rte";
        public string OutputDirectory { get; set; } = @"C:\RevitOutput";
        public bool EnableHeadless { get; set; } = true;
    }

    public class ApiSettings
    {
        public string Host { get; set; } = "0.0.0.0";
        public int Port { get; set; } = 5000;
        public string ApiKey { get; set; } = "change-this-key";
        public int TimeoutSeconds { get; set; } = 300;
    }

    public class LoggingSettings
    {
        public string Level { get; set; } = "Information";
        public string Directory { get; set; } = "logs";
    }

    // ========================================================================
    // Request/Response Models
    // ========================================================================

    public class BuildRequest
    {
        public string JobId { get; set; } = "";
        public string TransactionJson { get; set; } = "";
    }

    public class RevitTransaction
    {
        public string Version { get; set; } = "";
        public string Template { get; set; } = "";
        public ProjectInfo? ProjectInfo { get; set; }
        public List<LevelCommand>? Levels { get; set; }
        public List<WallCommand>? Walls { get; set; }
        public List<DoorCommand>? Doors { get; set; }
        public List<WindowCommand>? Windows { get; set; }
        public List<FloorCommand>? Floors { get; set; }
    }

    public class ProjectInfo
    {
        public string Name { get; set; } = "";
        public string Author { get; set; } = "";
        public string CreatedDate { get; set; } = "";
    }

    public class LevelCommand
    {
        public string Name { get; set; } = "";
        public double Elevation { get; set; }
    }

    public class WallCommand
    {
        public string Id { get; set; } = "";
        public string Command { get; set; } = "";
        public WallParameters? Parameters { get; set; }
        public WallProperties? Properties { get; set; }
    }

    public class WallParameters
    {
        public CurveData? Curve { get; set; }
        public string WallType { get; set; } = "";
        public string Level { get; set; } = "";
        public double Height { get; set; }
        public bool Structural { get; set; }
    }

    public class WallProperties
    {
        public string Function { get; set; } = "";
        public string Material { get; set; } = "";
        public double Thickness { get; set; }
    }

    public class CurveData
    {
        public string Type { get; set; } = "";
        public Point3D? Start { get; set; }
        public Point3D? End { get; set; }
    }

    public class Point3D
    {
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
    }

    public class DoorCommand
    {
        public string Id { get; set; } = "";
        public DoorParameters? Parameters { get; set; }
    }

    public class DoorParameters
    {
        public string Family { get; set; } = "";
        public string Symbol { get; set; } = "";
        public Point3D? Location { get; set; }
        public string HostWallId { get; set; } = "";
        public string Level { get; set; } = "";
    }

    public class WindowCommand
    {
        public string Id { get; set; } = "";
        public WindowParameters? Parameters { get; set; }
    }

    public class WindowParameters
    {
        public string Family { get; set; } = "";
        public string Symbol { get; set; } = "";
        public Point3D? Location { get; set; }
        public string HostWallId { get; set; } = "";
        public string Level { get; set; } = "";
    }

    public class FloorCommand
    {
        public string Id { get; set; } = "";
        public FloorParameters? Parameters { get; set; }
    }

    public class FloorParameters
    {
        public List<List<double>>? Boundary { get; set; }
        public string FloorType { get; set; } = "";
        public string Level { get; set; } = "";
    }
}
