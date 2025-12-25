@echo off
title Junior - AI Legal Assistant
color 0A
cls

echo ============================================================
echo    JUNIOR - AI Legal Assistant
echo ============================================================
echo.
echo Starting application...
echo.

if exist ".venv\Scripts\python.exe" (
	echo Using virtual environment: .venv\Scripts\python.exe
	".venv\Scripts\python.exe" start.py
) else (
	echo WARNING: .venv not found, falling back to system Python
	python start.py
)

pause
