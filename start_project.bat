@echo off
echo ========================================
echo   AI Gallery - Startup Script
echo ========================================
echo.

REM Проверка виртуального окружения
if exist "venv\Scripts\activate.bat" (
    echo [1/4] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment not found. Using system Python.
)

REM Сбор статических файлов
echo.
echo [2/4] Collecting static files...
python manage.py collectstatic --noinput --clear

REM Применение миграций
echo.
echo [3/4] Applying database migrations...
python manage.py migrate --noinput

REM Запуск сервера
echo.
echo [4/4] Starting development server...
echo.
echo ========================================
echo   Server will start at:
echo   http://localhost:8000/
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

python manage.py runserver

pause
