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

:: 3. Project Clean
echo.
echo [2/6] Cleaning Project Binaries...
dotnet clean
if %errorlevel% neq 0 echo ⚠️ Clean failed (files might be locked by Revit).

:: 4. Project Build
echo.
echo [3/6] Building Revit Service (net48)...
dotnet build
if %errorlevel% neq 0 (
    echo ❌ ERROR: Build failed! Check C# code for syntax errors.
    pause
    exit /b
)
echo ✅ Build Successful!

:: 5. Deploy Addin Manifest (This replaces registry bypass)
echo.
echo [4/6] Deploying Addin Manifest...
set "ADDIN_DIR=C:\ProgramData\Autodesk\Revit\Addins\2023"
set "ADDIN_FILE=%CD%\RevitService.addin"

:: Create directory if it doesn't exist
if not exist "%ADDIN_DIR%" (
    mkdir "%ADDIN_DIR%"
    echo 📁 Created Addins directory
)

:: Copy the .addin manifest file
if exist "%ADDIN_FILE%" (
    copy /Y "%ADDIN_FILE%" "%ADDIN_DIR%\RevitService.addin"
    if %errorlevel% equ 0 (
        echo ✅ Manifest deployed to %ADDIN_DIR%
    ) else (
        echo ❌ Failed to copy manifest file. Check permissions.
        pause
        exit /b
    )
) else (
    echo ❌ ERROR: RevitService.addin not found in %CD%
    echo Please ensure the .addin file exists in the project directory.
    pause
    exit /b
)

:: 6. Launch Revit 2023
echo.
echo [5/6] Launching Revit 2023...
start "" "C:\Program Files\Autodesk\Revit 2023\Revit.exe"

echo.
echo [6/6] Waiting for TCP Service to Initialize...
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

:: 7. TCP Connection Test
echo.
echo ✅ Port is LISTENING! Running final TCP Handshake...
powershell -Command "Test-NetConnection -ComputerName localhost -Port 49152"

:END
echo.
echo ============================================
echo 🚀 SETUP SEQUENCE COMPLETE
echo ============================================
echo.
echo 💡 TIPS:
echo - If Revit still prompts for trust, check the .addin file path
echo - Ensure the Assembly path in .addin matches: %CD%\bin\Debug\net48\RevitService.dll
echo - The addin should auto-load without prompts now
echo ============================================
pause