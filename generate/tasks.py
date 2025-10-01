from __future__ import annotations

import io
import logging
import time
from typing import Optional

import requests
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from dashboard.models import Wallet
from .models import GenerationJob

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

DEMO_IF_UNAUTHORIZED = bool(getattr(settings, "RUNWARE_DEMO_IF_UNAUTHORIZED", True))

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
def _auth_headers() -> dict:
    key = getattr(settings, "RUNWARE_API_KEY", "") or ""
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
    api = getattr(settings, "RUNWARE_API_URL", "https://api.runware.ai/v1").rstrip("/")
    payload = {
        "model": model_id,
        "prompt": prompt,
        "width": width,
        "height": height,
        # разумные дефолты
        "steps": 28,
        "cfg_scale": 7.0,
    }
    r = requests.post(f"{api}/images/generate", json=payload, headers=_auth_headers(), timeout=60)
    if r.status_code == 401:
        raise requests.HTTPError("401 Unauthorized from Runware")
    r.raise_for_status()
    data = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
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
    job.result_image.save(f"generated/{job.pk}.{ext}", ContentFile(content), save=False)
    job.status = GenerationJob.Status.DONE
    job.error = ""
    _safe_set(job, "provider_status", "success")
    job.save(update_fields=_safe_fields(job, ["status", "error", "result_image", "provider_status"]))

def _demo_render(job: GenerationJob, width: int = FALLBACK_WIDTH, height: int = FALLBACK_HEIGHT) -> None:
    """Создаём простую PNG-картинку с текстом промпта — для DEV/демо."""
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
    txt = (job.prompt or "").strip() or "AI Gallery"
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

def _refund_if_needed(job: GenerationJob) -> None:
    """Рефандим токены только авторизованному пользователю, если было списание."""
    if not job.user_id:
        return
    spent = int(getattr(job, "tokens_spent", 0) or 0)
    if spent <= 0:
        return
    try:
        with transaction.atomic():
            w = Wallet.objects.select_for_update().get(user_id=job.user_id)
            w.balance = int(w.balance or 0) + spent
            w.save(update_fields=["balance"])
    except Exception:
        log.exception("Refund failed for job %s (user %s, spent=%s)", job.pk, job.user_id, spent)

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
def run_generation_async(self, job_id: int) -> None:
    job = GenerationJob.objects.get(pk=job_id)
    if job.status in (GenerationJob.Status.DONE, GenerationJob.Status.RUNNING):
        return

    job.status = GenerationJob.Status.RUNNING
    job.error = ""
    _safe_set(job, "provider_status", "starting")
    job.save(update_fields=_safe_fields(job, ["status", "error", "provider_status"]))

    model_id = job.model_id or getattr(settings, "RUNWARE_DEFAULT_MODEL", "runware:101@1")
    force_sync = bool(getattr(settings, "RUNWARE_FORCE_SYNC", True))

    # === SYNC режим (локальная отладка/без брокера) ===========================
    if force_sync:
        try:
            # 1) Предпочитаем официальный клиент, если есть
            if rw is not None:
                url = rw.submit_image_inference_sync(
                    prompt=job.prompt,
                    model_id=model_id,
                    width=1024, height=1024, steps=28, cfg_scale=7.0,
                    scheduler=None,
                )
            else:
                url = _submit_sync_direct(job.prompt, model_id, width=1024, height=1024)

            _finalize_job_with_url(job, url)
            return

        except Exception as e:
            msg = str(e)
            unauthorized = ("401" in msg) or ("Unauthorized" in msg)
            if unauthorized and DEMO_IF_UNAUTHORIZED:
                log.warning("Runware 401 → DEMO render for job %s", job.pk)
                _demo_render(job)
                return

            job.status = GenerationJob.Status.FAILED
            job.error = (f"sync failed: {msg}")[:300]
            job.save(update_fields=_safe_fields(job, ["status", "error"]))
            _refund_if_needed(job)
            return

    # === ASYNC режим (webhook + polling) ======================================
    try:
        base = (getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
        token = getattr(settings, "RUNWARE_WEBHOOK_TOKEN", "")
        webhook = f"{base}/generate/api/runware/webhook/?token={token}" if (base and token) else None

        if rw is not None:
            task_uuid = rw.submit_image_inference_async(
                prompt=job.prompt,
                model_id=model_id,
                width=1024, height=1024, steps=28, cfg_scale=7.0,
                scheduler=None,
                webhook_url=webhook,
            )
        else:
            # Если нет клиента, принудительно используем синхронный путь
            url = _submit_sync_direct(job.prompt, model_id, width=1024, height=1024)
            _finalize_job_with_url(job, url)
            return

        _safe_set(job, "provider_task_uuid", task_uuid)
        _safe_set(job, "provider_status", "queued")
        job.save(update_fields=_safe_fields(job, ["provider_task_uuid", "provider_status"]))

        poll_runware_result.apply_async(args=[job.id, 1], countdown=FIRST_POLL_DELAY, queue=RUNWARE_QUEUE)

    except Exception as e:
        msg = str(e)
        unauthorized = ("401" in msg) or ("Unauthorized" in msg)
        if unauthorized and DEMO_IF_UNAUTHORIZED:
            log.warning("Runware 401 (async submit) → DEMО render for job %s", job.pk)
            _demo_render(job)
            return

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
    job.save(update_fields=_safe_fields(job, ["provider_status", "provider_payload", "last_polled_at"]))

    # «зависло» → принудительный sync-fallback/DEMO
    if hasattr(rw, "is_processing") and rw.is_processing(status):
        age_sec = (timezone.now() - job.created_at).total_seconds()
        if age_sec >= STUCK_TIMEOUT_SEC:
            try:
                log.warning("Job %s stuck for %.1fs → sync fallback", job.pk, age_sec)
                if rw is not None:
                    fallback_url = rw.submit_image_inference_sync(
                        prompt=job.prompt,
                        model_id=job.model_id or getattr(settings, "RUNWARE_DEFAULT_MODEL", "runware:101@1"),
                        width=FALLBACK_WIDTH, height=FALLBACK_HEIGHT,
                        steps=24, cfg_scale=7.0, scheduler=None,
                    )
                    _finalize_job_with_url(job, fallback_url)
                else:
                    _demo_render(job, width=FALLBACK_WIDTH, height=FALLBACK_HEIGHT)
                return
            except Exception as e:
                msg = str(e)
                if (("401" in msg) or ("Unauthorized" in msg)) and DEMO_IF_UNAUTHORIZED:
                    _demo_render(job, width=FALLBACK_WIDTH, height=FALLBACK_HEIGHT)
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
    poll_runware_result.apply_async(args=[job.id, attempt + 1], countdown=next_in, queue=RUNWARE_QUEUE)

# ── Финализация по внешнему URL ───────────────────────────────────────────────
def _finalize_job_with_url(job: GenerationJob, image_url: str) -> None:
    """Скачиваем картинку; если CDN падает — кэшируем внешний URL и считаем DONE."""
    if job.status == GenerationJob.Status.DONE:
        return

    timeout = int(getattr(settings, "RUNWARE_DOWNLOAD_TIMEOUT", 300))
    headers = {"User-Agent": "AI-Gallery/1.0 (+local)", "Accept": "image/*,*/*;q=0.8"}

    content: Optional[bytes] = None
    last_err: Optional[Exception] = None

    for attempt in range(3):
        try:
            r = requests.get(image_url, timeout=timeout, headers=headers, allow_redirects=True)
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
        job.result_image.save(f"generated/{job.pk}.jpg", ContentFile(content), save=False)
    else:
        cache.set(_img_url_key(job.pk), image_url, timeout=CACHE_TTL)
        log.warning("Job %s: download failed, serving external URL instead. err=%s", job.pk, last_err)

    job.status = GenerationJob.Status.DONE
    job.error = ""
    _safe_set(job, "provider_status", "success")
    job.save(update_fields=_safe_fields(job, ["status", "error", "result_image", "provider_status"]))
