"""
Скрипт для обновления существующих уведомлений о лайках job
Меняет текст с "понравилась ваша генерация" на "понравилось ваше фото/видео"
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from dashboard.models import Notification
from generate.models import GenerationJob

def update_job_notifications():
    # Получаем все уведомления типа LIKE_JOB
    notifications = Notification.objects.filter(type=Notification.Type.LIKE_JOB)

    updated_count = 0
    for notif in notifications:
        payload = notif.payload or {}
        job_id = payload.get("job_id")

        if not job_id:
            continue

        try:
            job = GenerationJob.objects.get(id=job_id)
            gen_type = getattr(job, "generation_type", "image")

            # Обновляем текст сообщения
            username = notif.actor.username if notif.actor else "Пользователь"
            if gen_type == "video":
                new_message = f"@{username} понравилось ваше видео"
            else:
                new_message = f"@{username} понравилось ваше фото"

            # Обновляем payload
            payload["generation_type"] = gen_type

            # Сохраняем изменения
            notif.message = new_message
            notif.payload = payload
            notif.save(update_fields=["message", "payload"])

            updated_count += 1
            print(f"✅ Обновлено уведомление #{notif.id}: {new_message}")

        except GenerationJob.DoesNotExist:
            print(f"⚠️  Job #{job_id} не найден для уведомления #{notif.id}")
            continue
        except Exception as e:
            print(f"❌ Ошибка при обновлении уведомления #{notif.id}: {e}")
            continue

    print(f"\n✅ Обновлено {updated_count} уведомлений")

if __name__ == "__main__":
    print("🚀 Начинаем обновление уведомлений...")
    update_job_notifications()
    print("✅ Готово!")
