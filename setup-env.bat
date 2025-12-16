@echo off
REM Setup script for glb-model-rotate UV environment (Windows)

echo Setting up glb-model-rotate Python environment with UV...

REM Check if UV is installed
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo UV is not installed. Installing UV...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo Please restart your command prompt after installation
    exit /b 1
)

echo UV version:
uv --version

REM Create virtual environment
echo Creating virtual environment...
uv venv

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
uv pip install trimesh pymeshlab numpy

echo.
echo Setup complete!
echo.
echo To activate the environment in the future, run:
echo   .venv\Scripts\activate.bat
echo.
echo To install development dependencies, run:
echo   uv pip install pytest black ruff
echo.
echo Python scripts are ready to use!
echo.
