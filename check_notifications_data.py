"""
Проверка данных уведомлений
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from dashboard.models import Notification
from generate.models import GenerationJob

# Получаем последние 5 уведомлений типа LIKE_JOB
notifications = Notification.objects.filter(type=Notification.Type.LIKE_JOB).order_by('-created_at')[:5]

print("=" * 80)
print("ПРОВЕРКА УВЕДОМЛЕНИЙ О ЛАЙКАХ ГЕНЕРАЦИЙ")
print("=" * 80)

for notif in notifications:
    print(f"\n📧 Уведомление #{notif.id}")
    print(f"   Сообщение: {notif.message}")
    print(f"   Payload: {json.dumps(notif.payload, indent=2, ensure_ascii=False)}")

    job_id = notif.payload.get("job_id")
    if job_id:
        try:
            job = GenerationJob.objects.get(id=job_id)
            print(f"\n   📦 Job #{job.id}:")
            print(f"      generation_type: {job.generation_type}")
            print(f"      result_video_url: {job.result_video_url or '(пусто)'}")
            print(f"      result_image: {job.result_image.name if job.result_image else '(пусто)'}")
            print(f"      persisted: {job.persisted}")
        except GenerationJob.DoesNotExist:
            print(f"   ❌ Job #{job_id} не найден")

    print("-" * 80)

