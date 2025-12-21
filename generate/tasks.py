from __future__ import annotations

import io
import logging
import os
import time
from typing import Optional

import requests
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from dotenv import load_dotenv

from dashboard.models import Wallet
from .models import GenerationJob
from .models_image import ImageModelConfiguration
from ai_gallery.services.runware_client import _extract_video_url as _rw_extract_video_url

try:
    # Если есть готовый клиент — используем его (маршруты, парсинг и т.п.)
    from .services import runware as rw
except Exception:  # модуль может отсутствовать
    rw = None  # type: ignore

log = logging.getLogger(__name__)

# ── Константы ────────────────────────────────────────────────────────────────
CACHE_TTL = 60 * 60 * 24 * 30  # 30 дней
RUNWARE_QUEUE = getattr(settings, "CELERY_QUEUE_SUBMIT", "runware_submit")
FIRST_POLL_DELAY = int(getattr(settings, "RUNWARE_FIRST_POLL_DELAY", 5))
STUCK_TIMEOUT_SEC = int(getattr(settings, "RUNWARE_STUCK_TIMEOUT_SEC", 90))
FALLBACK_WIDTH = int(getattr(settings, "RUNWARE_FALLBACK_WIDTH", 768))
FALLBACK_HEIGHT = int(getattr(settings, "RUNWARE_FALLBACK_HEIGHT", 768))

DEMO_IF_UNAUTHORIZED = bool(
    getattr(settings, "RUNWARE_DEMO_IF_UNAUTHORIZED", True))

# ── Ключи для кэша ───────────────────────────────────────────────────────────


def _img_key(job_id: int) -> str:
    return f"genimg:{job_id}"


def _img_url_key(job_id: int) -> str:
    return f"genimgurl:{job_id}"

# ── Безопасные сеттеры ───────────────────────────────────────────────────────


def _safe_set(obj, field: str, value) -> None:
    if hasattr(obj, field):
        setattr(obj, field, value)


def _safe_fields(obj, fields: list[str]) -> list[str]:
    return [f for f in fields if hasattr(obj, f)]

# ── Мини-клиент Runware (если нет services/runware.py) ───────────────────────


def _get_api_key() -> str:
    """
    Динамически загружает API ключ из .env файла.
    Это позволяет обновлять ключ без перезапуска сервера.
    """
    load_dotenv(override=True)
    key = os.getenv("RUNWARE_API_KEY", "")
    return key


def _auth_headers() -> dict:
    key = _get_api_key()
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "AI-Gallery/1.0",
    }


def _submit_sync_direct(prompt: str, model_id: str, *, width: int, height: int) -> str:
    """
    Минимальный Sync-запрос к Runware. Возвращает URL изображения.
    Используется, только если нет .services.runware.
    """
    api = getattr(settings, "RUNWARE_API_URL",
                  "https://api.runware.ai/v1").rstrip("/")

    # Получаем конфигурацию модели из БД
    model_config = None
    try:
        model_config = ImageModelConfiguration.objects.get(model_id=model_id)
    except ImageModelConfiguration.DoesNotExist:
        log.warning(f"Model config not found for {model_id}, using defaults")

    payload = {
        "model": model_id,
        "prompt": prompt,
        "width": width,
        "height": height,
    }

    # Добавляем параметры только если модель их поддерживает
    if model_config:
        if model_config.supports_steps:
            payload["steps"] = model_config.default_steps or 33
        if model_config.supports_cfg_scale:
            payload["cfg_scale"] = float(model_config.default_cfg_scale or 3.1)
    else:
        # Fallback для моделей без конфигурации (старое поведение)
        payload.update({
            "steps": 33,
            "cfg_scale": 3.1,
        })

    r = requests.post(f"{api}/images/generate", json=payload,
                      headers=_auth_headers(), timeout=60)
    if r.status_code == 401:
        raise requests.HTTPError("401 Unauthorized from Runware")
    r.raise_for_status()
    data = r.json() if r.headers.get("content-type",
                                     "").startswith("application/json") else {}
    # Пробуем распространённые поля для URL
    url = (data.get("imageURL") or data.get("url") or
           (data.get("data") and data["data"][0].get("imageURL")))
    if not url:
        raise RuntimeError("Runware response without image URL")
    return url

# ── Генерация DEMO-картинки (без Runware) ────────────────────────────────────


def _finalize_job_with_bytes(job: GenerationJob, content: bytes, ext: str = "png") -> None:
    """Финализируем задачу готовыми байтами изображения."""
    cache.set(_img_key(job.pk), content, timeout=CACHE_TTL)
    job.result_image.save(
        f"generated/{job.pk}.{ext}", ContentFile(content), save=False)
    job.status = GenerationJob.Status.DONE
    job.error = ""
    _safe_set(job, "provider_status", "success")
    job.save(update_fields=_safe_fields(
        job, ["status", "error", "result_image", "provider_status"]))


# ── Синхронный polling для видео (без Celery worker) ──────────────────────────
def _sync_poll_video_until_done(job_id: int, task_uuid: str, max_attempts: int = 120, delay_seconds: int = 1) -> None:
    """
    Синхронный polling статуса видео в цикле (для режима без Celery worker).
    Используется когда CELERY_TASK_ALWAYS_EAGER=True или USE_CELERY=False.
    """
    from ai_gallery.services.runware_client import check_video_status

    for attempt in range(1, max_attempts + 1):
        try:
            job = GenerationJob.objects.get(pk=job_id)

            if job.status in (GenerationJob.Status.DONE, GenerationJob.Status.FAILED):
                return

            time.sleep(delay_seconds)

            status_data = check_video_status(task_uuid)
            log.info(f"Video poll attempt {attempt}/{max_attempts} for job {job_id}: {status_data}")

            raw = status_data or {}
            data_val = raw.get('data')
            item = None

            if isinstance(data_val, list) and data_val:
                item = data_val[0]
            elif isinstance(data_val, dict):
                item = data_val
            else:
                item = raw

            status_val = (item or {}).get('status') or raw.get('status') or (item or {}).get('state')

            video_url = (
                (item or {}).get('videoURL')
                or raw.get('videoURL')
                or ((item or {}).get('output') or {}).get('videoURL')
            )

            if not video_url:
                try:
                    video_url = _rw_extract_video_url(item or {}) or _rw_extract_video_url(raw or {})
                except Exception:
                    video_url = None

            if str(status_val).lower() in {'completed', 'done', 'finished', 'success', 'succeeded'} and video_url:
                log.info(f"Video job {job_id} completed! URL: {video_url}")

                _download_and_save_video(job, video_url)

                from dashboard.models import Wallet
                from .models import FreeGrant

                token_cost = job.video_model.token_cost if job.video_model else 20

                with transaction.atomic():
                    if job.user and not job.user.is_staff:
                        wallet = Wallet.objects.select_for_update().get(user=job.user)
                        wallet.balance -= token_cost
                        wallet.save()
                    elif not job.user:
                        grant = FreeGrant.objects.filter(
                            Q(gid=job.guest_gid) | Q(fp=job.guest_fp),
                            user__isnull=True
                        ).select_for_update().first()
                        if grant:
                            grant.spend(token_cost)

                job.result_video_url = job.result_video_url or video_url
                job.status = GenerationJob.Status.DONE
                job.tokens_spent = token_cost
                from datetime import timedelta
                job.video_cached_until = timezone.now() + timedelta(hours=24)
                job.save()
                return

            if str(status_val).lower() in {'failed', 'error'}:
                job.status = GenerationJob.Status.FAILED
                job.error = raw.get('error') or (item or {}).get('error') or 'Video generation failed'
                job.save()
                _refund_if_needed(job)
                return

            log.info(f"Video job {job_id} still processing (attempt {attempt}/{max_attempts})")

        except GenerationJob.DoesNotExist:
            log.error(f"Video job {job_id} not found during sync polling")
            return
        except Exception as e:
            log.error(f"Error in sync polling for job {job_id}, attempt {attempt}: {e}", exc_info=True)
            if attempt >= max_attempts:
                try:
                    job = GenerationJob.objects.get(pk=job_id)
                    job.status = GenerationJob.Status.FAILED
                    job.error = f"Sync polling failed: {str(e)}"
                    job.save()
                    _refund_if_needed(job)
                except Exception:
                    pass
                return

    try:
        job = GenerationJob.objects.get(pk=job_id)
        job.status = GenerationJob.Status.FAILED
        job.error = "Video generation timed out"
        job.save()
        _refund_if_needed(job)
    except Exception:
        pass

    log.error(f"Video job {job_id} timed out after {max_attempts} attempts")


# ── Video Generation Async ────────────────────────────────────────────────────
@shared_task(
    bind=True,
    name="generate.tasks.process_video_generation_async",
    queue=RUNWARE_QUEUE,
    soft_time_limit=180,
    time_limit=240,
    max_retries=3,
    autoretry_for=(requests.RequestException,),
)
def process_video_generation_async(
    self,
    job_id: int,
    generation_mode: str,
    source_image_url: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    provider_fields: Optional[dict] = None
) -> None:
    """
    Асинхронная обработка генерации видео через Celery.
    Поддерживает до 100,000 обработок в день.

    Args:
        job_id: ID задачи генерации
        generation_mode: 't2v' или 'i2v'
        source_image_url: URL исходного изображения для I2V
        image_bytes: Байты изображения для I2V
        provider_fields: Дополнительные параметры провайдера
    """
    try:
        job = GenerationJob.objects.get(pk=job_id)
    except GenerationJob.DoesNotExist:
        log.error(f"Video job {job_id} not found")
        return

    if job.status in (GenerationJob.Status.DONE, GenerationJob.Status.FAILED):
        return

    try:
        # Импортируем функции генерации видео
        from ai_gallery.services.runware_client import (
            generate_video_via_rest,
            generate_video_from_image,
            RunwareVideoError,
        )

        # Подготовка параметров
        prompt = job.prompt or ""
        model_id = job.video_model.model_id if job.video_model else "vidu:2@0"
        duration = job.video_duration or 5
        aspect_ratio = job.video_aspect_ratio or "16:9"
        resolution = job.video_resolution or "1920x1080"
        camera_movement = job.video_camera_movement or None
        seed = job.video_seed or None

        provider_fields = provider_fields or {}

        log.info(
            f"Starting async video generation: job={job_id}, mode={generation_mode}, "
            f"model={model_id}, duration={duration}s"
        )

        # Генерация видео
        if generation_mode == 'i2v':
            # Image-to-Video
            motion_strength = job.video_motion_strength or 45

            result = generate_video_from_image(
                prompt=prompt,
                model_id=model_id,
                image_url=source_image_url,
                image_bytes=image_bytes,
                duration=duration,
                motion_strength=motion_strength,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                camera_movement=camera_movement,
                seed=seed,
                **provider_fields
            )
        else:
            # Text-to-Video
            result = generate_video_via_rest(
                prompt=prompt,
                model_id=model_id,
                duration=duration,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                camera_movement=camera_movement,
                seed=seed,
                **provider_fields
            )

        # Обработка результата
        if isinstance(result, dict) and result.get('async'):
            # Асинхронный режим - сохраняем taskUUID и запускаем polling
            task_uuid = result.get('taskUUID')
            if task_uuid:
                job.provider_task_uuid = task_uuid
                job.provider_status = 'queued'
                job.save(update_fields=[
                         'provider_task_uuid', 'provider_status'])

                log.info(
                    f"Video job {job_id} queued with taskUUID={task_uuid}, starting polling")

                # Определяем режим: если USE_CELERY=True и брокер НЕ memory — используем async
                use_celery = getattr(settings, 'USE_CELERY', False)
                broker_url = getattr(settings, 'CELERY_BROKER_URL', 'memory://')

                if use_celery and not broker_url.startswith('memory'):
                    # Асинхронный режим — отправляем polling задачу в очередь
                    log.info(f"Video job {job_id}: scheduling async polling via Celery worker")
                    poll_video_result.apply_async(
                        args=[job_id, 1],
                        countdown=10,
                        queue=RUNWARE_QUEUE
                    )
                else:
                    # Синхронный режим — выполняем polling прямо здесь
                    log.info(f"Video job {job_id}: running sync polling (Celery disabled or memory broker)")
                    _sync_poll_video_until_done(job_id, task_uuid, max_attempts=60, delay_seconds=10)
            else:
                raise RunwareVideoError("No taskUUID in async response")

        elif isinstance(result, str):
            # Синхронный режим - получили URL сразу
            log.info(
                f"Video job {job_id} completed synchronously, URL: {result}")

            # Скачиваем и сохраняем видео локально
            _download_and_save_video(job, result)

            # Списываем токены
            from dashboard.models import Wallet
            from generate.models import FreeGrant

            token_cost = job.video_model.token_cost if job.video_model else 20

            with transaction.atomic():
                if job.user and not job.user.is_staff:
                    wallet = Wallet.objects.select_for_update().get(user=job.user)
                    wallet.balance -= token_cost
                    wallet.save()
                elif not job.user:
                    # Гость
                    grant = FreeGrant.objects.filter(
                        Q(gid=job.guest_gid) | Q(fp=job.guest_fp),
                        user__isnull=True
                    ).first()
                    if grant:
                        grant.spend(token_cost)

                # Обновляем job (если локальное сохранение прошло — используем его URL)
                job.result_video_url = job.result_video_url or result
                job.status = GenerationJob.Status.DONE
                job.tokens_spent = token_cost
                from datetime import timedelta
                from django.utils import timezone
                job.video_cached_until = timezone.now() + timedelta(hours=24)
                job.save()
        else:
            raise RunwareVideoError(
                f"Unexpected result format: {type(result)}")

    except RunwareVideoError as e:
        log.error(f"Video generation error for job {job_id}: {e}")
        job.status = GenerationJob.Status.FAILED
        job.error = str(e)
        job.save(update_fields=['status', 'error'])
        _refund_if_needed(job)

    except Exception as e:
        log.error(
            f"Unexpected error in video generation for job {job_id}: {e}", exc_info=True)
        job.status = GenerationJob.Status.FAILED
        job.error = f"Внутренняя ошибка: {str(e)}"
        job.save(update_fields=['status', 'error'])
        _refund_if_needed(job)


# ── Video Polling ─────────────────────────────────────────────────────────────
@shared_task(
    bind=True,
    name="generate.tasks.poll_video_result",
    queue=RUNWARE_QUEUE,
    soft_time_limit=180,  # Видео генерируется дольше
    time_limit=240,
    max_retries=120,  # 2 минуты максимум
)
def poll_video_result(self, job_id: int, attempt: int = 1) -> None:
    """
    Polling статуса видео от Runware.
    Запускается автоматически после video_submit.
    """
    try:
        job = GenerationJob.objects.get(pk=job_id)
    except GenerationJob.DoesNotExist:
        log.error(f"Video job {job_id} not found")
        return

    if job.status in (GenerationJob.Status.DONE, GenerationJob.Status.FAILED):
        return

    provider_uuid = getattr(job, "provider_task_uuid", None)
    if not provider_uuid:
        log.warning(f"Video job {job_id} has no provider_task_uuid")
        return

    # Импортируем функцию проверки статуса
    try:
        from ai_gallery.services.runware_client import check_video_status

        status_data = check_video_status(provider_uuid)
        log.info(
            f"Video poll attempt {attempt} for job {job_id}: {status_data}")

        # Парсим ответ
        raw = status_data or {}
        data_val = raw.get('data')
        item = None

        if isinstance(data_val, list) and data_val:
            item = data_val[0]
        elif isinstance(data_val, dict):
            item = data_val
        else:
            item = raw

        status_val = (item or {}).get('status') or raw.get(
            'status') or (item or {}).get('state')

        # Пытаемся вытащить URL видео из типичных полей
        video_url = (
            (item or {}).get('videoURL')
            or raw.get('videoURL')
            or ((item or {}).get('output') or {}).get('videoURL')
        )

        # Фоллбек: используем общий парсер Runware (_extract_video_url), чтобы поддержать outputs/videos массивы
        if not video_url:
            try:
                # сначала пытаемся на элементе, затем на всём ответе
                video_url = _rw_extract_video_url(item or {}) or _rw_extract_video_url(raw or {})
            except Exception:
                video_url = None

        # Успех! (учитываем больше вариантов статусов Runware)
        if str(status_val).lower() in {'completed', 'done', 'finished', 'success', 'succeeded'} and video_url:
            log.info(f"Video job {job_id} completed! URL: {video_url}")

            # Скачиваем и сохраняем видео локально
            _download_and_save_video(job, video_url)

            # Списываем токены
            from dashboard.models import Wallet
            from .models import FreeGrant

            token_cost = job.video_model.token_cost if job.video_model else 20

            with transaction.atomic():
                if job.user and not job.user.is_staff:
                    wallet = Wallet.objects.select_for_update().get(user=job.user)
                    wallet.balance -= token_cost
                    wallet.save()
                elif not job.user:
                    # Гость
                    grant = FreeGrant.objects.filter(
                        Q(gid=job.guest_gid) | Q(fp=job.guest_fp),
                        user__isnull=True
                    ).select_for_update().first()
                    if grant:
                        grant.spend(token_cost)

            # Обновляем job (если локальное сохранение прошло — используем его URL)
            job.result_video_url = job.result_video_url or video_url
            job.status = GenerationJob.Status.DONE
            job.tokens_spent = token_cost
            from datetime import timedelta
            from django.utils import timezone
            job.video_cached_until = timezone.now() + timedelta(hours=24)
            job.save()

            return

        # Провал
        if str(status_val).lower() in {'failed', 'error'}:
            job.status = GenerationJob.Status.FAILED
            job.error = raw.get('error') or (item or {}).get(
                'error') or 'Video generation failed'
            job.save()

            # Рефанд токенов
            _refund_if_needed(job)
            return

        # Всё ещё обрабатывается
        log.info(f"Video job {job_id} still processing (attempt {attempt})")

        # Проверяем таймаут (60 попыток * 10 сек = ~10 минут максимум)
        if attempt >= 60:
            log.error(f"Video job {job_id} timed out after {attempt} attempts")
            job.status = GenerationJob.Status.FAILED
            job.error = "Video generation timed out"
            job.save()
            _refund_if_needed(job)
            return

        # Перезапускаем через 10 секунд
        poll_video_result.apply_async(
            args=[job_id, attempt + 1],
            countdown=10,
            queue=RUNWARE_QUEUE
        )

    except Exception as e:
        log.error(f"Error polling video job {job_id}: {e}", exc_info=True)

        # Таймаут или продолжаем?
        if attempt >= 120:
            job.status = GenerationJob.Status.FAILED
            job.error = f"Polling failed: {str(e)}"
            job.save()
            _refund_if_needed(job)
        else:
            # Retry через 2 секунды
            poll_video_result.apply_async(
                args=[job_id, attempt + 1],
                countdown=2,
                queue=RUNWARE_QUEUE
            )


def _demo_render(job: GenerationJob, width: int = FALLBACK_WIDTH, height: int = FALLBACK_HEIGHT) -> None:
    """Создаём простую PNG-картинку с текстом промпта — для DEV/демо."""
    # Ограничение размера для предотвращения DoS
    width = min(max(64, width), 2048)
    height = min(max(64, height), 2048)
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        # На крайний случай — 1x1 PNG
        _finalize_job_with_bytes(job, b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                                 b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                                 b"\x00\x00\x00\x0bIDATx\x9cc``\x00\x00\x00\x02\x00\x01"
                                 b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82")
        return

    img = Image.new("RGB", (max(64, width), max(64, height)), (18, 18, 24))
    d = ImageDraw.Draw(img)
    # мягкий градиент
    for y in range(img.height):
        shade = 18 + int(90 * (y / max(1, img.height - 1)))
        d.line([(0, y), (img.width, y)], fill=(shade, shade, shade))

    # надписи
    try:
        font = ImageFont.truetype("arial.ttf", 20)
        big = ImageFont.truetype("arial.ttf", 48)
    except Exception:
        font = ImageFont.load_default()
        big = ImageFont.load_default()

    d.text((24, 20), "DEMO", font=big, fill=(255, 170, 60))
    txt = (job.prompt or "").strip() or "Pixera"
    # переносим вручную
    lines, line, max_w = [], "", img.width - 48
    for word in txt.split():
        t = (line + " " + word).strip()
        if d.textlength(t, font=font) > max_w and line:
            lines.append(line)
            line = word
        else:
            line = t
    if line:
        lines.append(line)
    y = 90
    for ln in lines[:8]:
        d.text((24, y), ln, font=font, fill=(230, 230, 230))
        y += 26

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    _finalize_job_with_bytes(job, buf.getvalue(), ext="png")


def _download_and_save_video(job: GenerationJob, video_url: str) -> Optional[str]:
    """Скачивает видео по URL и сохраняет локально в MEDIA. Возвращает локальный URL или None при неудаче."""
    if not video_url:
        log.warning(f"Job {job.pk}: No video URL to download")
        return None

    try:
        log.info(f"Job {job.pk}: Downloading video from {video_url}")

        headers = {
            "User-Agent": "AI-Gallery/1.0",
            "Accept": "video/*,*/*;q=0.8"
        }

        # Скачиваем видео с повторными попытками
        video_content = None
        for attempt in range(3):
            try:
                r = requests.get(video_url, timeout=300, headers=headers, allow_redirects=True, stream=True)
                r.raise_for_status()

                # Скачиваем по частям для больших файлов
                content = b''
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        content += chunk

                video_content = content
                break
            except Exception as e:
                log.warning(f"Job {job.pk}: Download attempt {attempt + 1}/3 failed: {e}")
                if attempt == 2:
                    raise
                time.sleep(1.5 * (attempt + 1))

        if video_content:
            # Сохраняем видео локально в persist/videos/%Y/%m/
            try:
                now = timezone.now()
            except Exception:
                from django.utils import timezone as _tz
                now = _tz.now()
            rel_path = f"persist/videos/{now:%Y/%m}/job_{job.pk}.mp4"
            default_storage.save(rel_path, ContentFile(video_content))
            persisted_url = default_storage.url(rel_path)
            # Обновим job на локальный URL
            try:
                job.result_video_url = persisted_url
                job.save(update_fields=["result_video_url"])
            except Exception:
                pass
            log.info(f"Job {job.pk}: Video saved locally ({len(video_content)} bytes) -> {persisted_url}")
            return persisted_url
        else:
            log.error(f"Job {job.pk}: Failed to download video content")
            return None

    except Exception as e:
        log.error(f"Job {job.pk}: Error downloading/saving video: {e}")
        return None
        # Не прерываем выполнение - URL всё равно сохранён


def _refund_if_needed(job: GenerationJob) -> None:
    """Рефандим токены авторизованному пользователю или в FreeGrant для гостя."""
    spent = int(getattr(job, "tokens_spent", 0) or 0)
    if spent <= 0:
        return

    try:
        with transaction.atomic():
            if job.user_id:
                # Авторизованный пользователь - возвращаем в кошелек
                w = Wallet.objects.select_for_update().get(user_id=job.user_id)
                w.balance = int(w.balance or 0) + spent
                w.save(update_fields=["balance"])
                log.info(
                    f"Refunded {spent} tokens to wallet for user {job.user_id}")
            else:
                # Гость - возвращаем в FreeGrant
                from .models import FreeGrant
                grant_filters = []
                if job.guest_gid:
                    grant_filters.append(Q(gid=job.guest_gid))
                if job.guest_fp:
                    grant_filters.append(Q(fp=job.guest_fp))

                if grant_filters:
                    grant_q = grant_filters[0]
                    for f in grant_filters[1:]:
                        grant_q |= f

                    grant = FreeGrant.objects.filter(
                        grant_q, user__isnull=True).first()
                    if grant:
                        grant.consumed = max(0, int(grant.consumed) - spent)
                        grant.save(update_fields=["consumed"])
                        log.info(
                            f"Refunded {spent} tokens to FreeGrant {grant.pk}")
                    else:
                        log.warning(
                            f"No FreeGrant found for refund of job {job.pk}")

    except Exception as e:
        log.exception("Refund failed for job %s (user %s, spent=%s): %s",
                      job.pk, job.user_id, spent, e)

# ── Сабмит ────────────────────────────────────────────────────────────────────


@shared_task(
    bind=True,
    name="generate.tasks.run_generation_async",
    queue=RUNWARE_QUEUE,
    soft_time_limit=60,
    time_limit=120,
    max_retries=3,
    autoretry_for=(requests.RequestException,),
)
@transaction.atomic
def run_generation_async(self, job_id: int) -> None:
    try:
        job = GenerationJob.objects.select_for_update().get(pk=job_id)
    except GenerationJob.DoesNotExist:
        log.error(f"GenerationJob {job_id} not found")
        return

    if job.status in (GenerationJob.Status.DONE, GenerationJob.Status.RUNNING):
        return

    # Валидация промпта на предмет потенциально опасного контента
    if not job.prompt or len(job.prompt) > 2000:
        job.status = GenerationJob.Status.FAILED
        job.error = "Invalid prompt"
        job.save(update_fields=["status", "error"])
        return

    job.status = GenerationJob.Status.RUNNING
    job.error = ""
    _safe_set(job, "provider_status", "starting")
    job.save(update_fields=_safe_fields(
        job, ["status", "error", "provider_status"]))

    model_id = job.model_id or getattr(
        settings, "RUNWARE_DEFAULT_MODEL", "runware:101@1")

    # Определяем model_id в нижнем регистре для проверок
    try:
        mid = (job.model_id or model_id or "").strip().lower()
    except Exception:
        mid = (model_id or "").strip().lower()

    # Per-model resolution mapping
    w = 1024
    h = 1024

    # Попытка извлечь width и height из video_resolution (используется для хранения aspect ratio размеров)
    if job.video_resolution and 'x' in job.video_resolution.lower():
        try:
            parts = job.video_resolution.lower().split('x')
            if len(parts) == 2:
                w = int(parts[0].strip())
                h = int(parts[1].strip())
                log.info(f"Using custom dimensions from job.video_resolution: {w}x{h}")
        except (ValueError, AttributeError) as e:
            log.warning(f"Failed to parse video_resolution '{job.video_resolution}': {e}")
            # Fallback to model defaults
            if mid == "bfl:2@2":
                w = 2048
                h = 2048
            elif mid == "bytedance:5@0":
                w = 1024
                h = 1024
    else:
        # No custom resolution - use model defaults
        if mid == "bfl:2@2":
            w = 2048
            h = 2048
        elif mid == "bytedance:5@0":
            w = 1024
            h = 1024

    # Определяем режим: если USE_CELERY=True и брокер НЕ memory — используем async
    use_celery = getattr(settings, 'USE_CELERY', False)
    broker_url = getattr(settings, 'CELERY_BROKER_URL', 'memory://')
    force_sync = not (use_celery and not broker_url.startswith('memory'))

    # ========================================================================
    # LOAD REFERENCE IMAGES FIRST (for ALL models except Face Retouch)
    # ========================================================================
    general_refs: list[str] = []

    # Load reference images from ReferenceImage model (for ALL models)
    try:
        from .models import ReferenceImage
        ref_images = ReferenceImage.objects.filter(
            job=job).order_by('order', 'uploaded_at')

        if ref_images.exists():
            log.info(f"Found {ref_images.count()} reference images for job {job.pk}")

        for ref_img in ref_images:
            try:
                # Upload to Runware and get UUID
                with default_storage.open(ref_img.image.name, "rb") as f:
                    img_bytes = f.read()
                from ai_gallery.services.runware_client import _upload_image_to_runware
                img_uuid = _upload_image_to_runware(img_bytes)
                if img_uuid:
                    general_refs.append(img_uuid)
                    log.info(
                        f"Uploaded reference image {ref_img.id} for job {job.pk}: {img_uuid}")
            except Exception as e:
                log.error(
                    f"Failed to upload reference image {ref_img.id}: {e}", exc_info=True)
    except Exception as e:
        log.error(f"Failed to load reference images for job {job.pk}: {e}", exc_info=True)

    # Log final count
    if general_refs:
        log.info(f"Total {len(general_refs)} reference images ready for job {job.pk}")
    else:
        log.info(f"No reference images for job {job.pk}")

    # ========================================================================
    # Face Retouch (photo->photo) parameters from job.provider_payload
    # ========================================================================
    retouch_ref = None
    retouch_cfg = 4.0
    retouch_sched = "FlowMatchEulerDiscreteScheduler"
    retouch_accel = "medium"
    number_results = None
    retouch_refs: list[str] = []

    try:
        if mid == "runware:108@22" and isinstance(job.provider_payload, dict):
            retouch_ref = (job.provider_payload or {}).get(
                "retouch_ref_url") or None
            _cfg = (job.provider_payload or {}).get("cfg_scale")
            if _cfg is not None and str(_cfg).strip() != "":
                retouch_cfg = float(_cfg)
            retouch_sched = (job.provider_payload or {}).get(
                "scheduler") or retouch_sched
            retouch_accel = (job.provider_payload or {}).get(
                "acceleration") or retouch_accel
    except Exception:
        pass

    try:
        if mid == "runware:108@22":
            pay = job.provider_payload or {}
            # Variants
            try:
                _nr = (pay.get("number_results")
                       or pay.get("variants") or "").strip()
                if _nr:
                    number_results = int(_nr)
            except Exception:
                number_results = None
            # Size presets or custom
            try:
                ratio = (pay.get("retouch_ratio") or "").strip().lower()
                cw = int(pay.get("retouch_width") or 0)
                ch = int(pay.get("retouch_height") or 0)

                def _apply_ratio(rt: str):
                    nonlocal w, h
                    try:
                        a, b = [int(x) for x in rt.split(":")]
                        # constrain with max side 1024
                        if a >= b:
                            w = 1024
                            h = max(64, int(1024 * b / a))
                        else:
                            h = 1024
                            w = max(64, int(1024 * a / b))
                    except Exception:
                        pass
                if ratio == "custom" and cw and ch:
                    w = max(64, min(2048, int(cw)))
                    h = max(64, min(2048, int(ch)))
                elif ratio in {"1:1", "16:9", "4:3", "3:2", "2:3", "3:4", "9:16", "9:21", "21:9"}:
                    _apply_ratio(ratio)
            except Exception:
                pass
            # Try to upload to Runware to obtain UUID (preferred format)
            try:
                ref_path = (pay.get("retouch_ref_path") or "").strip()
                if ref_path:
                    with default_storage.open(ref_path, "rb") as f:
                        img_bytes = f.read()
                    try:
                        from ai_gallery.services.runware_client import _upload_image_to_runware, runware_image_url
                        img_uuid = _upload_image_to_runware(img_bytes)
                        if img_uuid:
                            # для Face Retouch требуем UUID v4 предыдущей загрузки
                            retouch_refs = [img_uuid]
                    except Exception:
                        # ignore, will re-attempt below
                        pass
                # If we only have a URL and provider requires UUID, try to download and upload
                if not retouch_refs and retouch_ref:
                    try:
                        # fetch bytes and upload
                        r = requests.get(retouch_ref, timeout=20)
                        if r.ok and r.content:
                            from ai_gallery.services.runware_client import _upload_image_to_runware, runware_image_url
                            img_uuid = _upload_image_to_runware(r.content)
                            if img_uuid:
                                retouch_refs = [img_uuid]
                    except Exception:
                        pass
            except Exception:
                pass
            # Filter to UUID only (strict), provider rejects raw URLs in referenceImages for this model
            try:
                # Дальнейшая фильтрация не требуется — мы уже конвертируем в CDN URL строки
                retouch_refs = retouch_refs or []
            except Exception:
                pass
            # If still no valid refs, do a second forced upload attempt; if fails — try inline base64
            try:
                if mid == "runware:108@22" and not retouch_refs:
                    ref_path = (pay.get("retouch_ref_path") or "").strip()
                    if ref_path:
                        with default_storage.open(ref_path, "rb") as f:
                            img_bytes = f.read()
                        from ai_gallery.services.runware_client import _upload_image_to_runware, runware_image_url
                        img_uuid = _upload_image_to_runware(img_bytes)
                        if img_uuid:
                            retouch_refs = [img_uuid]
            except Exception:
                pass
            # Больше не используем imageBase64 — требуется ссылочный формат CDN. Если не получилось — оставим пусто (ниже вернём понятную ошибку).
            try:
                pass
            except Exception:
                pass
    except Exception:
        pass

    # === SYNC режим (локальная отладка/без брокера) ===========================
    if force_sync:
        try:
            # 1) Предпочитаем официальный клиент, если есть
            if rw is not None:
                if mid == "runware:108@22":
                    # Require at least one valid reference image (prefer UUID)
                    if not retouch_refs:
                        job.status = GenerationJob.Status.FAILED
                        job.error = "Для Face Retouch требуется фото (reference image). Не удалось загрузить изображение в провайдер."
                        job.save(update_fields=_safe_fields(
                            job, ["status", "error"]))
                        _refund_if_needed(job)
                        return
                    url = rw.submit_image_inference_sync(
                        prompt=job.prompt,
                        model_id=model_id,
                        width=w, height=h,
                        steps=33, cfg_scale=retouch_cfg,
                        scheduler=retouch_sched,
                        reference_images=retouch_refs,
                        acceleration=retouch_accel,
                        number_results=number_results,
                    )
                else:
                    url = rw.submit_image_inference_sync(
                        prompt=job.prompt,
                        model_id=model_id,
                        width=w, height=h, steps=33, cfg_scale=3.1,
                        scheduler=None,
                        reference_images=general_refs if general_refs else None,
                    )
                _finalize_job_with_url(job, url)
                return
            else:
                url = _submit_sync_direct(
                    job.prompt, model_id, width=w, height=h)
                _finalize_job_with_url(job, url)
                return

        except Exception as e:
            msg = str(e)
            unauthorized = ("401" in msg) or ("Unauthorized" in msg)
            if unauthorized and DEMO_IF_UNAUTHORIZED:
                log.warning("Runware 401 → DEMO render for job %s", job.pk)
                _demo_render(job)
                return

            # Fallback: попытка прямого sync-запроса к /images/generate (НЕ для Face Retouch)
            try:
                if mid != "runware:108@22":
                    url = _submit_sync_direct(
                        job.prompt, model_id, width=w, height=h)
                    _finalize_job_with_url(job, url)
                    return
            except Exception as e2:
                log.error(
                    "Direct sync fallback failed for job %s: %s", job.pk, e2)

            job.status = GenerationJob.Status.FAILED
            job.error = (f"sync failed: {msg}")[:300]
            job.save(update_fields=_safe_fields(job, ["status", "error"]))
            _refund_if_needed(job)
            return

    # === ASYNC режим (webhook + polling) ======================================
    try:
        base = (getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
        token = getattr(settings, "RUNWARE_WEBHOOK_TOKEN", "")
        webhook = f"{base}/generate/api/runware/webhook/?token={token}" if (
            base and token) else None

        if rw is not None:
            if mid == "runware:108@22":
                # Require at least one valid reference image (prefer UUID)
                if not retouch_refs:
                    job.status = GenerationJob.Status.FAILED
                    job.error = "Для Face Retouch требуется фото (reference image). Не удалось загрузить изображение в провайдер."
                    job.save(update_fields=_safe_fields(
                        job, ["status", "error"]))
                    _refund_if_needed(job)
                    return
                task_uuid = rw.submit_image_inference_async(
                    prompt=job.prompt,
                    model_id=model_id,
                    width=w, height=h, steps=33, cfg_scale=retouch_cfg,
                    scheduler=retouch_sched,
                    reference_images=retouch_refs,
                    acceleration=retouch_accel,
                    number_results=number_results,
                    webhook_url=webhook,
                )
            else:
                # Логирование референсов перед отправкой
                log.info(f"Job {job.pk}: Sending to Runware async with {len(general_refs)} reference images: {general_refs}")
                task_uuid = rw.submit_image_inference_async(
                    prompt=job.prompt,
                    model_id=model_id,
                    width=w, height=h, steps=33, cfg_scale=3.1,
                    scheduler=None,
                    reference_images=general_refs if general_refs else None,
                    webhook_url=webhook,
                )
        else:
            # Если нет клиента, принудительно используем синхронный путь
            url = _submit_sync_direct(job.prompt, model_id, width=w, height=h)
            _finalize_job_with_url(job, url)
            return

        _safe_set(job, "provider_task_uuid", task_uuid)
        _safe_set(job, "provider_status", "queued")
        job.save(update_fields=_safe_fields(
            job, ["provider_task_uuid", "provider_status"]))

        poll_runware_result.apply_async(
            args=[job.id, 1], countdown=FIRST_POLL_DELAY, queue=RUNWARE_QUEUE)

    except Exception as e:
        msg = str(e)
        unauthorized = ("401" in msg) or ("Unauthorized" in msg)
        if unauthorized and DEMO_IF_UNAUTHORIZED:
            log.warning(
                "Runware 401 (async submit) → DEMО render for job %s", job.pk)
            _demo_render(job)
            return

        # Fallback: попытка синхронного прямого эндпоинта
        try:
            url = _submit_sync_direct(
                job.prompt, model_id, width=FALLBACK_WIDTH, height=FALLBACK_HEIGHT)
            _finalize_job_with_url(job, url)
            return
        except Exception as e2:
            log.error(
                "Async submit failed and direct sync fallback failed for job %s: %s", job.pk, e2)

        job.status = GenerationJob.Status.FAILED
        job.error = (f"submit failed: {msg}")[:300]
        job.save(update_fields=_safe_fields(job, ["status", "error"]))
        _refund_if_needed(job)

# ── Poll + fallback ───────────────────────────────────────────────────────────


@shared_task(
    bind=True,
    name="generate.tasks.poll_runware_result",
    queue=RUNWARE_QUEUE,
    soft_time_limit=60,
    time_limit=120,
    max_retries=20,
    autoretry_for=(requests.RequestException,),
)
def poll_runware_result(self, job_id: int, attempt: int = 1) -> None:
    job = GenerationJob.objects.get(pk=job_id)
    if job.status in (GenerationJob.Status.DONE, GenerationJob.Status.FAILED):
        return

    provider_uuid = getattr(job, "provider_task_uuid", None)
    if not provider_uuid or rw is None:
        _reschedule_poll(job, attempt)
        return

    data = rw.get_response(provider_uuid)
    status, url = rw.parse_status_and_url(data)

    _safe_set(job, "provider_status", status)
    _safe_set(job, "provider_payload", data)
    _safe_set(job, "last_polled_at", timezone.now())

    # успех
    if (status in ("success", "done") and url) or (url and not status):
        _finalize_job_with_url(job, url)
        return

    # провал
    if status in ("failed", "error"):
        job.status = GenerationJob.Status.FAILED
        job.error = (str(data)[:300]) if data else "provider error"
        job.save(update_fields=_safe_fields(job, [
            "status", "error", "provider_status", "provider_payload", "last_polled_at"
        ]))
        _refund_if_needed(job)
        return

    # ещё обрабатывается
    job.save(update_fields=_safe_fields(
        job, ["provider_status", "provider_payload", "last_polled_at"]))

    # «зависло» → принудительный sync-fallback/DEMO
    if hasattr(rw, "is_processing") and rw.is_processing(status):
        age_sec = (timezone.now() - job.created_at).total_seconds()
        if age_sec >= STUCK_TIMEOUT_SEC:
            try:
                log.warning(
                    "Job %s stuck for %.1fs → sync fallback", job.pk, age_sec)
                if rw is not None:
                    fallback_url = rw.submit_image_inference_sync(
                        prompt=job.prompt,
                        model_id=job.model_id or getattr(
                            settings, "RUNWARE_DEFAULT_MODEL", "runware:101@1"),
                        width=FALLBACK_WIDTH, height=FALLBACK_HEIGHT,
                        steps=33, cfg_scale=3.1, scheduler=None,
                    )
                    _finalize_job_with_url(job, fallback_url)
                else:
                    _demo_render(job, width=FALLBACK_WIDTH,
                                 height=FALLBACK_HEIGHT)
                return
            except Exception as e:
                msg = str(e)
                if (("401" in msg) or ("Unauthorized" in msg)) and DEMO_IF_UNAUTHORIZED:
                    _demo_render(job, width=FALLBACK_WIDTH,
                                 height=FALLBACK_HEIGHT)
                    return
                job.status = GenerationJob.Status.FAILED
                job.error = (f"Provider stuck; fallback failed: {msg}")[:300]
                job.save(update_fields=_safe_fields(job, ["status", "error"]))
                _refund_if_needed(job)
                return

    _reschedule_poll(job, attempt)


def _reschedule_poll(job: GenerationJob, attempt: int) -> None:
    base = max(5, FIRST_POLL_DELAY)
    next_in = min(120, int(base * (1.6 ** max(0, attempt - 1))))
    poll_runware_result.apply_async(
        args=[job.id, attempt + 1], countdown=next_in, queue=RUNWARE_QUEUE)

# ── Финализация по внешнему URL ───────────────────────────────────────────────


def _finalize_job_with_url(job: GenerationJob, image_url: str) -> None:
    """Скачиваем картинку; если CDN падает — кэшируем внешний URL и считаем DONE."""
    if job.status == GenerationJob.Status.DONE:
        return

    # Валидация URL для предотвращения SSRF атак
    if not image_url or not image_url.startswith(('https://', 'http://')):
        job.status = GenerationJob.Status.FAILED
        job.error = "Invalid image URL"
        job.save(update_fields=["status", "error"])
        return

    # Проверка на локальные/приватные адреса
    from urllib.parse import urlparse
    try:
        parsed = urlparse(image_url)
        if parsed.hostname in ('localhost', '127.0.0.1', '0.0.0.0') or \
           parsed.hostname.startswith('192.168.') or \
           parsed.hostname.startswith('10.') or \
           parsed.hostname.startswith('172.'):
            job.status = GenerationJob.Status.FAILED
            job.error = "Invalid image URL"
            job.save(update_fields=["status", "error"])
            return
    except Exception:
        job.status = GenerationJob.Status.FAILED
        job.error = "Invalid image URL"
        job.save(update_fields=["status", "error"])
        return

    timeout = int(getattr(settings, "RUNWARE_DOWNLOAD_TIMEOUT", 300))
    headers = {
        "User-Agent": "AI-Gallery/1.0 (+local)", "Accept": "image/*,*/*;q=0.8"}

    content: Optional[bytes] = None
    last_err: Optional[Exception] = None

    for attempt in range(3):
        try:
            r = requests.get(image_url, timeout=timeout,
                             headers=headers, allow_redirects=True)
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} Server Error")
            r.raise_for_status()
            content = r.content
            break
        except Exception as e:
            last_err = e
            time.sleep(1.2 * (attempt + 1))

    if content is not None:
        cache.set(_img_key(job.pk), content, timeout=CACHE_TTL)
        job.result_image.save(
            f"generated/{job.pk}.jpg", ContentFile(content), save=False)
    else:
        cache.set(_img_url_key(job.pk), image_url, timeout=CACHE_TTL)
        log.warning(
            "Job %s: download failed, serving external URL instead. err=%s", job.pk, last_err)

    job.status = GenerationJob.Status.DONE
    job.error = ""
    _safe_set(job, "provider_status", "success")
    job.save(update_fields=_safe_fields(
        job, ["status", "error", "result_image", "provider_status"]))


# ── Автоудаление неопубликованных работ старше 30 дней ───────────────────────
@shared_task(queue="default")
def delete_old_unpublished_jobs():
    """
    Удаляет GenerationJob старше 30 дней, которые не опубликованы в галерею.
    Публикованные работы (имеющие связь с PublicPhoto или PublicVideo) НЕ удаляются.
    """
    from datetime import timedelta
    from django.apps import apps

    cutoff_date = timezone.now() - timedelta(days=30)

    # Получаем модели
    PublicPhoto = apps.get_model('gallery', 'PublicPhoto')
    PublicVideo = apps.get_model('gallery', 'PublicVideo')

    # Находим все работы старше 30 дней
    old_jobs = GenerationJob.objects.filter(
        created_at__lt=cutoff_date
    )

    # Исключаем опубликованные (у которых есть связь с PublicPhoto или PublicVideo)
    published_photo_job_ids = PublicPhoto.objects.filter(
        source_job__isnull=False
    ).values_list('source_job_id', flat=True)

    published_video_job_ids = PublicVideo.objects.filter(
        source_job__isnull=False
    ).values_list('source_job_id', flat=True)

    # Объединяем ID опубликованных работ
    published_job_ids = set(published_photo_job_ids) | set(published_video_job_ids)

    # Фильтруем только неопубликованные
    jobs_to_delete = old_jobs.exclude(pk__in=published_job_ids)

    deleted_count = 0
    for job in jobs_to_delete:
        try:
            # Удаляем файлы из storage
            if job.result_image:
                try:
                    default_storage.delete(job.result_image.name)
                except Exception as e:
                    log.warning(f"Failed to delete image for job {job.pk}: {e}")

            if job.video_source_image:
                try:
                    default_storage.delete(job.video_source_image.name)
                except Exception as e:
                    log.warning(f"Failed to delete video source image for job {job.pk}: {e}")

            # Удаляем запись из БД
            job.delete()
            deleted_count += 1

        except Exception as e:
            log.error(f"Failed to delete job {job.pk}: {e}")

    log.info(f"Deleted {deleted_count} old unpublished generation jobs")
    return deleted_count
