@echo off
echo Starting Amplify AI Backend...

cd /d "%~dp0..\backend"
call venv\Scripts\activate

echo Starting FastAPI Server...
python app.py
