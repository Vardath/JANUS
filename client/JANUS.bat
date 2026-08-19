@echo off
setlocal
cd /d "%~dp0"
title JANUS - Global 7-3-1

if exist "JANUS.exe" (
    start "" "JANUS.exe"
    exit /b 0
)

echo ============================================
echo        JANUS Global 7-3-1 Launcher
echo ============================================
echo.
echo JANUS.exe was not found in this folder.
echo Keep JANUS.bat and JANUS.exe together, then run this launcher again.
echo.
pause
