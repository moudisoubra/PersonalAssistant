@echo off
title Bob Personal Assistant
color 0A

:: Switch to the directory where this script is located
cd /d "%~dp0"

echo ==========================================
echo       STARTING BOB PERSONAL ASSISTANT
echo ==========================================
echo.
echo Loading virtual environment...
call .venv\Scripts\activate.bat

echo.
python main.py

echo.
pause
