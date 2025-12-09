# 🚀 PIXERA - Production Deployment Guide

## Быстрый старт на сервере

### 1. Подготовка сервера

```bash
# Установка Docker и Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Клонирование и настройка

```bash
# Клонируем репозиторий
git clone https://github.com/yourusername/pixera.git
cd pixera

# Копируем и настраиваем .env
cp .env.production .env
nano .env  # Редактируем параметры
```

### 3. Важные настройки в .env

**Обязательно измените:**
- `DJANGO_SECRET_KEY` - генерируйте через: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- `DJANGO_ALLOWED_HOSTS` - ваш домен (без https://)
- `CSRF_TRUSTED_ORIGINS` - ваш домен (с https://)
- `MYSQL_PASSWORD` и `MYSQL_ROOT_PASSWORD` - надежные пароли
- `EMAIL_HOST_USER` и `EMAIL_HOST_PASSWORD` - данные SMTP

**Опционально (для полного функционала):**
- Google/Facebook/Discord OAuth credentials
- Runware/Replicate/Runway API keys
- Stripe keys для оплаты

### 4. Запуск

```bash
# Собираем и запускаем контейнеры
docker-compose up -d --build

# Проверяем логи
docker-compose logs -f web

# Проверяем статус
docker-compose ps
```

### 5. Первоначальная настройка

```bash
# Создаём суперюзера (если не создан автоматически)
docker-compose exec web python manage.py createsuperuser

# Собираем статику
docker-compose exec web python manage.py collectstatic --noinput

# Применяем миграции
docker-compose exec web python manage.py migrate
```

### 6. Доступ

- **Сайт:** http://your-server-ip:8000
- **Админка:** http://your-server-ip:8000/admin

Логин по умолчанию (если создан автоматически):
- Username: `admin`
- Password: `changeme123`

⚠️ **Сразу измените пароль через админку!**

---

## Архитектура

```
pixera/
├── web          - Django (8000) - WSGI приложение
├── celery       - Celery Worker - фоновые задачи
├── celery-beat  - Планировщик задач
├── db           - MySQL 8.0 (3306)
├── redis        - Redis (6379) - очереди и кеш
└── nginx        - (опционально) Reverse proxy
```

---

## Production чеклист

### Безопасность
- ✅ Изменён `DJANGO_SECRET_KEY`
- ✅ `DJANGO_DEBUG=False`
- ✅ Настроены `ALLOWED_HOSTS` и `CSRF_TRUSTED_ORIGINS`
- ✅ Включены HTTPS redirects (`SECURE_SSL_REDIRECT=True`)
- ✅ Secure cookies enabled
- ✅ Изменены пароли MySQL
- ✅ Изменён пароль admin-пользователя

### База данных
- ✅ MySQL вместо SQLite
- ✅ Автоматические бэкапы настроены
- ✅ CONN_MAX_AGE установлен для пула соединений

### Статика и медиа
- ⚠️ Рекомендуется настроить S3/CDN для production
- ✅ WhiteNoise для статики
- ✅ Volume для media файлов

### Мониторинг
- 📊 Добавьте Sentry для ошибок
- 📊 Настройте логирование в файлы
- 📊 Health check endpoint: `/health/`

---

## Команды Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Остановка
docker-compose down

# Пересборка после изменений
docker-compose up -d --build

# Логи конкретного сервиса
docker-compose logs -f web
docker-compose logs -f celery

# Выполнение команд Django
docker-compose exec web python manage.py shell
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# Вход в контейнер
docker-compose exec web bash

# Перезапуск сервиса
docker-compose restart web

# Статус сервисов
docker-compose ps
```

---

## Обновление на сервере

```bash
# Пулл изменений
git pull origin main

# Пересборка и перезапуск
docker-compose down
docker-compose up -d --build

# Миграции
docker-compose exec web python manage.py migrate

# Статика
docker-compose exec web python manage.py collectstatic --noinput
```

---

## Backup базы данных

```bash
# Создание бэкапа
docker-compose exec db mysqldump -u root -p pixera > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление
docker-compose exec -T db mysql -u root -p pixera < backup_20250109_120000.sql
```

---

## Nginx (опционально для production)

Раскомментируйте секцию `nginx` в `docker-compose.yml` и создайте конфиг:

```nginx
# nginx/conf.d/pixera.conf
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    client_max_body_size 100M;

    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /app/staticfiles/;
    }

    location /media/ {
        alias /app/media/;
    }
}
```

---

## Troubleshooting

### Не запускается web
```bash
docker-compose logs web
# Проверьте .env, особенно DJANGO_SECRET_KEY и DB credentials
```

### Ошибка подключения к MySQL
```bash
docker-compose logs db
# Подождите пока MySQL полностью запустится (healthcheck)
docker-compose restart web
```

### Celery не обрабатывает задачи
```bash
docker-compose logs celery
# Проверьте REDIS_URL и CELERY_BROKER_URL в .env
```

### Статика не загружается
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

---

## Контакты

Если возникли проблемы при деплое, создайте issue в репозитории.
