@echo off
echo ============================================
echo Building Revit API Service
echo ============================================

REM Check if dotnet is installed
dotnet --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: .NET SDK not found!
    echo Please install .NET 6.0 SDK from: https://dotnet.microsoft.com/download
    pause
    exit /b 1
)

REM Build the project
echo Building in Release mode...
dotnet build -c Release

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo Build completed successfully!
    echo ============================================
    echo.
    echo To run the service:
    echo   cd bin\Release\net6.0
    echo   RevitService.exe
    echo.
) else (
    echo.
    echo ============================================
    echo Build FAILED!
    echo ============================================
    pause
    exit /b 1
)

pause
