@echo off
REM Paint Formulation AI - uygulamayi konsol penceresi olmadan baslatir
cd /d "%~dp0.."
if not exist venv\Scripts\pythonw.exe (
    echo Once scripts\setup_windows.bat dosyasini calistirin.
    pause
    exit /b 1
)
start "" venv\Scripts\pythonw.exe app\main.py
