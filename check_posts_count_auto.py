#!/usr/bin/env python
"""
Скрипт для проверки количества публикаций пользователя (автоматический)
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from django.contrib.auth import get_user_model
from gallery.models import PublicPhoto, PublicVideo
from generate.models import GenerationJob
from dashboard.models import Profile

User = get_user_model()

# Берем username из аргументов или используем Stas по умолчанию
username = sys.argv[1] if len(sys.argv) > 1 else "Stas"

user = User.objects.filter(username=username).first()
if not user:
    print(f"❌ Пользователь '{username}' не найден")
    sys.exit(1)

print(f"\n{'='*60}")
print(f"Проверка публикаций для пользователя: {user.username}")
print(f"{'='*60}\n")

# Подсчитываем фото
photos_active = PublicPhoto.objects.filter(uploaded_by=user, is_active=True).count()
photos_inactive = PublicPhoto.objects.filter(uploaded_by=user, is_active=False).count()
photos_total = PublicPhoto.objects.filter(uploaded_by=user).count()

print(f"📷 ФОТО:")
print(f"  • Активные (опубликованные): {photos_active}")
print(f"  • Неактивные (на модерации):  {photos_inactive}")
print(f"  • Всего:                      {photos_total}")

# Подсчитываем видео
videos_active = PublicVideo.objects.filter(uploaded_by=user, is_active=True).count()
videos_inactive = PublicVideo.objects.filter(uploaded_by=user, is_active=False).count()
videos_total = PublicVideo.objects.filter(uploaded_by=user).count()

print(f"\n🎥 ВИДЕО:")
print(f"  • Активные (опубликованные): {videos_active}")
print(f"  • Неактивные (на модерации):  {videos_inactive}")
print(f"  • Всего:                      {videos_total}")

# Итоговый счетчик
total_publications = photos_active + videos_active

print(f"\n{'='*60}")
print(f"📊 ИТОГО ПУБЛИКАЦИЙ (активных): {total_publications}")
print(f"{'='*60}\n")

# Дополнительная информация
done_jobs = GenerationJob.objects.filter(user=user, status=GenerationJob.Status.DONE).count()
print(f"ℹ️  Дополнительная информация:")
print(f"  • Завершенных работ (GenerationJob): {done_jobs}")

# Проверка is_private
try:
    profile = Profile.objects.get(user=user)
    privacy_status = "Закрытый" if profile.is_private else "Открытый"
    print(f"  • Тип аккаунта: {privacy_status}")
except Profile.DoesNotExist:
    print(f"  • Профиль не создан")

print(f"\n✅ Ожидаемое значение счетчика 'Публикации': {total_publications}")
