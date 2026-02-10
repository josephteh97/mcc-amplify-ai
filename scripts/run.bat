@echo off
setlocal
echo ============================================
echo 🛠️  REVIT BRIDGE INITIALIZATION
echo ============================================

:: 1. Kill any running Revit processes
echo.
echo [1/7] Closing any running Revit instances...
taskkill /F /IM Revit.exe 2>nul
if %errorlevel% equ 0 (
    echo ✅ Revit closed
    timeout /t 2 /nobreak >nul
) else (
    echo ℹ️  No Revit instance running
)

:: 2. Navigation
cd /d "C:\MyDocuments\mcc-amplify-ai\revit_server\csharp_service"
echo 📂 Working Directory: %CD%

:: 3. Ubuntu Host Mapping Instruction
echo.
echo [2/7] NETWORK CONFIGURATION:
echo Run this on your UBUNTU machine (not here) to map the hostname:
echo echo "191.168.124.64 LT-HQ-277" ^| sudo tee -a /etc/hosts
echo --------------------------------------------

:: 4. Project Clean
echo.
echo [3/7] Cleaning Project Binaries...
dotnet clean
if %errorlevel% neq 0 echo ⚠️ Clean failed.

:: 5. Project Build
echo.
echo [4/7] Building Revit Service (net48)...
dotnet build
if %errorlevel% neq 0 (
    echo ❌ ERROR: Build failed! Check C# code for syntax errors.
    pause
    exit /b
)
echo ✅ Build Successful!

:: 6. Deploy Addin Manifest
echo.
echo [5/7] Deploying Addin Manifest...
set "ADDIN_SOURCE=C:\Program Files\Autodesk\Revit 2023\RevitService.addin"
set "ADDIN_DIR=C:\ProgramData\Autodesk\Revit\Addins\2023"

if not exist "%ADDIN_DIR%" mkdir "%ADDIN_DIR%"

if exist "%ADDIN_SOURCE%" (
    copy /Y "%ADDIN_SOURCE%" "%ADDIN_DIR%\RevitService.addin"
    echo ✅ Manifest deployed to %ADDIN_DIR%
) else (
    echo ⚠️ Addin file not found, continuing anyway...
)

:: 7. Launch Revit 2023
echo.
echo [6/7] Launching Revit 2023...
start "" "C:\Program Files\Autodesk\Revit 2023\Revit.exe"

echo.
echo [7/7] Waiting for TCP Service to Initialize...
set /a retry_count=0

:CHECK_PORT
timeout /t 20 /nobreak > nul
set /a retry_count+=1

echo.
echo [Attempt %retry_count%/6] Checking Port 49152 Status...
netstat -ano | findstr LISTENING | findstr :49152 >nul

if %errorlevel% neq 0 (
    if %retry_count% lss 6 (
        echo ⏳ Port not active yet. Retrying in 20s...
        goto CHECK_PORT
    ) else (
        echo ❌ TIMEOUT: Revit took too long to open the port.
        echo ℹ️  Check if the addin loaded correctly in Revit.
        goto END
    )
)

:: 8. TCP Connection Test
echo.
echo ✅ Port is LISTENING! Running final TCP Handshake...
powershell -Command "Test-NetConnection -ComputerName localhost -Port 49152"

:END
echo.
echo ============================================
echo 🚀 SETUP SEQUENCE COMPLETE
echo ============================================
echo.
echo 💡 NOTE: You may need to click "Always Load" once in Revit
echo ============================================
pause