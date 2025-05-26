@echo off
python C:\Users\suudo\Desktop\temautomation.py
if %errorlevel% neq 0 (
    echo Python script encountered an error.
    pause
    exit /b %errorlevel%
)
start chrome "https://app.diagrams.net/"
pause
