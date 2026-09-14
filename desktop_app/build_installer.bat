@echo off
title FB Auto Bot - Setup Builder
echo ======================================================================
echo           FB Auto Bot - Windows Setup Installer Builder
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking dependencies...
python -m pip install -q playwright playwright-stealth PyQt5 Pillow google-genai
python -m playwright install chromium

echo.
echo [2/3] Running Installer Builder...
python build_installer.py

echo.
echo ======================================================================
echo Process finished. Check 'desktop_app\dist_installer' for FBAutoBot_Setup_v5.0.exe!
echo ======================================================================
pause
