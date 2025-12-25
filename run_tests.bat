@echo off
echo ============================================================
echo Testing Junior API Endpoints
echo ============================================================
echo.
echo Please ensure Junior is running in another terminal:
echo   python start.py
echo.
echo Press any key to start testing...
pause >nul
echo.

python tests\test_quick_api.py

echo.
echo ============================================================
echo Testing Complete!
echo ============================================================
pause
