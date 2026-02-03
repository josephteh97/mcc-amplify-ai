// windows_server/RevitService/ApiServer.cs

using System;
using System.Net;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace RevitService
{
    public class ApiServer
    {
        private HttpListener listener;
        private ModelBuilder modelBuilder;
        
        public ApiServer()
        {
            listener = new HttpListener();
            listener.Prefixes.Add("http://+:5000/");
            modelBuilder = new ModelBuilder();
        }
        
        public void Start()
        {
            listener.Start();
            Console.WriteLine("Revit API Server started on port 5000");
            
            Task.Run(() => Listen());
        }
        
        private async void Listen()
        {
            while (listener.IsListening)
            {
                var context = await listener.GetContextAsync();
                ProcessRequest(context);
            }
        }
        
        private void ProcessRequest(HttpListenerContext context)
        {
            try
            {
                if (context.Request.HttpMethod == "POST" && 
                    context.Request.Url.AbsolutePath == "/build-model")
                {
                    // Read request body
                    string requestBody;
                    using (var reader = new System.IO.StreamReader(context.Request.InputStream))
                    {
                        requestBody = reader.ReadToEnd();
                    }
                    
                    var request = JsonConvert.DeserializeObject<BuildRequest>(requestBody);
                    
                    // Build Revit model
                    string outputPath = $"C:\\RevitOutput\\{request.JobId}.rvt";
                    string resultPath = modelBuilder.BuildModel(
                        request.TransactionJson,
                        outputPath
                    );
                    
                    // Return RVT file
                    byte[] rvtFile = System.IO.File.ReadAllBytes(resultPath);
                    
                    context.Response.ContentType = "application/octet-stream";
                    context.Response.ContentLength64 = rvtFile.Length;
                    context.Response.AddHeader("Content-Disposition", 
                        $"attachment; filename={request.JobId}.rvt");
                    
                    context.Response.OutputStream.Write(rvtFile, 0, rvtFile.Length);
                    context.Response.OutputStream.Close();
                    
                    Console.WriteLine($"Model built successfully: {request.JobId}");
                }
                else if (context.Request.HttpMethod == "GET" && 
                         context.Request.Url.AbsolutePath == "/health")
                {
                    // Health check
                    byte[] response = Encoding.UTF8.GetBytes("Revit service healthy");
                    context.Response.ContentType = "text/plain";
                    context.Response.ContentLength64 = response.Length;
                    context.Response.OutputStream.Write(response, 0, response.Length);
                    context.Response.OutputStream.Close();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
                context.Response.StatusCode = 500;
                byte[] error = Encoding.UTF8.GetBytes(ex.Message);
                context.Response.OutputStream.Write(error, 0, error.Length);
                context.Response.OutputStream.Close();
            }
        }
        
        public void Stop()
        {
            listener.Stop();
            listener.Close();
        }
    }
    
    public class BuildRequest
    {
        public string JobId { get; set; }
        public string TransactionJson { get; set; }
    }
}
