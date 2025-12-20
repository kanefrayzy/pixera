# FILE: generate/views_api.py
from __future__ import annotations
from django.views.decorators.http import require_GET
import json
from typing import Any, Dict
import os
import requests
from urllib.parse import quote as urlquote

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Q
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.urls import NoReverseMatch, reverse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.cache import cache
from django.utils import timezone
import io
from PIL import Image
import tempfile
import subprocess
import shutil
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from dashboard.models import Wallet
from .models import FreeGrant, GenerationJob, Suggestion, SuggestionCategory, AbuseCluster, ReferenceImage
from .tasks import run_generation_async  # submit в очередь

# утилиты из views (не дублируем)
from .views import _ensure_session_key, _tariffs_url
from .services.translator import translate_prompt_if_needed

# Celery/Kombu исключения для graceful-fallback
from kombu.exceptions import OperationalError as KombuOperationalError
try:
    from celery.exceptions import OperationalError as CeleryOperationalError
except Exception:  # на случай старых версий celery
    class CeleryOperationalError(Exception):
        pass


# =============================================================================
# Helpers
# =============================================================================

def _ok(**extra) -> JsonResponse:
    data = {"ok": True}
    data.update(extra)
    return JsonResponse(data)


def _err(msg: str, code: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": str(msg)}, status=code)


def _b(val, default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _is_staff(user) -> bool:
    return bool(user.is_authenticated and user.is_staff)


def _token_cost() -> int:
    return int(getattr(settings, "TOKEN_COST_PER_GEN", 10))


def _free_for_staff() -> bool:
    return bool(getattr(settings, "FREE_FOR_STAFF", True))


def _login_to_billing_url() -> str:
    try:
        billing = reverse("dashboard:billing")
    except NoReverseMatch:
        billing = "/dashboard/billing/"
    try:
        login = reverse("account_login")
    except NoReverseMatch:
        login = "/accounts/login/"
    return f"{login}?next={urlquote(billing)}"

FP_COOKIE = getattr(settings, "FP_COOKIE_NAME", "aid_fp")
FP_HEADER = getattr(settings, "FP_HEADER_NAME", "X-Device-Fingerprint")
FP_PARAM  = getattr(settings, "FP_PARAM_NAME", "fp")
def _client_fp(request: HttpRequest) -> str:
    """
    «Железный» отпечаток с фронта (canvas/WebGL и т.п.).
    Берём из заголовка, POST-поля или cookie — что первым попадётся.
    Стабилен в инкогнито и при VPN.
    """
    return (
        (request.headers.get(FP_HEADER) or "").strip()
        or (request.POST.get(FP_PARAM) or "").strip()
        or (request.COOKIES.get(FP_COOKIE) or "").strip()
    )

def _ua_hash(request: HttpRequest) -> str:
    """
    ВАЖНО: не включаем Accept-Language — он часто меняется/отсутствует в инкогнито.
    Используем только User-Agent для вспомогательного сигнала.
    """
    ua = (request.META.get("HTTP_USER_AGENT") or "").strip()
    import hashlib
    return hashlib.sha256(ua.encode("utf-8")).hexdigest()

def _ip_hash(request: HttpRequest) -> str:
    ip = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip() or \
         (request.META.get("REMOTE_ADDR") or "")
    if not ip:
        return ""
    import hashlib
    return hashlib.sha256(f"{ip}|{settings.SECRET_KEY}".encode("utf-8")).hexdigest()

def _hard_fingerprint(request: HttpRequest) -> str:
    """
    Главный ключ:
      1) если пришёл «железный» client_fp — используем ТОЛЬКО его (склеенный с SECRET_KEY),
         чтобы он не зависел ни от IP, ни от языка, ни от сессии;
      2) иначе — старый резервный способ (UA + IP).
    """
    import hashlib
    cfp = _client_fp(request)
    if cfp:
        return hashlib.sha256(f"{cfp}|{settings.SECRET_KEY}".encode("utf-8")).hexdigest()
    # fallback для очень старых браузеров/блокировщиков
    raw = f"{_ua_hash(request)}|{_ip_hash(request)}|{settings.SECRET_KEY}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _guest_cookie_id(request: HttpRequest) -> str:
    return request.COOKIES.get("gid") or ""


def _ensure_grant(request: HttpRequest) -> FreeGrant:
    """
    ОБНОВЛЁННАЯ СИСТЕМА: Использует ensure_guest_grant_with_security
    для защиты от Tor/VPN обхода.
    """
    from .security import ensure_guest_grant_with_security

    grant, device, error = ensure_guest_grant_with_security(request)

    if error:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied(error)

    if not grant:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Не удалось получить токены")

    return grant


# --- Celery enqueue helper ----------------------------------------------------

def _enqueue_or_run_sync(task, *, args=None, kwargs=None, queue: str | None = None):
    """
    Пытаемся отправить задачу в Celery. В DEV (DEBUG=True) и/или при настройке
    CELERY_TASK_ALWAYS_EAGER=True — исполняем синхронно (task.apply).

    Если брокер недоступен:
      • DEBUG=True → фолбэк на синхронное выполнение.
      • DEBUG=False → пробрасываем исключение (выше превратим в 503 JSON).
    """
    args = args or ()
    kwargs = kwargs or {}

    # Принудительно «eager»
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) or settings.DEBUG:
        # throw=True — чтобы исключения таска не глотались
        return task.apply(args=args, kwargs=kwargs, throw=True)

    # Обычный путь — очередь
    try:
        return task.apply_async(args=args, kwargs=kwargs, queue=queue)
    except (KombuOperationalError, CeleryOperationalError, ConnectionRefusedError):
        if settings.DEBUG:
            return task.apply(args=args, kwargs=kwargs, throw=True)
        raise


# =============================================================================
# API: создать задачу генерации (резерв токенов + анти-абуз лимит для гостей)
# =============================================================================

@require_POST
def api_submit(request: HttpRequest) -> JsonResponse:
    """
    Создаём задачу и сразу резервируем стоимость:

    • Staff (если FREE_FOR_STAFF=True) — cost=0 (без списаний).
    • Авторизованные — атомарно списываем из Wallet (select_for_update).
    • Гости — СНАЧАЛА списываем «1 обработку» из AbuseCluster (жёсткий лимит),
      затем атомарно увеличиваем consumed у FreeGrant (select_for_update).

    При нехватке средств — {"redirect": "<тарифы>"}.
    """
    prompt = (request.POST.get("prompt") or "").strip()
    if not prompt:
        return _err("Пустой промпт")

    if len(prompt) > 2000:
        return _err("Промпт слишком длинный")

    dangerous_patterns = ['<script', 'javascript:', 'data:', 'vbscript:', 'onload=', 'onerror=']
    prompt_lower = prompt.lower()
    for pattern in dangerous_patterns:
        if pattern in prompt_lower:
            return _err("Недопустимое содержимое в промпте")

    # Переводим промпт на английский если нужно (учитываем флаг с клиента)
    auto_translate_raw = request.POST.get("auto_translate", "1")
    auto_translate = str(auto_translate_raw).strip().lower() in ("1", "true", "on", "yes")
    if auto_translate:
        try:
            translated_prompt = translate_prompt_if_needed(prompt)
            # Сохраняем оригинальный промпт для отображения пользователю
            original_prompt = prompt
            prompt = translated_prompt
        except Exception as e:
            # В случае ошибки перевода, используем оригинальный промпт
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка перевода промпта: {e}")
            original_prompt = prompt
    else:
        # Автоперевод выключен клиентом — используем исходный промпт
        original_prompt = prompt

    # Необязательный выбор модели с фронта
    model_id_in = (request.POST.get("model_id") or "").strip()

    # Читаем количество результатов (по умолчанию 1)
    number_results = 1
    try:
        nr = int(request.POST.get("number_results") or "1")
        number_results = max(1, min(20, nr))  # Ограничиваем 1-20
    except (ValueError, TypeError):
        number_results = 1

    # Переменная стоимости: 15 TOK для FLUX/Seedream, иначе глобальный токен-кост
    special_model = (model_id_in or "").strip().lower() in {"bfl:2@2", "bytedance:5@0"}
    base_cost = 15 if special_model else _token_cost()

    # Умножаем базовую цену на количество результатов
    cost = base_cost * number_results

    is_staff_user = request.user.is_authenticated and (
        request.user.is_staff or request.user.is_superuser
    )
    if _free_for_staff() and is_staff_user:
        cost = 0

    # --- авторизованный пользователь -----------------------------------------
    if request.user.is_authenticated:
        # Подтягиваем возможные гостевые задачи этой же сессии к пользователю
        try:
            GenerationJob.claim_for_user(
                user=request.user,
                session_key=request.session.session_key,
                guest_gid=_guest_cookie_id(request),
                guest_fp=_hard_fingerprint(request),
            )
        except Exception:
            # не мешаем сабмиту из-за фоновой консолидации
            pass

        # По желанию: привяжем кластер к задаче для диагностики
        cluster = None
        try:
            cluster = AbuseCluster.ensure_for(
                fp=_hard_fingerprint(request),
                gid=_guest_cookie_id(request) or None,
                ip_hash=_ip_hash(request) or None,
                ua_hash=_ua_hash(request) or None,
                user_id=request.user.id,
            )
        except Exception:
            cluster = None  # анти-абуз не должен ломать поток

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        tokens_spent = 0

        if cost > 0:
            with transaction.atomic():
                w = Wallet.objects.select_for_update().get(pk=wallet.pk)
                bal = int(w.balance or 0)
                if bal < cost:
                    return JsonResponse({"redirect": _tariffs_url()})
                w.balance = bal - cost
                w.save(update_fields=["balance"])
                tokens_spent = cost

        # Создаем несколько задач согласно number_results
        created_jobs = []
        for i in range(number_results):
            job_kwargs = {
                "user": request.user,
                "guest_session_key": "",
                "guest_gid": "",
                "guest_fp": "",
                "cluster": cluster,
                "prompt": prompt,
                "original_prompt": original_prompt,
                "status": GenerationJob.Status.PENDING,
                "error": "",
                "tokens_spent": base_cost if i == 0 else 0,  # Токены списываем только с первой задачи
            }
            if model_id_in:
                job_kwargs["model_id"] = model_id_in
            job = GenerationJob.objects.create(**job_kwargs)
            created_jobs.append(job)

            # Save reference images if any (up to 5 images) - только для первой задачи
            if i == 0:
                try:
                    reference_images = request.FILES.getlist('reference_images')
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"📸 Received {len(reference_images)} reference images for job {job.pk}")
                    for idx, ref_img in enumerate(reference_images[:5]):  # Max 5 images
                        ref_obj = ReferenceImage.objects.create(
                            job=job,
                            image=ref_img,
                            order=idx
                        )
                        logger.info(f"  ✅ Saved reference image {idx}: {ref_img.name} ({ref_img.size} bytes) -> {ref_obj.pk}")
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"❌ Failed to save reference images: {e}", exc_info=True)

                # Face Retouch (runware:108@22): persist uploaded reference image for special processing
                try:
                    model_effective = (job.model_id or model_id_in or "").strip().lower()
                    if model_effective == "runware:108@22" and "reference_image" in request.FILES:
                        ref_file = request.FILES["reference_image"]
                        if getattr(ref_file, "size", 0) > 15 * 1024 * 1024:
                            return JsonResponse({"ok": False, "error": "Слишком большой файл для ретуши (макс 15MB)"}, status=400)
                        save_path = default_storage.save(f"retouch_refs/{ref_file.name}", ref_file)
                        ref_url = request.build_absolute_uri(default_storage.url(save_path))
                        payload = job.provider_payload or {}
                        if not isinstance(payload, dict):
                            payload = {}
                        payload.update({
                            "retouch_ref_url": ref_url,
                            "retouch_ref_path": save_path,
                            "cfg_scale": (request.POST.get("cfg_scale") or "4"),
                            "scheduler": (request.POST.get("scheduler") or "FlowMatchEulerDiscreteScheduler"),
                            "acceleration": (request.POST.get("acceleration") or "medium"),
                            "retouch_ratio": (request.POST.get("retouch_ratio") or ""),
                            "retouch_width": (request.POST.get("retouch_width") or ""),
                            "retouch_height": (request.POST.get("retouch_height") or ""),
                            "number_results": (request.POST.get("number_results") or ""),
                        })
                        job.provider_payload = payload
                        job.save(update_fields=["provider_payload"])
                except Exception as _e:
                    import logging
                    logging.getLogger(__name__).error(f"Face Retouch payload prepare error: {_e}", exc_info=True)

        # Используем первую задачу как основную для ответа
        job = created_jobs[0]

    # --- гость ----------------------------------------------------------------
    else:
        # Определяем/создаём FreeGrant
        grant = _ensure_grant(request)

        # Создаем или находим кластер для анти-абуза
        cluster = None
        try:
            cluster = AbuseCluster.ensure_for(
                fp=grant.fp,
                gid=grant.gid or None,
                ip_hash=grant.ip_hash or None,
                ua_hash=grant.ua_hash or None,
            )
        except Exception:
            # если что-то пошло не так — не даём обойти лимит: ведём себя как «исчерпан»
            return JsonResponse({"redirect": _tariffs_url()})


        # 2) Теперь резервируем токены FreeGrant (если cost==0, всё равно допускаем)
        if cost <= 0:
            cost = _token_cost()

        with transaction.atomic():
            g = FreeGrant.objects.select_for_update().get(pk=grant.pk)
            left = max(0, int(g.total) - int(g.consumed))
            if left < cost:
                return JsonResponse({"redirect": _tariffs_url()})
            g.consumed = int(g.consumed) + cost
            g.save(update_fields=["consumed"])

        # Создаем несколько задач согласно number_results
        created_jobs = []
        for i in range(number_results):
            job_kwargs = {
                "user": None,
                "guest_session_key": request.session.session_key,
                "guest_gid": grant.gid,
                "guest_fp": grant.fp,
                "cluster": cluster,
                "prompt": prompt,
                "original_prompt": original_prompt,
                "status": GenerationJob.Status.PENDING,
                "error": "",
                "tokens_spent": base_cost if i == 0 else 0,  # Токены списываем только с первой задачи
            }
            if model_id_in:
                job_kwargs["model_id"] = model_id_in
            job = GenerationJob.objects.create(**job_kwargs)
            created_jobs.append(job)

            # Save reference images if any (for guests) - только для первой задачи
            if i == 0:
                try:
                    reference_images = request.FILES.getlist('reference_images')
                    for idx, ref_img in enumerate(reference_images[:5]):  # Max 5 images
                        ReferenceImage.objects.create(
                            job=job,
                            image=ref_img,
                            order=idx
                        )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Failed to save reference images (guest): {e}", exc_info=True)

        # Используем первую задачу как основную для ответа
        job = created_jobs[0]

    # Публикуем все задачи в очередь Celery (или выполняем синхронно — см. helper)
    queue_name = getattr(settings, "CELERY_QUEUE_SUBMIT", "runware_submit")
    for created_job in created_jobs:
        try:
            _enqueue_or_run_sync(
                run_generation_async,
                args=[created_job.id],
                kwargs={},  # на будущее
                queue=queue_name,
            )
        except (KombuOperationalError, CeleryOperationalError, ConnectionRefusedError):
            # В проде явно сигнализируем, что очередь недоступна
            if not settings.DEBUG:
                return JsonResponse({"ok": False, "error": "queue-unavailable"}, status=503)
            # В DEBUG сюда обычно не попадём (фолбэк уже сработал), но на всякий:
            try:
                run_generation_async.apply(args=[created_job.id], throw=True)
            except Exception as e:
                return _err(f"local-run-failed: {e}", 500)

    # Возвращаем ID всех созданных задач для фронтенда
    if len(created_jobs) > 1:
        return JsonResponse({
            "id": created_jobs[0].id,
            "job_ids": [j.id for j in created_jobs]
        })
    else:
        # Обратная совместимость - один результат
        return JsonResponse({"id": job.id})


# =============================================================================
# API: статус задачи (поллинг)
# =============================================================================

def api_status(request: HttpRequest, job_id: int) -> JsonResponse:
    job = get_object_or_404(GenerationJob, pk=job_id)

    # Enforce per-user/per-guest visibility
    owner_ok = False
    try:
        if job.user_id:
            owner_ok = (request.user.is_authenticated and request.user.id == job.user_id)
        else:
            try:
                _ensure_session_key(request)
            except Exception:
                pass
            sk = request.session.session_key or ""
            gid = request.COOKIES.get("gid", "")
            fp = _hard_fingerprint(request)
            owner_ok = (job.guest_session_key == sk) or (job.guest_gid == gid) or (job.guest_fp == fp)
    except Exception:
        owner_ok = False

    if not owner_ok:
        # Hide existence of foreign jobs
        return JsonResponse({"ok": False, "error": "not found"}, status=404)

    resp: Dict[str, Any] = {
        "id": job.id,
        "done": job.status == GenerationJob.Status.DONE,
        "failed": job.status == GenerationJob.Status.FAILED,
        "error": job.error or "",
        "provider_status": getattr(job, "provider_status", "") or "",
    }
    if job.result_image:
        try:
            resp["image"] = {"url": job.result_image.url}
        except Exception:
            resp["image"] = None
    else:
        resp["image"] = None
    return JsonResponse(resp)


@require_POST
def job_persist(request: HttpRequest, pk: int) -> JsonResponse:
    """
    Mark a GenerationJob as 'persisted' so it appears in My Jobs/Profile.
    - Allowed for owner (user) or the same guest (session_key/gid/fp).
    - If the requester is authenticated and the job has no user yet, attach it to the user.
    """
    job = get_object_or_404(GenerationJob, pk=pk)

    # Owner/guest-ownership check (same rules as api_status)
    owner_ok = False
    try:
        if job.user_id:
            owner_ok = (request.user.is_authenticated and request.user.id == job.user_id)
        else:
            try:
                _ensure_session_key(request)
            except Exception:
                pass
            sk = request.session.session_key or ""
            gid = request.COOKIES.get("gid", "")
            fp = _hard_fingerprint(request)
            owner_ok = (job.guest_session_key == sk) or (job.guest_gid == gid) or (job.guest_fp == fp)
    except Exception:
        owner_ok = False

    if not owner_ok:
        # Hide existence of foreign jobs
        return JsonResponse({"ok": False, "error": "not found"}, status=404)

    updates = []

    # Attach to user if authenticated and current job is guest-owned
    if request.user.is_authenticated and not job.user_id:
        job.user_id = request.user.id
        updates.extend(["user"])
        # clear guest markers for cleanliness
        if job.guest_session_key:
            job.guest_session_key = ""
            updates.append("guest_session_key")
        if job.guest_gid:
            job.guest_gid = ""
            updates.append("guest_gid")
        if job.guest_fp:
            job.guest_fp = ""
            updates.append("guest_fp")

    if not getattr(job, "persisted", False):
        job.persisted = True
        updates.append("persisted")

    if updates:
        try:
            job.save(update_fields=updates)
        except Exception:
            # fallback to full save in rare cases (e.g., different backends)
            job.save()

    # Prepare compressed, persisted asset and immediate download link
    download_url: str | None = None
    download_name: str | None = None
    content_type: str | None = None

    try:
        # Ensure peristent folders by date
        now = timezone.now()
        img_dir = f"persist/images/{now:%Y/%m}/"
        vid_dir = f"persist/videos/{now:%Y/%m}/"

        if (job.generation_type or "image") == "image":
            # 1) Obtain source bytes
            src_bytes: bytes | None = None
            # Prefer local stored result image
            if getattr(job, "result_image", None) and getattr(job.result_image, "name", ""):
                try:
                    with default_storage.open(job.result_image.name, "rb") as f:
                        src_bytes = f.read()
                except Exception:
                    src_bytes = None
            # Try in-memory cache as fallback (see tasks._img_key)
            if src_bytes is None:
                try:
                    cached = cache.get(f"genimg:{job.pk}")
                    if isinstance(cached, (bytes, bytearray)):
                        src_bytes = bytes(cached)
                except Exception:
                    src_bytes = None
            # As a last resort try external cached-url then download
            if src_bytes is None:
                try:
                    cached_url = cache.get(f"genimgurl:{job.pk}")
                    if cached_url:
                        r = requests.get(cached_url, timeout=20)
                        if r.ok and r.content:
                            src_bytes = r.content
                except Exception:
                    pass

            if src_bytes:
                # 2) Compress to WEBP (max compression with reasonable quality)
                try:
                    im = Image.open(io.BytesIO(src_bytes))
                    if im.mode not in ("RGB", "L"):
                        im = im.convert("RGB")
                    # Optional downscale very large to 2048px max side
                    try:
                        w, h = im.size
                        max_side = 2048
                        if max(w, h) > max_side:
                            if w >= h:
                                nw = max_side
                                nh = max(1, int(h * (max_side / float(w))))
                            else:
                                nh = max_side
                                nw = max(1, int(w * (max_side / float(h))))
                            im = im.resize((int(nw), int(nh)), Image.LANCZOS)
                    except Exception:
                        pass
                    buf = io.BytesIO()
                    # q=75 is a good "max compression" compromise; method=6 for best effort
                    im.save(buf, format="WEBP", quality=75, method=6)
                    buf.seek(0)
                    fname = f"{img_dir}job_{job.pk}.webp"
                    default_storage.save(fname, ContentFile(buf.read()))
                    # Ensure job points to durable persisted file
                    try:
                        job.result_image.name = fname
                        job.save(update_fields=["result_image"])
                    except Exception:
                        pass
                    download_url = default_storage.url(fname)
                    download_name = f"image_{job.pk}.webp"
                    content_type = "image/webp"
                except Exception:
                    # Fallback: store original as-is
                    try:
                        fname = f"{img_dir}job_{job.pk}.jpg"
                        default_storage.save(fname, ContentFile(src_bytes))
                        # Ensure job points to durable persisted file
                        try:
                            job.result_image.name = fname
                            job.save(update_fields=["result_image"])
                        except Exception:
                            pass
                        download_url = default_storage.url(fname)
                        download_name = f"image_{job.pk}.jpg"
                        content_type = "image/jpeg"
                    except Exception:
                        pass

        else:
            # VIDEO: download, compress with ffmpeg if available, persist to media
            src_url = (job.result_video_url or "").strip()
            tmp_in = None
            tmp_out = None
            try:
                if not src_url:
                    raise RuntimeError("empty video url")
                # Download to temp file
                r = requests.get(src_url, timeout=40, stream=True)
                r.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as fin:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            fin.write(chunk)
                    tmp_in = fin.name
                # Prepare output temp file
                tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                # Detect ffmpeg binary
                ffmpeg_bin = shutil.which("ffmpeg") or os.getenv("FFMPEG_BIN", "ffmpeg")
                # Run compression: H.264 CRF 28, faststart, keep audio AAC 128k
                try:
                    subprocess.run(
                        [
                            ffmpeg_bin,
                            "-y",
                            "-i",
                            tmp_in,
                            "-c:v",
                            "libx264",
                            "-preset",
                            "veryfast",
                            "-crf",
                            "28",
                            "-movflags",
                            "+faststart",
                            "-c:a",
                            "aac",
                            "-b:a",
                            "128k",
                            tmp_out,
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )
                    # Persist compressed
                    with open(tmp_out, "rb") as f:
                        fname = f"{vid_dir}job_{job.pk}.mp4"
                        default_storage.save(fname, ContentFile(f.read()))
                    persisted_url = default_storage.url(fname)
                    download_url = persisted_url
                    download_name = f"video_{job.pk}.mp4"
                    content_type = "video/mp4"
                    # Optionally update job to local URL for durability
                    try:
                        job.result_video_url = persisted_url
                        job.save(update_fields=["result_video_url"])
                    except Exception:
                        pass
                except Exception:
                    # Fallback: store original (uncompressed) to media
                    if tmp_in and os.path.exists(tmp_in):
                        with open(tmp_in, "rb") as f:
                            fname = f"{vid_dir}job_{job.pk}.mp4"
                            default_storage.save(fname, ContentFile(f.read()))
                        persisted_url = default_storage.url(fname)
                        download_url = persisted_url
                        download_name = f"video_{job.pk}.mp4"
                        content_type = "video/mp4"
                        try:
                            job.result_video_url = persisted_url
                            job.save(update_fields=["result_video_url"])
                        except Exception:
                            pass
            finally:
                # Cleanup temp files
                try:
                    if tmp_in and os.path.exists(tmp_in):
                        os.unlink(tmp_in)
                except Exception:
                    pass
                try:
                    if tmp_out and os.path.exists(tmp_out):
                        os.unlink(tmp_out)
                except Exception:
                    pass
    except Exception:
        # Silently ignore compression errors; user still gets redirect
        download_url = download_url or None

    try:
        my_jobs_url = reverse("dashboard:my_jobs")
    except NoReverseMatch:
        my_jobs_url = "/dashboard/my-jobs"

    payload = {"ok": True, "persisted": True, "redirect": my_jobs_url}
    if download_url:
        payload.update({"download_url": download_url, "filename": download_name, "content_type": content_type})
    return JsonResponse(payload)


# =============================================================================
# Webhook от Runware (успех/ошибка провайдера)
# =============================================================================

@csrf_exempt
def runware_webhook(request: HttpRequest) -> HttpResponse:
    """
    На успех — финализируем (tasks._finalize_job_with_url), без повторных списаний.
    На провале — FAILED и рефанд токенов только авторизованному пользователю.
    """
    # Проверяем только POST метод
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)
    import logging
    logger = logging.getLogger(__name__)

    token_expected = getattr(settings, "RUNWARE_WEBHOOK_TOKEN", "")
    token_get = request.GET.get("token") or request.headers.get("X-Runware-Token") or ""
    if token_expected and token_get != token_expected:
        logger.warning(f"Invalid webhook token from {request.META.get('REMOTE_ADDR')}")
        return HttpResponseForbidden("bad token")

    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Webhook JSON decode error: {e}")
        return HttpResponseBadRequest("bad json")

    arr = (body or {}).get("data") or []
    if not arr:
        logger.warning("Webhook received empty data array")
        return HttpResponse("no data")

    item = arr[0] or {}
    task_uuid = item.get("taskUUID")
    image_url = item.get("imageURL") or item.get("url")
    status = (item.get("status") or "").lower()
    if not task_uuid:
        return HttpResponse("skip")

    job = GenerationJob.objects.filter(provider_task_uuid=task_uuid).first()
    if not job:
        return HttpResponse("job not found yet")

    from .tasks import _finalize_job_with_url as _finalize_success

    # SUCCESS
    if image_url and (status in ("success", "succeeded", "")):
        if job.status != GenerationJob.Status.DONE:
            _finalize_success(job, image_url)
        return HttpResponse("ok")

    if job.status != GenerationJob.Status.FAILED:
        job.status = GenerationJob.Status.FAILED
        job.error = (item.get("error") or item.get("message") or "Generation failed")[:500]
        job.provider_status = item.get("status") or "failed"
        job.provider_payload = item
        job.save(update_fields=["status", "error", "provider_status", "provider_payload"])

        # Используем рефанд
        from .tasks import _refund_if_needed
        _refund_if_needed(job)

    return HttpResponse("ok")


# =============================================================================
# API (STAFF): управление категориями подсказок
# =============================================================================

@login_required
@user_passes_test(_is_staff)
@require_POST
@transaction.atomic
def cat_create(request: HttpRequest) -> JsonResponse:
    """
    Создать категорию подсказок.
    POST: name, [slug], [is_active=1|0], [position|order]
    """
    name = (request.POST.get("name") or "").strip()
    slug_in = (request.POST.get("slug") or "").strip()
    is_active = _b(request.POST.get("is_active"), True)
    position = request.POST.get("position") or request.POST.get("order") or "0"

    if not name:
        return _err("name is required")

    base = slugify(slug_in or name) or "cat"
    slug_val = base
    i = 2
    while SuggestionCategory.objects.filter(slug=slug_val).exists():
        slug_val = f"{base}-{i}"
        i += 1

    cat_kwargs = {"name": name, "slug": slug_val, "is_active": is_active}
    try:
        pos = int(position)
        if hasattr(SuggestionCategory, "order"):
            cat_kwargs["order"] = pos
        elif hasattr(SuggestionCategory, "position"):
            cat_kwargs["position"] = pos
    except ValueError:
        pass

    cat = SuggestionCategory.objects.create(**cat_kwargs)
    return _ok(id=cat.pk, name=cat.name, slug=cat.slug, is_active=cat.is_active)


@login_required
@user_passes_test(_is_staff)
@require_POST
@transaction.atomic
def cat_update(request: HttpRequest, pk: int) -> JsonResponse:
    """
    Обновить категорию.
    POST: [name], [slug], [is_active=1|0], [position|order]
    """
    try:
        cat = SuggestionCategory.objects.get(pk=pk)
    except SuggestionCategory.DoesNotExist:
        return _err("category not found", 404)

    name = request.POST.get("name")
    slug_in = request.POST.get("slug")
    is_active = request.POST.get("is_active")
    position = request.POST.get("position") or request.POST.get("order")

    if name is not None:
        cat.name = name.strip() or cat.name

    if slug_in is not None:
        new_slug = slugify(slug_in.strip() or cat.name) or cat.slug
        if new_slug != cat.slug and SuggestionCategory.objects.filter(slug=new_slug).exclude(pk=cat.pk).exists():
            return _err("slug already exists")
        cat.slug = new_slug

    if is_active is not None:
        cat.is_active = _b(is_active, cat.is_active)

    if position is not None:
        try:
            val = int(position)
            if hasattr(cat, "order"):
                cat.order = val
            elif hasattr(cat, "position"):
                cat.position = val
        except ValueError:
            pass

    update_fields = ["name", "slug", "is_active"]
    if hasattr(cat, "order"):
        update_fields.append("order")
    if hasattr(cat, "position"):
        update_fields.append("position")

    cat.save(update_fields=update_fields)
    return _ok(id=cat.pk)


@login_required
@user_passes_test(_is_staff)
@require_POST
@transaction.atomic
def cat_delete(request: HttpRequest, pk: int) -> JsonResponse:
    """
    Удалить категорию. Подсказки остаются «без категории».
    """
    try:
        cat = SuggestionCategory.objects.get(pk=pk)
    except SuggestionCategory.DoesNotExist:
        return _err("category not found", 404)

    Suggestion.objects.filter(category=cat).update(category=None)
    cat.delete()
    return _ok()



@require_GET
def guest_balance(request: HttpRequest) -> JsonResponse:
    """
    Вернуть актуальный гостевой остаток по СТАБИЛЬНОМУ fp.
    Ничего не создаёт (если записи нет — возвращает need_fp/none).
    """
    if request.user.is_authenticated:
        return _ok(tokens=0, gens_left=0, auth=True)

    # нужен стабильный fp (из заголовка/куки, см. base.js)
    fp = (request.headers.get(getattr(settings, "FP_HEADER_NAME", "X-Device-Fingerprint")) or
          request.COOKIES.get(getattr(settings, "FP_COOKIE_NAME", "aid_fp")) or "").strip()
    if not fp:
        return _ok(tokens=None, gens_left=None, need_fp=True)

    # тот же «жёсткий» хеш, что и в _hard_fingerprint
    import hashlib
    hard_fp = hashlib.sha256(f"{fp}|{settings.SECRET_KEY}".encode("utf-8")).hexdigest()

    grant = FreeGrant.objects.filter(fp=hard_fp).first()
    if not grant:
        return _ok(tokens=None, gens_left=None, found=False)

    # Переход на модель "только токены": без учёта лимита обработок на кластер
    # (анти-абуз идентификаторы сохраняем в другом месте; здесь показываем только баланс)

    # Рассчитываем количество обработок из токенов
    tokens_left = int(grant.left)
    cost = _token_cost()
    gens_left = (tokens_left // cost) if cost > 0 else 0

    return _ok(tokens=tokens_left, gens_left=gens_left, found=True)


@require_POST
def prompt_ai(request: HttpRequest) -> JsonResponse:
    """
    Generate a professional image/video prompt from a short idea using X.AI Grok.
    Body (JSON): { "idea": "text", "mode": "image" | "video" }
    Returns: { "ok": true, "text": "..." } or { "ok": false, "error": "..." }
    """
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"ok": False, "error": "bad json"}, status=400)

    idea = (data.get("idea") or "").strip()
    mode = (data.get("mode") or "image").strip().lower()
    if not idea:
        return JsonResponse({"ok": False, "error": "empty idea"}, status=400)

    # Translate idea to English if needed (same logic as main prompt path)
    try:
        idea_en = translate_prompt_if_needed(idea)
    except Exception:
        idea_en = idea

    api_key = os.getenv("GROK_API_KEY") or ""
    if not api_key:
        return JsonResponse({"ok": False, "error": "server not configured"}, status=500)

    # System instruction: always convert short idea into a single professional prompt
    is_video = (mode == "video")
    system_prompt = (
        "You are a prompt engineering assistant. Convert the user's short idea into a single, concise, professional prompt for "
        + ("video" if is_video else "image")
        + " generation. Write in English only. Include subject, composition, style, lighting, and "
        + ("cinematography and camera movement cues" if is_video else "camera/lens hints if useful")
        + ". Prefer comma-separated tags. Avoid meta text, explanations, or quotes. Output only the prompt."
    )

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": idea_en},
        ],
        "model": "grok-4-fast-reasoning",
        "stream": False,
        "temperature": 0
    }

    try:
        resp = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
    except requests.RequestException:
        return JsonResponse({"ok": False, "error": "network error"}, status=502)

    try:
        j = resp.json()
    except Exception:
        return JsonResponse({"ok": False, "error": "bad response"}, status=502)

    if resp.status_code >= 400:
        err_msg = ""
        if isinstance(j, dict):
            err = j.get("error")
            if isinstance(err, dict):
                err_msg = err.get("message") or ""
            elif isinstance(err, str):
                err_msg = err
        eml = (err_msg or "").lower()
        # Strict model policy: only grok-4-fast-reasoning, no fallbacks, no local stubs
        if resp.status_code == 402 or "credit" in eml or "credits" in eml or "balance" in eml:
            return JsonResponse({"ok": False, "error": "no_credits"}, status=402)
        return JsonResponse({"ok": False, "error": err_msg or "upstream error"}, status=resp.status_code)

    text = ""
    try:
        choices = j.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            text = (message.get("content") or "").strip()
    except Exception:
        text = ""

    if not text:
        return JsonResponse({"ok": False, "error": "empty completion"}, status=502)

    return JsonResponse({"ok": True, "text": text})

@require_GET
def api_last_pending(request: HttpRequest) -> JsonResponse:
    """
    Вернуть последний незавершённый (PENDING/RUNNING) job генерации изображений
    для текущего пользователя или гостя (session_key/gid/fp).
    ВАЖНО: Используется только для восстановления после перезагрузки страницы.
    """
    try:
        qs = GenerationJob.objects.filter(
            generation_type='image',
            status__in=[GenerationJob.Status.PENDING, GenerationJob.Status.RUNNING],
        )
        if request.user.is_authenticated:
            qs = qs.filter(user=request.user)
        else:
            # Совпадение по гостевым идентификаторам
            try:
                _ensure_session_key(request)
            except Exception:
                pass
            sk = request.session.session_key or ''
            gid = request.COOKIES.get("gid", "")
            # Жёсткий fp — как в api_submit/_ensure_grant
            fp = _hard_fingerprint(request)
            qs = qs.filter(Q(guest_session_key=sk) | Q(guest_gid=gid) | Q(guest_fp=fp))

        job = qs.order_by('-created_at').first()
        if job:
            return JsonResponse({"success": True, "job_id": job.id, "status": "found"})
        return JsonResponse({"success": True, "job_id": None, "status": "none"})
    except Exception as e:
        # Не падаем — просто нет восстановления
        return JsonResponse({"success": False, "error": "internal"}, status=500)


@require_GET
def api_completed_jobs(request: HttpRequest) -> JsonResponse:
    """
    Вернуть список ТОЛЬКО завершённых (DONE) генераций для текущего пользователя/гостя.
    Используется для отображения в очереди - показываем только готовые результаты.
    """
    try:
        # Фильтруем только завершенные задачи
        qs = GenerationJob.objects.filter(
            status=GenerationJob.Status.DONE,
        ).filter(
            (Q(result_image__isnull=False) & ~Q(result_image__exact='')) |
            (Q(result_video_url__isnull=False) & ~Q(result_video_url__exact=''))
        )

        # Дополнительная фильтрация по типу медиа, если указано ?type=image|video
        req_type = (request.GET.get('type') or '').strip().lower()
        if req_type in ('image', 'video'):
            qs = qs.filter(generation_type=req_type)

        if request.user.is_authenticated:
            qs = qs.filter(user=request.user)
        else:
            # Совпадение по гостевым идентификаторам
            try:
                _ensure_session_key(request)
            except Exception:
                pass
            sk = request.session.session_key or ''
            gid = request.COOKIES.get("gid", "")
            fp = _hard_fingerprint(request)
            qs = qs.filter(Q(guest_session_key=sk) | Q(guest_gid=gid) | Q(guest_fp=fp))

        # Берем последние 24 завершенных задачи
        jobs = qs.order_by('-created_at')[:24]

        results = []
        for job in jobs:
            item = {
                'job_id': job.id,
                'status': 'done',
                'generation_type': job.generation_type or 'image',
                'created_at': job.created_at.isoformat() if job.created_at else None,
            }

            # Добавляем URL результата
            if job.generation_type == 'video' and job.result_video_url:
                item['video_url'] = job.result_video_url
            elif job.result_image:
                try:
                    item['image_url'] = job.result_image.url
                except Exception:
                    pass

            results.append(item)

        return JsonResponse({"success": True, "jobs": results})
    except Exception as e:
        return JsonResponse({"success": False, "error": "internal"}, status=500)
