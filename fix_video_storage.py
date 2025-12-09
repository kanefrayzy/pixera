"""
Скрипт для исправления хранения видео:
1. Добавляет поле result_video в модель GenerationJob
2. Обновляет задачи для скачивания видео локально
3. Скачивает существующие видео из URL
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

import requests
import logging
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from generate.models import GenerationJob

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def download_video(url: str, timeout: int = 300) -> bytes:
    """Скачивает видео по URL и возвращает байты."""
    headers = {
        "User-Agent": "AI-Gallery/1.0",
        "Accept": "video/*,*/*;q=0.8"
    }

    for attempt in range(3):
        try:
            log.info(f"Downloading video from {url} (attempt {attempt + 1}/3)")
            r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True, stream=True)
            r.raise_for_status()

            # Скачиваем по частям для больших файлов
            content = b''
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk

            log.info(f"Downloaded {len(content)} bytes")
            return content
        except Exception as e:
            log.error(f"Download attempt {attempt + 1} failed: {e}")
            if attempt == 2:
                raise

    raise Exception("Failed to download video after 3 attempts")


def fix_video_storage():
    """Скачивает все видео из URL и сохраняет локально."""

    # Находим все видео задачи с URL но без локального файла
    video_jobs = GenerationJob.objects.filter(
        generation_type='video',
        status=GenerationJob.Status.DONE,
        result_video_url__isnull=False
    ).exclude(result_video_url='')

    total = video_jobs.count()
    log.info(f"Found {total} video jobs with URLs")

    success_count = 0
    error_count = 0

    for i, job in enumerate(video_jobs, 1):
        try:
            log.info(f"Processing job {job.pk} ({i}/{total})")

            # Проверяем, есть ли уже локальный файл
            if job.result_image and job.result_image.name:
                if default_storage.exists(job.result_image.name):
                    log.info(f"Job {job.pk} already has local file, skipping")
                    success_count += 1
                    continue

            # Скачиваем видео
            video_url = job.result_video_url
            if not video_url:
                log.warning(f"Job {job.pk} has no video URL")
                error_count += 1
                continue

            try:
                video_bytes = download_video(video_url)

                # Сохраняем локально
                filename = f"videos/{job.pk}.mp4"
                job.result_image.save(filename, ContentFile(video_bytes), save=False)

                # Обновляем result_video_url, чтобы везде использовать локальный файл
                try:
                    local_url = default_storage.url(job.result_image.name)
                except Exception:
                    local_url = job.result_video_url
                job.result_video_url = local_url or job.result_video_url

                job.save(update_fields=['result_image', 'result_video_url'])

                log.info(f"✓ Job {job.pk}: Saved video locally ({len(video_bytes)} bytes), url={job.result_video_url}")
                success_count += 1

            except Exception as e:
                log.error(f"✗ Job {job.pk}: Failed to download/save video: {e}")
                error_count += 1

        except Exception as e:
            log.error(f"✗ Job {job.pk}: Unexpected error: {e}")
            error_count += 1

    log.info(f"\n{'='*60}")
    log.info(f"SUMMARY:")
    log.info(f"Total jobs: {total}")
    log.info(f"Success: {success_count}")
    log.info(f"Errors: {error_count}")
    log.info(f"{'='*60}\n")


if __name__ == '__main__':
    print("Starting video storage fix...")
    print("This will download all videos from URLs and save them locally.")
    print("This may take a while depending on the number of videos.\n")

    try:
        fix_video_storage()
        print("\n✓ Video storage fix completed!")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
