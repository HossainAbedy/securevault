@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo  SecureVault Installer Build
echo ============================================
echo.

set ROOT=%~dp0..
set INSTALLER=%~dp0
set VENV=%ROOT%\.venv\Scripts\python.exe
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if not exist "%VENV%" (
    echo ERROR: venv not found. Run: python -m venv .venv ^&^& pip install -r requirements.txt
    pause & exit /b 1
)
if not exist %ISCC% (
    echo ERROR: Inno Setup not found. Download: https://jrsoftware.org/isdl.php
    pause & exit /b 1
)
"%VENV%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller not installed. Run: pip install pyinstaller
    pause & exit /b 1
)

mkdir "%INSTALLER%dist"   2>nul
mkdir "%INSTALLER%output" 2>nul

echo [1/4] Building SecureVault.exe ...
cd /d "%ROOT%"
"%VENV%" -m PyInstaller installer\securevault.spec --distpath installer\dist --workpath installer\build --noconfirm
if errorlevel 1 ( echo ERROR: Main app build failed. & pause & exit /b 1 )

echo [2/4] Building native_host.exe ...
"%VENV%" -m PyInstaller installer\native_host.spec --distpath installer\dist --workpath installer\build --noconfirm
if errorlevel 1 ( echo ERROR: Native host build failed. & pause & exit /b 1 )

echo [3/5] Generating native host manifests...
"%VENV%" installer\build_manifests.py
if errorlevel 1 (
    echo ERROR: Native host manifest generation failed.
    pause
    exit /b 1
)

echo [4/5] Packaging Firefox .xpi ...
REM ======================================================
REM Firefox release build
REM The signed XPI downloaded from Mozilla AMO is already
REM located in installer\dist\securevault_firefox.xpi
REM Do NOT regenerate it here.
REM ======================================================

REM echo [4/5] Packaging Firefox .xpi ...
REM "%VENV%" installer\build_xpi.py
REM if errorlevel 1 (
REM     echo ERROR: XPI build failed.
REM     pause
REM     exit /b 1
REM )

echo [5/5] Running Inno Setup ...
cd /d "%INSTALLER%"
%ISCC% setup.iss
if errorlevel 1 ( echo ERROR: Inno Setup failed. & pause & exit /b 1 )

echo.
echo ============================================
echo  DONE: installer\output\SecureVaultSetup.exe
echo ============================================
start "" "%INSTALLER%output"
pause
