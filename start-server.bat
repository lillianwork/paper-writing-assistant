@echo off
cd /d "%~dp0"
start http://localhost:8765/academic-writing-hub.html
python -m http.server 8765
