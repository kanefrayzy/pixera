# 🚀 Чеклист запуска Pixera на сервере

## Перед загрузкой на сервер

### 1. Локальная подготовка

- [ ] Собран Tailwind CSS: `npm run build:css`
- [ ] Проверена работоспособность локально
- [ ] Все миграции созданы: `python manage.py makemigrations`
- [ ] Нет незакоммиченных файлов в `.gitignore`
- [ ] Обновлен `requirements.txt` (уже включает mysqlclient, gunicorn)

### 2. Файлы для редактирования на сервере

После загрузки на сервер отредактируйте `.env`:

```bash
cp .env.production .env
nano .env
```

**Обязательные изменения:**

```env
# Генерируем secret key (на сервере):
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

DJANGO_SECRET_KEY=<вставьте_сгенерированный_ключ>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

MYSQL_PASSWORD=<сильный_пароль>
MYSQL_ROOT_PASSWORD=<еще_более_сильный_пароль>

EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<app_password_из_gmail>
```

---

## На сервере

### 1. Установка Docker (если не установлен)

```bash
# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перелогиниваемся для применения прав
exit
# (заходим снова)
```

### 2. Загрузка проекта

```bash
# Клонируем репозиторий или загружаем архив
git clone https://github.com/yourusername/pixera.git
cd pixera

# ИЛИ загружаем через scp/rsync:
# scp -r ./pixera user@server:/home/user/
```

### 3. Настройка .env

```bash
cp .env.production .env
nano .env
# Редактируем все параметры выше
```

### 4. Даём права на docker-entrypoint.sh

```bash
chmod +x docker-entrypoint.sh
```

### 5. Запуск

```bash
# Собираем и запускаем все сервисы
docker-compose up -d --build

# Проверяем логи
docker-compose logs -f web

# Ждём пока MySQL инициализируется и миграции применятся
# В логах должно появиться: "Starting application..."
```

### 6. Проверка

```bash
# Проверяем статус всех контейнеров
docker-compose ps

# Все должны быть "Up" (может занять 30-60 сек для MySQL)

# Проверяем health check
curl http://localhost:8000/health/
# Ответ: {"status":"healthy",...}
```

### 7. Создание суперюзера (если не создан автоматически)

```bash
docker-compose exec web python manage.py createsuperuser
```

### 8. Проверка админки

Открываем: `http://your-server-ip:8000/admin`

Логин по умолчанию (если создан автоматически):
- Username: `admin`
- Password: `changeme123`

⚠️ **СРАЗУ ИЗМЕНИТЕ ПАРОЛЬ!**

---

## Настройка домена и HTTPS

### 1. DNS

Добавьте A-запись в DNS:
```
A    @              123.45.67.89
A    www            123.45.67.89
```

### 2. Nginx + SSL (рекомендуется)

Раскомментируйте секцию `nginx` в `docker-compose.yml`:

```yaml
nginx:
  image: nginx:alpine
  container_name: pixera_nginx
  restart: unless-stopped
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/conf.d:/etc/nginx/conf.d:ro
    - static_volume:/app/staticfiles:ro
    - media_volume:/app/media:ro
    - ./certbot/conf:/etc/letsencrypt:ro
    - ./certbot/www:/var/www/certbot:ro
  depends_on:
    - web
```

### 3. Создайте конфиг Nginx

```bash
mkdir -p nginx/conf.d
nano nginx/conf.d/pixera.conf
```

```nginx
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

### 4. SSL через Certbot

```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Автообновление
sudo certbot renew --dry-run
```

---

## Полезные команды

```bash
# Перезапуск после изменений
docker-compose restart web

# Обновление после git pull
git pull
docker-compose down
docker-compose up -d --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput

# Логи
docker-compose logs -f web         # Django
docker-compose logs -f celery      # Celery worker
docker-compose logs -f db          # MySQL

# Backup БД
docker-compose exec db mysqldump -u root -p pixera > backup_$(date +%Y%m%d).sql

# Вход в контейнер
docker-compose exec web bash
docker-compose exec db mysql -u root -p

# Остановка всех сервисов
docker-compose down

# Полная очистка (ОСТОРОЖНО! Удалит данные)
docker-compose down -v
```

---

## Проверка после запуска

- [ ] Сайт открывается: `http://your-domain.com`
- [ ] Health check работает: `http://your-domain.com/health/`
- [ ] Админка доступна: `http://your-domain.com/admin`
- [ ] Регистрация работает
- [ ] Генерация изображений работает (требует RUNWARE_API_KEY)
- [ ] Статика загружается (CSS, JS, images)
- [ ] Медиа загружается (uploaded images)
- [ ] Email отправляются (если настроен SMTP)
- [ ] Celery обрабатывает задачи (проверьте логи)

---

## Мониторинг

### Основные метрики

```bash
# Использование ресурсов
docker stats

# Размер volumes
docker system df -v

# Логи за последний час
docker-compose logs --since 1h
```

### Рекомендации для production

- [ ] Настроить Sentry для отслеживания ошибок
- [ ] Настроить регулярные бэкапы БД (cron)
- [ ] Настроить мониторинг (Prometheus + Grafana)
- [ ] Настроить S3/CDN для media файлов
- [ ] Настроить firewall (ufw)
- [ ] Настроить fail2ban для защиты SSH

---

## Troubleshooting

### "Connection refused" при обращении к БД
```bash
# Проверьте что MySQL запустился
docker-compose logs db | grep "ready for connections"
# Перезапустите web
docker-compose restart web
```

### Celery не обрабатывает задачи
```bash
# Проверьте Redis
docker-compose exec redis redis-cli ping
# Должно ответить: PONG

# Проверьте настройки в .env
grep CELERY .env
```

### Статика не загружается
```bash
docker-compose exec web python manage.py collectstatic --noinput
docker-compose restart web
```

### 502 Bad Gateway (если используется Nginx)
```bash
# Проверьте логи Nginx
docker-compose logs nginx

# Проверьте что web контейнер запущен
docker-compose ps web
```

---

## Поддержка

Если возникли проблемы:
1. Проверьте логи: `docker-compose logs -f`
2. Создайте issue в репозитории
3. Свяжитесь через Telegram: @your_support

---

**Готово! Pixera запущена и готова к работе! 🎉**
