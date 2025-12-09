"""
Проверка превью в уведомлениях
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from dashboard.models import Notification
from generate.models import GenerationJob
from gallery.models import PublicVideo

# Получаем последние уведомления о лайках видео
notifications = Notification.objects.filter(type__in=['like_video', 'like_job']).order_by('-created_at')[:5]

print("=" * 80)
print("ПРОВЕРКА ПРЕВЬЮ В УВЕДОМЛЕНИЯХ")
print("=" * 80)

for notif in notifications:
    print(f"\n📧 Уведомление #{notif.id}")
    print(f"   Тип: {notif.type}")
    print(f"   Сообщение: {notif.message}")
    print(f"   Payload: {json.dumps(notif.payload, indent=2, ensure_ascii=False)}")

    if notif.type == 'like_video':
        video_id = notif.payload.get("video_id")
        if video_id:
            try:
                video = PublicVideo.objects.get(id=video_id)
                print(f"\n   📹 PublicVideo #{video.id}:")
                print(f"      video_url: {video.video_url or '(пусто)'}")
                print(f"      thumbnail: {video.thumbnail.name if video.thumbnail else '(пусто)'}")
                if video.thumbnail:
                    print(f"      thumbnail.url: {video.thumbnail.url}")
            except PublicVideo.DoesNotExist:
                print(f"   ❌ Video #{video_id} не найден")

    elif notif.type == 'like_job':
        job_id = notif.payload.get("job_id")
        gen_type = notif.payload.get("generation_type", "image")
        if job_id:
            try:
                job = GenerationJob.objects.get(id=job_id)
                print(f"\n   📦 Job #{job.id}:")
                print(f"      generation_type: {job.generation_type}")
                print(f"      result_video_url: {job.result_video_url or '(пусто)'}")
                print(f"      result_image: {job.result_image.name if job.result_image else '(пусто)'}")
                if job.result_image:
                    print(f"      result_image.url: {job.result_image.url}")
            except GenerationJob.DoesNotExist:
                print(f"   ❌ Job #{job_id} не найден")

    print("-" * 80)

print("\n✅ Проверка завершена")
