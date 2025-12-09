@echo off
echo ========================================
echo Celery Worker для AI Gallery
echo ========================================
echo.

REM Проверка, что Redis запущен
docker exec ainude-redis-1 redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Redis не запущен!
    echo.
    echo Запустите Redis сначала:
    echo   docker-compose up -d redis
    echo.
    echo Или используйте: start_with_redis.bat
    echo.
    pause
    exit /b 1
)

echo Redis подключен ✓
echo.
echo Запуск Celery worker...
echo.
echo ========================================
echo Нажмите Ctrl+C для остановки worker
echo ========================================
echo.

celery -A ai_gallery worker -l info -P solo
