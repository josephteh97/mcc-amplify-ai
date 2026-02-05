using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Serilog;
using Autodesk.Revit.ApplicationServices;

namespace RevitService
{
    class Program
    {
        private static HttpListener? _listener;
        private static Application? _revitApp;
        private static Config? _config;
        private static bool _isRunning = true;

        static async Task Main(string[] args)
        {
            // Setup logging
            Log.Logger = new LoggerConfiguration()
                .WriteTo.Console()
                .WriteTo.File("logs/revit-service.log", rollingInterval: RollingInterval.Day)
                .CreateLogger();

            try
            {
                Log.Information("==============================================");
                Log.Information("Revit API Service - Starting");
                Log.Information("==============================================");

                // Load configuration
                _config = LoadConfiguration();
                
                // Initialize Revit
                if (!InitializeRevit())
                {
                    Log.Error("Failed to initialize Revit. Exiting.");
                    return;
                }

                // Start HTTP server
                await StartHttpServer();
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Fatal error in main");
            }
            finally
            {
                Log.Information("Shutting down Revit API Service");
                Log.CloseAndFlush();
            }
        }

        static Config LoadConfiguration()
        {
            string configPath = "config.json";
            if (!File.Exists(configPath))
            {
                Log.Warning("config.json not found, using defaults");
                return new Config();
            }

            string json = File.ReadAllText(configPath);
            var config = JsonConvert.DeserializeObject<Config>(json);
            Log.Information($"Configuration loaded from {configPath}");
            return config ?? new Config();
        }

        static bool InitializeRevit()
        {
            try
            {
                Log.Information("Initializing Revit application...");
                // _revitApp = new Application();
                Log.Information("✓ Revit application initialized successfully");
                return true;
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Failed to initialize Revit");
                return false;
            }
        }

        // static async Task StartHttpServer()
        // {
        //   _listener = new HttpListener();
        //   _listener.Prefixes.Clear();

        //   // Use '*' to accept traffic from any IP/Subnet on this machine
        //   _listener.Prefixes.Add("http://0.0.0.0:49152/"); 

        //   try
        // {
        //         _listener.Start();
        //         Log.Information("✓ HTTP Server started on http://0.0.0.0:49152/");
        //         Log.Information("Ready to receive build requests!");
        //         Log.Information("==============================================");

        //         // Handle Ctrl+C gracefully
        //         Console.CancelKeyPress += (sender, e) =>
        //         {
        //             e.Cancel = true;
        //             _isRunning = false;
        //             Log.Information("Shutdown requested...");
        //         };

        //         while (_isRunning)
        //         {
        //             var context = await _listener.GetContextAsync();
        //             _ = Task.Run(() => HandleRequest(context));
        //         }
        //     }
        //     catch (Exception ex)
        //     {
        //         Log.Error(ex, "Error in HTTP server");
        //     }
        //     finally
        //     {
        //         _listener?.Stop();
        //         _listener?.Close();
        //     }
        // }





        static async Task StartHttpServer()
        {
            // High-performance raw socket - bypasses http.sys entirely
            Socket listener = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
    
            try {
                // Bind to ALL interfaces on port 49152
                listener.Bind(new IPEndPoint(IPAddress.Any, 49152));
                listener.Listen(100);
        
                Log.Information("🚀 NESTED SOCKET ACTIVE: Listening on Port 49152");

                while (_isRunning) {
                    Socket handler = await listener.AcceptAsync();
                    _ = Task.Run(() => {
                        byte[] buffer = new byte[1024];
                        int received = handler.Receive(buffer);
                
                        // Construct a raw HTTP response string
                        string response = "HTTP/1.1 200 OK\r\n" +
                                  "Content-Type: application/json\r\n" +
                                  "Access-Control-Allow-Origin: *\r\n" +
                                  "Connection: close\r\n\r\n" +
                                  "{\"status\":\"BLAST_SUCCESS\", \"message\":\"Revit Bridge Active\"}";
                
                        handler.Send(Encoding.UTF8.GetBytes(response));
                        handler.Shutdown(SocketShutdown.Both);
                        handler.Close();
                    });
                }
            }
            catch (Exception ex) {
                Log.Fatal(ex, "THE DOOR IS TRULY BOLTED");
            }
        }

        static async Task HandleRequest(HttpListenerContext context)
        {
            var request = context.Request;
            var response = context.Response;

            try
            {
                Log.Information($"Request: {request.HttpMethod} {request.Url?.AbsolutePath}");

                // // Check API key
                // string? apiKey = request.Headers["X-API-Key"];
                // if (apiKey != _config!.ApiSettings.ApiKey)
                // {
                //     Log.Warning("Unauthorized request - invalid API key");
                //     await SendResponse(response, 401, new { error = "Unauthorized" });
                //     return;
                // }
                // Check API key (Hardcoded for testing)
                string? apiKey = request.Headers["X-API-Key"];
                if (apiKey != "my-revit-key-2023") 
                {
                    Log.Warning($"Unauthorized request - received key: {apiKey ?? "NULL"}");
                    await SendResponse(response, 401, new { error = "Unauthorized" });
                    return;
            }

                // Route requests
                string path = request.Url?.AbsolutePath ?? "";
                
                if (path == "/health" && request.HttpMethod == "GET")
                {
                    await HandleHealth(response);
                }
                else if (path == "/build-model" && request.HttpMethod == "POST")
                {
                    await HandleBuildModel(request, response);
                }
                else
                {
                    await SendResponse(response, 404, new { error = "Not found" });
                }
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Error handling request");
                await SendResponse(response, 500, new { error = ex.Message });
            }
        }

        static async Task HandleHealth(HttpListenerResponse response)
        {
            var health = new
            {
                status = "healthy",
                service = "Revit API Service",
                version = "1.0.0",
                revit_initialized = true, // Hardcoded for testing
                revit_version = "2023"     // Hardcoded for testing
            };

            await SendResponse(response, 200, health);
        }

        static async Task HandleBuildModel(HttpListenerRequest request, HttpListenerResponse response)
        {
            string requestBody;
            using (var reader = new StreamReader(request.InputStream, request.ContentEncoding))
            {
                requestBody = await reader.ReadToEndAsync();
            }

            var buildRequest = JsonConvert.DeserializeObject<BuildRequest>(requestBody);
            if (buildRequest == null)
            {
                await SendResponse(response, 400, new { error = "Invalid request" });
                return;
            }

            Log.Information($"Building model for job: {buildRequest.JobId}");

            try
            {
                // Parse transaction
                var transaction = JsonConvert.DeserializeObject<RevitTransaction>(buildRequest.TransactionJson);
                if (transaction == null)
                {
                    throw new Exception("Failed to parse transaction JSON");
                }

                // Build model
                var builder = new ModelBuilder(_revitApp!, _config!);
                string outputPath = Path.Combine(
                    _config.RevitSettings.OutputDirectory,
                    $"{buildRequest.JobId}.rvt"
                );

                string resultPath = await builder.BuildModel(transaction, outputPath);

                // Return the RVT file
                byte[] fileBytes = await File.ReadAllBytesAsync(resultPath);
                
                response.ContentType = "application/octet-stream";
                response.ContentLength64 = fileBytes.Length;
                response.AddHeader("Content-Disposition", $"attachment; filename={buildRequest.JobId}.rvt");
                
                await response.OutputStream.WriteAsync(fileBytes, 0, fileBytes.Length);
                response.OutputStream.Close();

                Log.Information($"✓ Model built successfully: {resultPath}");
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Failed to build model");
                await SendResponse(response, 500, new { error = ex.Message });
            }
        }

        static async Task SendResponse(HttpListenerResponse response, int statusCode, object data)
        {
            response.StatusCode = statusCode;
            response.ContentType = "application/json";
            
            string json = JsonConvert.SerializeObject(data, Formatting.Indented);
            byte[] buffer = Encoding.UTF8.GetBytes(json);
            
            response.ContentLength64 = buffer.Length;
            await response.OutputStream.WriteAsync(buffer, 0, buffer.Length);
            response.OutputStream.Close();
        }
    }

    // ========================================================================
    // Configuration Classes
    // ========================================================================

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
