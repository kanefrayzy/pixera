# AI Gallery - AI Image Generation Platform

Django-based web application for AI image generation using Runware API.

## Features

- 🎨 AI Image generation via Runware
- 🖼️ Public gallery with likes/comments
- 💰 Token-based wallet system
- 🌍 Multi-language support (EN, ES, PT, DE, RU)
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