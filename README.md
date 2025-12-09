# 🎨 Pixera - AI Image & Video Generation Platform

Современная платформа для генерации и публикации изображений и видео с помощью искусственного интеллекта.

## ✨ Возможности

- 🖼️ **Генерация изображений** - Flux, SDXL, Stable Diffusion
- 🎬 **Генерация видео** - Runway Gen3, Kling, Luma AI
- 🎨 **Галерея** - публикация и поиск работ
- 👤 **Профили** - подписки, лайки, комментарии
- 💰 **Токены** - система оплаты генераций
- 🌐 **Мультиязычность** - EN, ES, PT, DE, RU
- 🌙 **Темы** - тёмная/светлая
- 📱 **Адаптивный дизайн** - мобильные и десктоп

## 🚀 Быстрый старт (Development)

### Требования

- Python 3.11+
- Node.js 18+ (для сборки Tailwind CSS)
- Redis (опционально, для Celery)

### Установка

```bash
# 1. Клонируем репозиторий
git clone https://github.com/yourusername/pixera.git
cd pixera

# 2. Создаём виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 3. Устанавливаем зависимости
pip install -r requirements.txt

# 4. Устанавливаем Node зависимости (Tailwind CSS)
npm install

# 5. Собираем Tailwind CSS
npm run build:css

# 6. Копируем .env
cp .env.example .env
# Отредактируйте .env - минимум нужен DJANGO_SECRET_KEY

# 7. Миграции
python manage.py migrate

# 8. Создаём суперюзера
python manage.py createsuperuser

# 9. Собираем статику
python manage.py collectstatic --noinput

# 10. Запускаем сервер
python manage.py runserver
```

Сайт доступен: http://127.0.0.1:8000

## 🐳 Production (Docker)

Полная инструкция по деплою: [DEPLOYMENT.md](DEPLOYMENT.md)

### Быстрый деплой

```bash
# 1. Копируем и настраиваем .env
cp .env.production .env
nano .env  # редактируем

# 2. Запускаем
docker-compose up -d --build

# 3. Проверяем
docker-compose ps
docker-compose logs -f web
```

Сайт доступен: http://your-server:8000

## 📁 Структура проекта

```
pixera/
├── ai_gallery/          # Основные настройки Django
├── dashboard/           # Профиль, баланс, уведомления
├── gallery/             # Галерея изображений и видео
├── generate/            # Генерация (API интеграции)
├── blog/                # Блог
├── pages/               # Статические страницы
├── moderation/          # Модерация контента
├── templates/           # HTML шаблоны
├── static/              # Статика
│   └── css/
│       ├── tailwind.input.css   # Исходник Tailwind
│       └── tailwind.min.css     # Собранный (95KB)
├── media/               # Загружаемые файлы
├── Dockerfile           # Docker image
├── docker-compose.yml   # Docker services
└── tailwind.config.js   # Tailwind конфигурация
```

## 🛠️ Технологии

- **Django 5.2** + **MySQL 8.0** + **Redis**
- **Tailwind CSS 3.4** (локальный билд 95KB вместо 3.5MB CDN)
- **Celery** - фоновые задачи
- **Gunicorn** - WSGI сервер
- **Docker** - контейнеризация

## 📝 Разработка

### Сборка Tailwind CSS

```bash
npm run watch:css    # Development (watch mode)
npm run build:css    # Production (minified)
```

### Миграции

```bash
python manage.py makemigrations
python manage.py migrate
```

## 📜 Документация

- [DEPLOYMENT.md](DEPLOYMENT.md) - Подробная инструкция по деплою на сервер

---

**Pixera** © 2025 - Генерация изображений и видео с помощью ИИ
- 🔐 Authentication (email + Google OAuth)
- 🛡️ Anti-abuse protection with device fingerprinting
- 📝 Blog system
- 👥 User dashboard

## Tech Stack

- **Backend**: Django 4.x, Python 3.10+
- **Database**: SQLite (dev) / MySQL (prod)
- **Task Queue**: Celery (optional)
- **API**: Django REST Framework
- **Auth**: django-allauth
- **Frontend**: HTML, CSS, JavaScript

## Installation

### 1. Clone repository
```bash
git clone https://github.com/yourusername/ai-gallery.git
cd ai-gallery
