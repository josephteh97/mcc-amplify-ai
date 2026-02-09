@echo off
setlocal
echo ============================================
echo 🛠️  REVIT BRIDGE INITIALIZATION
echo ============================================

:: 1. Navigation
cd /d "C:\MyDocuments\mcc-amplify-ai\revit_server\csharp_service"
echo 📂 Working Directory: %CD%

:: 2. Ubuntu Host Mapping Instruction (Reminder)
echo.
echo [1/6] NETWORK CONFIGURATION:
echo Run this on your UBUNTU machine (not here) to map the hostname:
echo echo "191.168.124.64 LT-HQ-277" ^| sudo tee -a /etc/hosts
echo --------------------------------------------

:: 3. Port Check
echo.
echo [2/6] Checking Port 49152 Status...
netstat -ano | findstr LISTENING | findstr :49152
if %errorlevel% neq 0 echo ⚠️ Port is currently free (No active Revit session).

:: 4. TCP Connection Test
echo.
echo [3/6] Running Local TCP Handshake Test...
powershell -Command "Test-NetConnection -ComputerName localhost -Port 49152"

:: 5. Project Clean
echo.
echo [4/6] Cleaning Project Binaries...
dotnet clean
if %errorlevel% neq 0 echo ⚠️ Clean failed (files might be locked by Revit).

:: 6. Project Build
echo.
echo [5/6] Building Revit Service (net48)...
dotnet build
if %errorlevel% neq 0 (
    echo ❌ ERROR: Build failed! Check C# code for syntax errors.
    pause
    exit /b 1
)
echo ✅ Build Successful!

:: 7. Launch Revit 2023
echo.
echo [6/6] Launching Revit 2023...
echo 🚨 ACTION REQUIRED: Click the LEFTMOST button "Always Load" when the popup appears.
start "" "C:\Program Files\Autodesk\Revit 2023\Revit.exe"

echo.
echo ============================================
echo 🚀 SETUP SEQUENCE COMPLETE
echo ============================================
pause