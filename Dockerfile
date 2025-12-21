# Dockerfile для Pixera
FROM python:3.11-slim

# Отключаем буферизацию для логов
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    pkg-config \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаём директории для статики и медиа
RUN mkdir -p /app/staticfiles /app/media

# Собираем статику (collectstatic выполнится при запуске)
# RUN python manage.py collectstatic --noinput

# Expose порт
EXPOSE 8000

# Entrypoint скрипт
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "ai_gallery.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
