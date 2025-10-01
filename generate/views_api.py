# FILE: generate/views_api.py
from __future__ import annotations
from django.views.decorators.http import require_GET
import json
from typing import Any, Dict
from urllib.parse import quote as urlquote

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.urls import NoReverseMatch, reverse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from dashboard.models import Wallet
from .models import FreeGrant, GenerationJob, Suggestion, SuggestionCategory, AbuseCluster
from .tasks import run_generation_async  # submit в очередь

# утилиты из views (не дублируем)
from .views import _ensure_session_key, _tariffs_url

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
    Ищем/создаём FreeGrant по нескольким идентификаторам.
    Cookie «gid» ставится при отдаче формы (views.new), здесь лишь используем.
    ПРИМЕЧАНИЕ: в нашей модели FreeGrant.ensure_for уже создаёт и привязывает
    AbuseCluster, так что grant.cluster должен быть заполнен.
    """
    _ensure_session_key(request)
    gid = _guest_cookie_id(request)
    grant = FreeGrant.ensure_for(
        fp=_hard_fingerprint(request),
        gid=gid,
        session_key=request.session.session_key,
        ip_hash=_ip_hash(request),
        ua_hash=_ua_hash(request),
        first_ip=(request.META.get("REMOTE_ADDR") or "").strip() or None,
    )
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

    cost = _token_cost()
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

        job = GenerationJob.objects.create(
            user=request.user,
            guest_session_key="",
            guest_gid="",
            guest_fp="",
            cluster=cluster,
            prompt=prompt,
            status=GenerationJob.Status.PENDING,
            error="",
            tokens_spent=tokens_spent,
        )

    # --- гость ----------------------------------------------------------------
    else:
        # Определяем/создаём FreeGrant (внутри также привяжется AbuseCluster)
        grant = _ensure_grant(request)

        # КЛАСТЕР: жёсткий лимит в «обработках» (по умолчанию 3 на кластер)
        cluster = grant.cluster
        if not cluster:
            # на случай старых записей grant без кластера — создадим и привяжем
            try:
                cluster = AbuseCluster.ensure_for(
                    fp=grant.fp,
                    gid=grant.gid or None,
                    ip_hash=grant.ip_hash or None,
                    ua_hash=grant.ua_hash or None,
                )
                grant.cluster = cluster
                grant.save(update_fields=["cluster"])
            except Exception:
                # если что-то пошло не так — не даём обойти лимит: ведём себя как «исчерпан»
                return JsonResponse({"redirect": _tariffs_url()})

        # 1) Пробуем списать 1 «обработку» из кластера (атомарно)
        spent_jobs = 0
        try:
            with transaction.atomic():
                # повторно читаем кластер «под замком»
                c = AbuseCluster.objects.select_for_update().get(pk=cluster.pk)
                left_jobs = max(0, int(c.guest_jobs_limit) - int(c.guest_jobs_used))
                if left_jobs <= 0:
                    return JsonResponse({"redirect": _tariffs_url()})
                c.guest_jobs_used = int(c.guest_jobs_used) + 1
                c.save(update_fields=["guest_jobs_used", "updated_at"])
                spent_jobs = 1
        except Exception:
            # консервативно: если не получилось — считаем лимит недоступным → редирект
            return JsonResponse({"redirect": _tariffs_url()})

        # 2) Теперь резервируем токены FreeGrant (если cost==0, всё равно допускаем)
        if cost <= 0:
            cost = _token_cost()

        with transaction.atomic():
            g = FreeGrant.objects.select_for_update().get(pk=grant.pk)
            left = max(0, int(g.total) - int(g.consumed))
            if left < cost:
                # Нет токенов — вернём «обратный» шаг по кластеру (мягкий откат)
                try:
                    c = AbuseCluster.objects.select_for_update().get(pk=cluster.pk)
                    if spent_jobs > 0 and c.guest_jobs_used > 0:
                        c.guest_jobs_used = int(c.guest_jobs_used) - 1
                        c.save(update_fields=["guest_jobs_used", "updated_at"])
                except Exception:
                    pass
                return JsonResponse({"redirect": _tariffs_url()})
            g.consumed = int(g.consumed) + cost
            g.save(update_fields=["consumed"])

        job = GenerationJob.objects.create(
            user=None,
            guest_session_key=request.session.session_key,
            guest_gid=grant.gid,
            guest_fp=grant.fp,
            cluster=cluster,
            prompt=prompt,
            status=GenerationJob.Status.PENDING,
            error="",
            tokens_spent=cost,
        )

    # Публикуем задачу в очередь Celery (или выполняем синхронно — см. helper)
    queue_name = getattr(settings, "CELERY_QUEUE_SUBMIT", "runware_submit")
    try:
        _enqueue_or_run_sync(
            run_generation_async,
            args=[job.id],
            kwargs={},  # на будущее
            queue=queue_name,
        )
    except (KombuOperationalError, CeleryOperationalError, ConnectionRefusedError):
        # В проде явно сигнализируем, что очередь недоступна
        if not settings.DEBUG:
            return JsonResponse({"ok": False, "error": "queue-unavailable"}, status=503)
        # В DEBUG сюда обычно не попадём (фолбэк уже сработал), но на всякий:
        try:
            run_generation_async.apply(args=[job.id], throw=True)
        except Exception as e:
            return _err(f"local-run-failed: {e}", 500)

    # Фронт ждёт {"id": <job_id>} либо {"redirect": "..."} — используем id
    return JsonResponse({"id": job.id})


# =============================================================================
# API: статус задачи (поллинг)
# =============================================================================

def api_status(request: HttpRequest, job_id: int) -> JsonResponse:
    job = get_object_or_404(GenerationJob, pk=job_id)
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


# =============================================================================
# Webhook от Runware (успех/ошибка провайдера)
# =============================================================================

@csrf_exempt
@require_POST
def runware_webhook(request: HttpRequest) -> HttpResponse:
    """
    На успех — финализируем (tasks._finalize_job_with_url), без повторных списаний.
    На провале — FAILED и рефанд токенов только авторизованному пользователю.
    """
    token_expected = getattr(settings, "RUNWARE_WEBHOOK_TOKEN", "")
    token_get = request.GET.get("token") or request.headers.get("X-Runware-Token") or ""
    if token_expected and token_get != token_expected:
        return HttpResponseForbidden("bad token")

    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return HttpResponseBadRequest("bad json")

    arr = (body or {}).get("data") or []
    if not arr:
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

    # FAILED → фиксируем и рефандим авторизованному пользователю (если были списания)
    if job.status != GenerationJob.Status.FAILED:
        job.status = GenerationJob.Status.FAILED
        job.error = (item.get("error") or item.get("message") or "Generation failed")[:500]
        job.provider_status = item.get("status") or "failed"
        job.provider_payload = item
        job.save(update_fields=["status", "error", "provider_status", "provider_payload"])

        if job.user_id and job.tokens_spent > 0:
            try:
                with transaction.atomic():
                    w = Wallet.objects.select_for_update().get(user_id=job.user_id)
                    w.balance = int(w.balance or 0) + int(job.tokens_spent or 0)
                    w.save(update_fields=["balance"])
            except Exception:
                pass

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

    return _ok(tokens=int(grant.left), gens_left=int(grant.diamonds_left), found=True)
