
:: 2. Ubuntu Host Mapping Instruction (Reminder)
echo.
echo [1/7] NETWORK CONFIGURATION:
echo Run this on your UBUNTU machine (not here) to map the hostname:
echo echo "191.168.124.64 LT-HQ-277" ^| sudo tee -a /etc/hosts
echo --------------------------------------------

:: 3. Port Check
echo.
echo [2/7] Checking Port 49152 Status...
netstat -ano | findstr LISTENING | findstr :49152
if %errorlevel% neq 0 echo ⚠️ Port is currently free (No active Revit session).

:: 4. TCP Connection Test
echo.
echo [3/7] Running Local TCP Handshake Test...
powershell -Command "Test-NetConnection -ComputerName localhost -Port 49152"

:: 5. Project Clean
echo.
echo [4/7] Cleaning Project Binaries...
dotnet clean
if %errorlevel% neq 0 echo ⚠️ Clean failed (files might be locked by Revit).

:: 6. Project Build
echo.
echo [5/7] Building Revit Service (net48)...
dotnet build
if %errorlevel% neq 0 (
    echo ❌ ERROR: Build failed! Check C# code for syntax errors.
@@ -43,10 +43,15 @@ if %errorlevel% neq 0 (
)
echo ✅ Build Successful!


:: 7. Registry Bypass (This "clicks" the button for you permanently)
echo [6/7] Registering Trusted DLL...
set "DLL_PATH=%CD%\bin\Debug\net48\RevitService.dll"
reg add "HKEY_CURRENT_USER\Software\Autodesk\Revit\Autodesk Revit 2023\CodeSigning" /v "%DLL_PATH%" /t REG_DWORD /d 1 /f

:: 8. Launch Revit 2023
echo.
echo [7/7] Launching Revit 2023...

start "" "C:\Program Files\Autodesk\Revit 2023\Revit.exe"

echo.