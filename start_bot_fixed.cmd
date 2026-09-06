@echo off
cd /d "%~dp0"
set "NO_PROXY=localhost,127.0.0.1"
set "no_proxy=localhost,127.0.0.1"
set "OLLAMA_URL=http://127.0.0.1:11434"
echo Starting pantry bot with local Ollama proxy bypass...
".venv\Scripts\python.exe" run_ollama.py
echo.
echo The bot has stopped. See the error above.
pause
