"""
Скрипт для обновления URL в существующих уведомлениях.
Изменяет старые URL вида /gallery/12 на новый формат /generate/photo/slug-ID
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from dashboard.models import Notification
from gallery.models import PublicPhoto, PublicVideo
from django.db.models import Q


def fix_notification_urls():
    """Обновляет URL в уведомлениях о лайках фото и видео"""
    
    # Находим уведомления с лайками на фото
    photo_notifications = Notification.objects.filter(
        Q(type=Notification.Type.LIKE_PHOTO) | Q(type=Notification.Type.COMMENT_PHOTO)
    ).exclude(payload={})
    
    photo_count = 0
    for notif in photo_notifications:
        photo_id = notif.payload.get('photo_id')
        if photo_id:
            try:
                photo = PublicPhoto.objects.get(pk=photo_id)
                new_url = photo.get_absolute_url()
                
                if notif.link != new_url:
                    notif.link = new_url
                    notif.save(update_fields=['link'])
                    photo_count += 1
                    print(f"✓ Photo notification {notif.id}: {notif.link}")
            except PublicPhoto.DoesNotExist:
                print(f"✗ Photo {photo_id} not found for notification {notif.id}")
    
    # Находим уведомления с лайками на видео
    video_notifications = Notification.objects.filter(
        Q(type=Notification.Type.LIKE_VIDEO) | Q(type=Notification.Type.COMMENT_VIDEO)
    ).exclude(payload={})
    
    video_count = 0
    for notif in video_notifications:
        video_id = notif.payload.get('video_id')
        if video_id:
            try:
                video = PublicVideo.objects.get(pk=video_id)
                new_url = video.get_absolute_url()
                
                if notif.link != new_url:
                    notif.link = new_url
                    notif.save(update_fields=['link'])
                    video_count += 1
                    print(f"✓ Video notification {notif.id}: {notif.link}")
            except PublicVideo.DoesNotExist:
                print(f"✗ Video {video_id} not found for notification {notif.id}")
    
    print(f"\n{'='*60}")
    print(f"Обновлено уведомлений:")
    print(f"  - Фото: {photo_count}")
    print(f"  - Видео: {video_count}")
    print(f"  - Всего: {photo_count + video_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    print("Начинаем обновление URL в уведомлениях...\n")
    fix_notification_urls()
    print("\nГотово!")
