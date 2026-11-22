@echo off
title FB Auto Bot - Windows EXE & Setup Builder
echo ======================================================================
echo       FB Auto Bot - Windows EXE, Admin KeyGen & Setup Builder
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/4] Checking and installing Python dependencies from requirements.txt...
python -m pip install -q -r requirements.txt
python -m pip install -q pyinstaller

echo.
echo [2/4] Ensuring Playwright Chromium runtime is installed...
python -m playwright install chromium

echo.
echo [3/4] Building FBAutoBot.exe, FBAutoBot_AdminKeyGen.exe, Portable ZIP & Setup EXE...
python build_installer.py %*

echo.
echo ======================================================================
echo Build finished! Check 'desktop_app\dist_installer\' for:
echo   1. FBAutoBot_Setup_v5.0.exe            (Customer Windows Setup Wizard)
echo   2. FBAutoBot_v5.0_Windows_Portable.zip (Customer Portable ZIP)
echo   3. FBAutoBot_AdminKeyGen.exe           (Admin-Only License Generator)
echo ======================================================================
pause
