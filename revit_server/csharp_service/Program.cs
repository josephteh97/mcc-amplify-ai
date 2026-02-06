using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Serilog;
using Autodesk.Revit.UI;
using Autodesk.Revit.ApplicationServices;

namespace RevitService
{
    class Program
    {
        private static HttpListener? _listener;
        private static Application? _revitApp;
        private static Config? _config;
        private static bool _isRunning = true;

        // === Global wiring for ExternalEvent (MUST be static) ===
        private static readonly RevitBuildHandler _handler = new RevitBuildHandler();
        private static readonly ExternalEvent _externalEvent = ExternalEvent.Create(_handler);

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

                // Start the socket server
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
                // _revitApp = new Application();  // ← usually not needed in add-in/external context
                Log.Information("✓ Revit application initialized successfully (assuming running inside Revit)");
                return true;
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Failed to initialize Revit");
                return false;
            }
        }

        static async Task StartHttpServer()
        {
            Socket listener = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);

            try
            {
                listener.Bind(new IPEndPoint(IPAddress.Any, 49152));
                listener.Listen(100);
                Log.Information("🚀 SOCKET SERVER ACTIVE: Listening on port 49152");

                while (_isRunning)
                {
                    Socket handler = await listener.AcceptAsync();
                    _ = Task.Run(() => ProcessClient(handler));
                }
            }
            catch (Exception ex)
            {
                Log.Fatal(ex, "Socket listener failed");
            }
            finally
            {
                listener.Close();
            }
        }

        private static void ProcessClient(Socket handler)
        {
            try
            {
                byte[] buffer = new byte[8192];
                int received = handler.Receive(buffer);
                if (received == 0) return;

                string request = Encoding.UTF8.GetString(buffer, 0, received);

                // Extract path (very basic parsing — improve if needed)
                string requestLine = request.Split('\n')[0];
                string requestPath = requestLine.Split(' ')[1].Trim();

                // Extract body (after \r\n\r\n)
                string requestBody = "";
                int bodyStart = request.IndexOf("\r\n\r\n");
                if (bodyStart != -1)
                {
                    requestBody = request.Substring(bodyStart + 4).Trim();
                }

                string jsonResponse;

                if (requestPath == "/health")
                {
                    jsonResponse = "{\"status\":\"HEALTHY\"}";
                }
                else if (requestPath == "/build")
                {
                    Log.Information($"Received build request: {requestBody}");

                    // 1. Pass data to handler (will be picked up in Execute)
                    _handler.Data = requestBody;

                    // 2. Raise the external event → Revit will call Execute() when idling
                    _externalEvent.Raise();

                    Log.Information("✅ ExternalEvent raised — Revit will process when idle");

                    jsonResponse = "{\"status\":\"QUEUED\", \"message\":\"Build event sent to Revit\"}";
                }
                else
                {
                    jsonResponse = "{\"status\":\"NOT_FOUND\"}";
                }

                // Send response immediately (client doesn't wait for Revit)
                string response = "HTTP/1.1 200 OK\r\n" +
                                  "Content-Type: application/json\r\n" +
                                  "Access-Control-Allow-Origin: *\r\n" +
                                  "Connection: close\r\n\r\n" +
                                  jsonResponse;

                handler.Send(Encoding.UTF8.GetBytes(response));
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Error processing client request");
            }
            finally
            {
                if (handler.Connected)
                    handler.Shutdown(SocketShutdown.Both);
                handler.Close();
            }
        }
    }

    // Your existing RevitBuildHandler (runs on Revit's main thread)
    public class RevitBuildHandler : IExternalEventHandler
    {
        public string Data { get; set; } = string.Empty;

        public void Execute(UIApplication app)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(Data))
                {
                    Log.Warning("RevitBuildHandler: No data received.");
                    return;
                }

                Log.Information($"Revit processing build data: {Data}");

                // TODO: Add your real Revit logic here
                // Example:
                // var transactionData = JsonConvert.DeserializeObject<RevitTransaction>(Data);
                // using var tx = new Transaction(app.ActiveUIDocument.Document, "External Build");
                // tx.Start();
                // ... create walls, levels, etc ...
                // tx.Commit();

                // For testing / visibility:
                // TaskDialog.Show("External Build", $"Received data:\n{Data}");
            }
            catch (Exception ex)
            {
                Log.Error(ex, "RevitBuildHandler failed");
                // TaskDialog.Show("Build Error", ex.Message);
            }
        }

        public string GetName() => "Revit Build External Event";
    }

    // ───────────────────────────────────────────────
    // Keep all your other classes (Config, BuildRequest, RevitTransaction, etc.)
    // ───────────────────────────────────────────────
    // ... (paste your existing configuration and model classes here) ...
}