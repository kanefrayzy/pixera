@echo off
echo ========================================
echo AI Gallery - Запуск с Redis и Celery
echo ========================================
echo.

REM Проверка Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Docker не установлен или не запущен!
    echo Установите Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo [1/4] Запуск Redis через Docker...
docker-compose up -d redis
if errorlevel 1 (
    echo [ОШИБКА] Не удалось запустить Redis!
    pause
    exit /b 1
)

echo.
echo [2/4] Проверка Redis...
timeout /t 2 /nobreak >nul
docker exec ainude-redis-1 redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Redis не отвечает!
    pause
    exit /b 1
)
echo Redis работает! ✓

echo.
echo [3/4] Проверка .env файла...
if not exist .env (
    echo [ВНИМАНИЕ] Файл .env не найден!
    echo Создаю из .env.example...
    copy .env.example .env >nul
    echo.
    echo [ВАЖНО] Отредактируйте .env файл:
    echo - Установите RUNWARE_API_KEY
    echo - Проверьте другие настройки
    echo.
    pause
)

REM Проверка настроек Celery в .env
findstr /C:"USE_CELERY=True" .env >nul
if errorlevel 1 (
    echo [ВНИМАНИЕ] В .env не установлено USE_CELERY=True
    echo Убедитесь, что в .env есть:
    echo   USE_CELERY=True
    echo   CELERY_BROKER_URL=redis://localhost:6379/0
    echo   CELERY_RESULT_BACKEND=redis://localhost:6379/0
    echo.
)

echo.
echo [4/4] Готово к запуску!
echo.
echo ========================================
echo Следующие шаги:
echo ========================================
echo.
echo 1. Откройте НОВЫЙ терминал и запустите Celery worker:
echo    celery -A ai_gallery worker -l info -P solo
echo.
echo 2. В ЭТОМ терминале запустите Django:
echo    python manage.py runserver
echo.
echo 3. Откройте браузер: http://127.0.0.1:8000/generate/new
echo.
echo ========================================
echo Полезные команды:
echo ========================================
echo.
echo Остановить Redis:     docker-compose stop redis
echo Логи Redis:           docker-compose logs -f redis
echo Статус контейнеров:   docker-compose ps
echo.
echo ========================================
echo.

REM Спросить, запустить ли Django сразу
set /p START_DJANGO="Запустить Django сервер сейчас? (y/n): "
if /i "%START_DJANGO%"=="y" (
    echo.
    echo [ВНИМАНИЕ] Не забудьте запустить Celery worker в другом терминале!
    echo Запуск через 3 секунды...
    timeout /t 3 /nobreak >nul
    echo.
    python manage.py runserver
) else (
    echo.
    echo Запустите Django вручную: python manage.py runserver
    pause
)
