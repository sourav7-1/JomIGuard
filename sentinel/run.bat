@echo off
REM Starts the Sentinel Tree Monitor on http://127.0.0.1:5060
cd /d "%~dp0"
start "" http://127.0.0.1:5060
python app.py
