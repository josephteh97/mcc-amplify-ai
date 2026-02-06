using System;
using System.Net;
using System.Text;
using System.Threading.Tasks;
using System.IO;
using Newtonsoft.Json;
using System.Collections.Generic;

namespace RevitService
{
    public class ApiServer
    {
        private HttpListener listener;
        private ModelBuilder modelBuilder;
        
        public ApiServer(ModelBuilder builder)
        {
            listener = new HttpListener();
            listener.Prefixes.Add("http://+:5000/");
            modelBuilder = builder;
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
        
        private async void ProcessRequest(HttpListenerContext context)
        {
            try
            {
                if (context.Request.HttpMethod == "POST" && context.Request.Url.AbsolutePath == "/build-model")
                {
                    await HandleBuildModel(context);
                }
                else if (context.Request.HttpMethod == "POST" && context.Request.Url.AbsolutePath == "/render-model")
                {
                    await HandleRenderModel(context);
                }
                else if (context.Request.HttpMethod == "GET" && context.Request.Url.AbsolutePath == "/health")
                {
                    byte[] response = Encoding.UTF8.GetBytes("Revit service healthy");
                    context.Response.ContentType = "text/plain";
                    context.Response.ContentLength64 = response.Length;
                    context.Response.OutputStream.Write(response, 0, response.Length);
                    context.Response.OutputStream.Close();
                }
                else
                {
                    context.Response.StatusCode = 404;
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

        private async Task HandleBuildModel(HttpListenerContext context)
        {
            string requestBody;
            using (var reader = new StreamReader(context.Request.InputStream))
            {
                requestBody = await reader.ReadToEndAsync();
            }
            
            var request = JsonConvert.DeserializeObject<BuildRequest>(requestBody);
            var recipe = JsonConvert.DeserializeObject<RevitRecipe>(request.TransactionJson);
            
            string outputPath = Path.Combine(@"C:\RevitOutput", $"{request.JobId}.rvt");
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            
            string resultPath = await modelBuilder.BuildModel(recipe, outputPath);
            
            byte[] rvtFile = File.ReadAllBytes(resultPath);
            context.Response.ContentType = "application/octet-stream";
            context.Response.ContentLength64 = rvtFile.Length;
            context.Response.AddHeader("Content-Disposition", $"attachment; filename={request.JobId}.rvt");
            context.Response.OutputStream.Write(rvtFile, 0, rvtFile.Length);
            context.Response.OutputStream.Close();
            
            Console.WriteLine($"Model built successfully: {request.JobId}");
        }

        private async Task HandleRenderModel(HttpListenerContext context)
        {
            // Simple Multipart Parser (Production should use a library like HttpMultipartParser)
            string boundary = context.Request.ContentType.Split('=')[1];
            string jobId = "";
            string tempRvtPath = "";

            // NOTE: This is a simplified placeholder for multipart parsing logic.
            // In a real production environment, use a robust library to extract the file and form fields.
            // Assuming for now the file is saved to a temp path
            
            // ... (Multipart parsing logic would go here) ...
            
            // Placeholder: Assume file is saved to C:\RevitOutput\temp\{jobId}.rvt
            // For now, let's pretend we parsed it:
            jobId = context.Request.Headers["X-Job-ID"] ?? Guid.NewGuid().ToString(); // Fallback if parsing fails
            
            // In a real scenario, you'd save the stream to a file first
            // var fileStream = ...
            
            string outputDir = Path.Combine(@"C:\RevitOutput", jobId);
            Directory.CreateDirectory(outputDir);
            
            string renderPath = modelBuilder.RenderModel(tempRvtPath, outputDir);
            
            byte[] imgFile = File.ReadAllBytes(renderPath);
            context.Response.ContentType = "image/png";
            context.Response.ContentLength64 = imgFile.Length;
            context.Response.OutputStream.Write(imgFile, 0, imgFile.Length);
            context.Response.OutputStream.Close();
        }
        
        public void Stop()
        {
            listener.Stop();
            listener.Close();
        }
    }
}
