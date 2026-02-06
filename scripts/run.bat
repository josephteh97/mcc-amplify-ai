@echo off
echo Starting Amplify AI Backend...

cd ..\backend
call venv\Scripts\activate

echo Starting FastAPI Server...
cd C:\MyDocuments\mcc-amplify-ai\revit_server\csharp_service
dotnet build
