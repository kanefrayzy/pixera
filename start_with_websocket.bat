@echo off
echo ============================================================
echo   Starting AI Gallery with WebSocket Support (Daphne)
echo ============================================================
echo.
echo Stopping any running servers on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do taskkill /F /PID %%a 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Starting Daphne ASGI server...
echo Server will be available at: http://127.0.0.1:8000
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

daphne -b 127.0.0.1 -p 8000 ai_gallery.asgi:application
