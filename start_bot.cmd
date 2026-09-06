@echo off
cd /d "%~dp0"
echo Starting pantry bot...
".venv\Scripts\python.exe" run_ollama.py
echo.
echo The bot has stopped. See the error above.
pause
