# FILE: generate/views.py
from __future__ import annotations

import hashlib
import io
import logging
from typing import Tuple, Dict, List, Optional
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import connection, transaction, utils as db_utils
from django.db.models import Q
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods, require_POST

from dashboard.models import Wallet
from .models import (
    GenerationJob,
    Suggestion,
    FreeGrant,
    SuggestionCategory,
    ShowcaseCategory,
    ShowcaseImage,
)

log = logging.getLogger(__name__)

# --- тарифы / стоимость ---
TOKEN_COST = int(getattr(settings, "TOKEN_COST_PER_GEN", 10))
FREE_FOR_STAFF = bool(getattr(settings, "FREE_FOR_STAFF", True))
GUEST_INITIAL_TOKENS = int(getattr(settings, "GUEST_INITIAL_TOKENS", 30))

# имя cookie с device-fp (если фронт его ставит)
FP_COOKIE_NAME = getattr(settings, "FP_COOKIE_NAME", "aid_fp")


# =======================
#       helpers
# =======================
def _ensure_session_key(request: HttpRequest) -> str:
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _tariffs_url() -> str:
    for name in ("dashboard:tariffs", "dashboard:billing"):
        try:
            return reverse(name)
        except NoReverseMatch:
            continue
    return "/dashboard/tariffs/"


def _job_slug(job: GenerationJob) -> str:
    """Создает безопасный slug из промпта с поддержкой кириллицы."""
    base = (job.prompt or "").strip() or "job"

    # Попробуем стандартный slugify
    s = slugify(base, allow_unicode=True)

    # Если пустой (может случиться с некоторыми символами), используем транслитерацию
    if not s:
        # Простая транслитерация основных кириллических символов
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            ' ': '-', '_': '-'
        }

        import re
        # Приводим к нижнему регистру и транслитерируем
        text = base.lower()
        transliterated = ''
        for char in text:
            transliterated += translit_map.get(char, char)

        # Удаляем недопустимые символы и создаем slug
        s = re.sub(r'[^a-zA-Z0-9\-_]', '', transliterated)
        s = re.sub(r'[-_]+', '-', s)  # Убираем повторяющиеся дефисы
        s = s.strip('-')  # Убираем дефисы в начале и конце

        # Если всё равно пустой, используем fallback
        if not s:
            s = "job"

    return s[:60]


def _ua_hash(request: HttpRequest) -> str:
    ua = (request.META.get("HTTP_USER_AGENT") or "").strip()
    al = (request.META.get("HTTP_ACCEPT_LANGUAGE") or "").strip()
    raw = f"{ua}|{al}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _ip_hash(request: HttpRequest) -> str:
    ip = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip() or (
        request.META.get("REMOTE_ADDR") or ""
    )
    raw = f"{ip}|{settings.SECRET_KEY}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest() if ip else ""


def _hard_fingerprint(request: HttpRequest) -> str:
    # Стабильный отпечаток на стороне сервера (инкогнито не сбивает),
    # но не используем для СОЗДАНИЯ гранта — только для поиска/склейки.
    raw = f"{_ua_hash(request)}|{_ip_hash(request)}|{settings.SECRET_KEY}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _guest_cookie_id(request: HttpRequest) -> Optional[str]:
    # Старый гостевой идентификатор браузера
    return request.COOKIES.get("gid") or None


def _has_field(model, name: str) -> bool:
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False


def _get_fp_from_request(request: HttpRequest) -> str:
    """
    Берём «мягкий» fp от клиента (cookie/заголовок/проставленный middleware'ом).
    Без него новый грант НЕ СОЗДАЁМ (защита от инкогнито-бонуса).
    """
    # 1) middleware мог положить request.fp
    fp = getattr(request, "fp", "") or ""
    if fp:
        return fp.strip()

    # 2) cookie с фронта
    fp = (request.COOKIES.get(FP_COOKIE_NAME) or "").strip()
    if fp:
        return fp

    # 3) заголовок (если фронт его шлёт)
    hdr = getattr(settings, "FP_HEADER_NAME", "X-Device-Fingerprint")
    fp = (request.META.get(f"HTTP_{hdr.upper().replace('-', '_')}", "") or "").strip()
    return fp


def _find_grant_only(
    *,
    fp: str,
    gid: str,
    session_key: str,
    ua_hash: str,
    ip_hash: str,
    first_ip: Optional[str],
) -> Optional[FreeGrant]:
    """
    Только ПОИСК существующего FreeGrant без создания.
    Ищем по: fp -> gid -> session_key -> (ua_hash+ip_hash).
    Любые отсутствующие поля пропускаем.
    """
    fields = {f.attname for f in FreeGrant._meta.concrete_fields}

    def first(q):
        return FreeGrant.objects.filter(**{k: v for k, v in q.items() if v}).first()

    # 1) fp
    if "fp" in fields and fp:
        obj = first({"fp": fp})
        if obj:
            return obj

    # 2) gid
    if "gid" in fields and gid:
        obj = first({"gid": gid})
        if obj:
            return obj

    # 3) session_key
    if "session_key" in fields and session_key:
        obj = first({"session_key": session_key})
        if obj:
            return obj

    # 4) ua+ip
    if "ua_hash" in fields and "ip_hash" in fields and ua_hash and ip_hash:
        obj = first({"ua_hash": ua_hash, "ip_hash": ip_hash})
        if obj:
            return obj

    return None


def _create_grant_if_fp(
    *,
    fp: str,
    gid: str,
    session_key: str,
    ua_hash: str,
    ip_hash: str,
    first_ip: Optional[str],
) -> Optional[FreeGrant]:
    """
    Создаём НОВЫЙ грант ТОЛЬКО если есть осмысленный fp (cookie/hdr/middleware).
    Поля, которых нет в модели, не трогаем.
    """
    fp = (fp or "").strip()
    if not fp:
        return None  # защита: без fp — не создаём

    fields = {f.attname for f in FreeGrant._meta.concrete_fields}
    defaults: Dict[str, object] = {}

    if "total" in fields:
        defaults["total"] = int(getattr(settings, "GUEST_INITIAL_TOKENS", GUEST_INITIAL_TOKENS))
    if "consumed" in fields:
        defaults["consumed"] = 0
    if "first_ip" in fields and first_ip:
        defaults["first_ip"] = first_ip
    if "session_key" in fields and session_key:
        defaults["session_key"] = session_key
    if "ip_hash" in fields and ip_hash:
        defaults["ip_hash"] = ip_hash
    if "ua_hash" in fields and ua_hash:
        defaults["ua_hash"] = ua_hash
    if "gid" in fields and gid:
        defaults["gid"] = gid
    if "fp" in fields:
        defaults["fp"] = fp

    try:
        with transaction.atomic():
            obj = FreeGrant.objects.create(**defaults)
            return obj
    except Exception:
        return None


def _ensure_grant(request: HttpRequest) -> Tuple[Optional[FreeGrant], Optional[str]]:
    """
    Создаёт/находит FreeGrant так, чтобы инкогнито НЕ получало новый бонус.
    Возвращает (grant|None, set_cookie_gid_if_needed|None).
    """
    _ensure_session_key(request)

    # исходные маркеры
    session_key = request.session.session_key or ""
    gid = _guest_cookie_id(request) or ""
    fp_soft = _get_fp_from_request(request)  # мягкий fp (cookie/hdr/middleware)
    ua = _ua_hash(request)
    ip = _ip_hash(request)
    first_ip = (request.META.get("REMOTE_ADDR") or "").strip() or None

    # Если gid отсутствует — сгенерируем, но поставим cookie только если грант реально появится
    set_cookie_gid: Optional[str] = None
    if not gid:
        gid = uuid4().hex
        set_cookie_gid = gid

    # 1) Сначала ТОЛЬКО ПОИСК — без создания
    grant = _find_grant_only(
        fp=fp_soft, gid=gid, session_key=session_key, ua_hash=ua, ip_hash=ip, first_ip=first_ip
    )
    if grant:
        # допривязываем недостающие маркеры (молча)
        updated = []
        if fp_soft and _has_field(FreeGrant, "fp") and not getattr(grant, "fp", ""):
            grant.fp = fp_soft
            updated.append("fp")
        if gid and _has_field(FreeGrant, "gid") and not getattr(grant, "gid", ""):
            grant.gid = gid
            updated.append("gid")
        if session_key and _has_field(FreeGrant, "session_key") and not getattr(grant, "session_key", ""):
            grant.session_key = session_key
            updated.append("session_key")
        if ip and _has_field(FreeGrant, "ip_hash") and not getattr(grant, "ip_hash", ""):
            grant.ip_hash = ip
            updated.append("ip_hash")
        if ua and _has_field(FreeGrant, "ua_hash") and not getattr(grant, "ua_hash", ""):
            grant.ua_hash = ua
            updated.append("ua_hash")
        if first_ip and _has_field(FreeGrant, "first_ip") and not getattr(grant, "first_ip", None):
            grant.first_ip = first_ip
            updated.append("first_ip")
        if updated:
            try:
                grant.save(update_fields=updated)
            except Exception:
                pass
        return grant, set_cookie_gid

    # 2) Не нашли — СОЗДАЁМ ТОЛЬКО если есть fp (cookie/hdr/middleware)
    new_grant = _create_grant_if_fp(
        fp=fp_soft, gid=gid, session_key=session_key, ua_hash=ua, ip_hash=ip, first_ip=first_ip
    )
    if new_grant:
        return new_grant, set_cookie_gid

    # 3) Нет fp → не создаём (инкогнито-первый-заход). Вернём None.
    return None, None


def _claim_guest_jobs_for_user(request: HttpRequest) -> None:
    """
    Привязывает все «гостевые» задачи текущего клиента к авторизованному пользователю.
    Работает по нескольким ключам: session_key, gid, fp — если такие поля есть в модели.
    Безошибочно работает и на старой схеме (только guest_session_key).
    """
    if not request.user.is_authenticated:
        return

    sk = _ensure_session_key(request)
    gid = _guest_cookie_id(request) or ""
    fp = _get_fp_from_request(request) or _hard_fingerprint(request)

    q = Q(guest_session_key=sk)
    if gid and _has_field(GenerationJob, "guest_gid"):
        q |= Q(guest_gid=gid)
    if fp and _has_field(GenerationJob, "guest_fp"):
        q |= Q(guest_fp=fp)

    try:
        with transaction.atomic():
            GenerationJob.objects.filter(user__isnull=True).filter(q).update(user_id=request.user.id)
    except Exception:
        # не мешаем странице, если что-то пошло не так
        pass


def _image_cache_key(job_id: int) -> str:
    return f"genimg:{job_id}"


def _image_url_cache_key(job_id: int) -> str:
    return f"genimgurl:{job_id}"


def _default_back_url(request: HttpRequest) -> str:
    for name in ("dashboard:my_jobs", "gallery:index"):
        try:
            return reverse(name)
        except Exception:
            continue
    return "/"


def _owner_allowed(request: HttpRequest, job: GenerationJob) -> bool:
    """
    Доступ: владелец или «тот же гость».
    Для гостя проверяем session_key, а если поля существуют — ещё и gid/fp.
    """
    if job.user_id:
        return request.user.is_authenticated and (request.user.id == job.user_id or request.user.is_staff)

    # гость
    if _ensure_session_key(request) == (job.guest_session_key or ""):
        return True

    # расширенные ключи, если они есть в модели
    try:
        if _has_field(GenerationJob, "guest_gid"):
            gid = _guest_cookie_id(request) or ""
            if gid and getattr(job, "guest_gid", "") == gid:
                return True
    except Exception:
        pass

    try:
        if _has_field(GenerationJob, "guest_fp"):
            fp = _get_fp_from_request(request) or _hard_fingerprint(request)
            if getattr(job, "guest_fp", "") == fp:
                return True
    except Exception:
        pass

    return False


def _merge_grant_to_wallet_once(request: HttpRequest, wallet: Wallet) -> None:
    """
    Переносим остаток гостевого FreeGrant в кошелёк при первом визите после логина.
    """
    session_key = f"grant_merged_once_{wallet.user_id}"
    if request.session.get(session_key):
        return

    try:
        with transaction.atomic():
            # Используем select_for_update для предотвращения race conditions
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

            # Проверяем, есть ли уже привязанный к этому пользователю FreeGrant
            existing_grant = FreeGrant.objects.filter(user=wallet.user).first()
            if existing_grant:
                # У пользователя уже есть привязанный грант, не создаем новый и не переносим токены
                request.session[session_key] = True
                request.session.modified = True
                return

            grant, _maybe_cookie = _ensure_grant(request)
            if not grant:
                request.session[session_key] = True
                request.session.modified = True
                return

            # Дополнительная проверка - грант уже привязан к этому пользователю
            if grant.user_id == wallet.user_id:
                request.session[session_key] = True
                request.session.modified = True
                return

            # Проверяем, что у гранта есть токены для переноса
            if grant.left <= 0:
                request.session[session_key] = True
                request.session.modified = True
                return

            # Логируем операцию для диагностики
            log.info(f"Merging grant {grant.pk} (left={grant.left}) to user {wallet.user_id}")

            # bind_to_user умеет аккуратно переносить остаток
            grant.bind_to_user(wallet.user, transfer_left=True)

            log.info(f"Successfully merged grant {grant.pk} to user {wallet.user_id}")

    except Exception as e:
        log.error(f"Grant merge failed: {e}")
    finally:
        request.session[session_key] = True
        request.session.modified = True


# =======================
#        views
# =======================
@require_http_methods(["GET"])
def new(request: HttpRequest) -> HttpResponse:
    is_staff = request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)
    price = 0 if (FREE_FOR_STAFF and is_staff) else TOKEN_COST

    # если пользователь уже вошёл — «подцепим» его прошлые гостевые задачи
    if request.user.is_authenticated:
        _claim_guest_jobs_for_user(request)

    # --- подсказки/витрина ---
    suggestion_categories: List[SuggestionCategory] = list(
        SuggestionCategory.objects.filter(is_active=True)
        .prefetch_related("suggestions")
        .order_by("order", "name")
    )
    suggestions_flat: List[Suggestion] = list(
        Suggestion.objects.filter(is_active=True).order_by("order", "title")
    )
    showcase_categories: List[ShowcaseCategory] = list(
        ShowcaseCategory.objects.filter(is_active=True).order_by("order", "name")
    )
    showcase_images: List[ShowcaseImage] = list(
        ShowcaseImage.objects.filter(is_active=True).order_by("order", "-created_at")[:18]
    )

    wallet = None
    set_cookie_gid: Optional[str] = None

    # ЧИСЛО ОБРАБОТОК
    auth_gens_left: Optional[int] = 0
    guest_tokens = 0
    guest_gens_left = 0

    if request.user.is_authenticated:
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        if price == 0:
            auth_gens_left = None
        else:
            _merge_grant_to_wallet_once(request, wallet)
            auth_gens_left = int(wallet.balance or 0) // int(price or 1)
    else:
        grant, maybe_gid = _ensure_grant(request)
        set_cookie_gid = maybe_gid
        if grant:
            # Проверяем состояние AbuseCluster перед отображением токенов
            try:
                from .models import AbuseCluster
                cluster = AbuseCluster.ensure_for(
                    fp=_hard_fingerprint(request),
                    gid=_guest_cookie_id(request) or None,
                    ip_hash=_ip_hash(request) or None,
                    ua_hash=_ua_hash(request) or None,
                    create_if_missing=False
                )
                # Если кластер существует и лимит исчерпан, показываем 0 токенов
                if cluster and cluster.jobs_left <= 0:
                    guest_tokens = 0
                    guest_gens_left = 0
                else:
                    # у модели часто есть свойство/поле left; на всякий — считаем безопасно
                    try:
                        guest_tokens = int(getattr(grant, "left", max(grant.total - grant.consumed, 0)))
                    except Exception:
                        guest_tokens = 0
                    guest_gens_left = (guest_tokens // int(price or 1)) if price else 0
            except Exception:
                # Если кластер не найден (новый пользователь), показываем токены из гранта
                try:
                    guest_tokens = int(getattr(grant, "left", max(grant.total - grant.consumed, 0)))
                except Exception:
                    guest_tokens = 0
                guest_gens_left = (guest_tokens // int(price or 1)) if price else 0
        else:
            # Защита сработала: без fp новый грант не создан → ничего не добавляем
            guest_tokens = 0
            guest_gens_left = 0

    ctx = {
        "wallet": wallet,
        "price": price,
        "TOKENS_PRICE_PER_GEN": TOKEN_COST,
        "guest_tokens": guest_tokens,
        "guest_gens_left": guest_gens_left,
        "auth_gens_left": auth_gens_left,
        "tariffs_url": _tariffs_url(),
        "suggestion_categories": suggestion_categories,
        "suggestions": suggestions_flat,
        "showcase_categories": showcase_categories,
        "showcase_images": showcase_images,
    }

    resp = render(request, "generate/new.html", ctx)
    if set_cookie_gid:
        # ставим gid только если грант найден/создан — без фанатизма
        resp.set_cookie("gid", set_cookie_gid, max_age=60 * 60 * 24 * 730, httponly=False, samesite="Lax")
    return resp


def job_detail(request: HttpRequest, pk: int, slug: str) -> HttpResponse:
    job = get_object_or_404(GenerationJob, pk=pk)
    if not _owner_allowed(request, job):
        return HttpResponseForbidden("Forbidden")

    canonical = _job_slug(job)
    if slug != canonical:
        return redirect("generate:job_detail", pk=pk, slug=canonical)

    try:
        poll_url = reverse("generate:api_status", kwargs={"job_id": job.pk})
    except NoReverseMatch:
        poll_url = ""
    try:
        image_url = reverse("generate:job_image", kwargs={"pk": job.pk, "slug": canonical})
    except NoReverseMatch:
        image_url = ""

    return render(
        request,
        "generate/job_detail.html",
        {"job": job, "poll_url": poll_url, "estimate_ms": 60000, "image_url": image_url},
    )


def job_status(request: HttpRequest, pk: int, slug: str) -> JsonResponse:
    job = get_object_or_404(GenerationJob, pk=pk)
    if not _owner_allowed(request, job):
        return JsonResponse({"error": "forbidden"}, status=403)

    canonical = _job_slug(job)
    if slug != canonical:
        try:
            redir = reverse("generate:job_status", kwargs={"pk": pk, "slug": canonical})
        except NoReverseMatch:
            redir = ""
        return JsonResponse({"redirect": redir}, status=308)

    try:
        image_url = reverse("generate:job_image", kwargs={"pk": job.pk, "slug": canonical})
    except NoReverseMatch:
        image_url = None

    data = {
        "id": job.pk,
        "status": (job.status or ""),
        "image": {"url": image_url} if (job.status == GenerationJob.Status.DONE and image_url) else None,
        "error": job.error or "",
        "done": job.status == GenerationJob.Status.DONE,
        "failed": job.status == GenerationJob.Status.FAILED,
    }
    return JsonResponse(data, status=200)


def job_detail_no_slug(request: HttpRequest, pk: int) -> HttpResponse:
    job = get_object_or_404(GenerationJob, pk=pk)
    if not _owner_allowed(request, job):
        return HttpResponseForbidden("Forbidden")
    return redirect("generate:job_detail", pk=pk, slug=_job_slug(job))


def job_status_no_slug(request: HttpRequest, pk: int) -> HttpResponse:
    job = get_object_or_404(GenerationJob, pk=pk)
    if not _owner_allowed(request, job):
        return JsonResponse({"error": "forbidden"}, status=403)
    return redirect("generate:job_status", pk=pk, slug=_job_slug(job))


def job_image(request: HttpRequest, pk: int, slug: str) -> HttpResponse:
    job = get_object_or_404(GenerationJob, pk=pk)
    if not _owner_allowed(request, job):
        return HttpResponseForbidden("Forbidden")

    # 1) результат из файла
    if job.result_image and job.result_image.name:
        try:
            name = job.result_image.name.lower()
            ctype = "image/png" if name.endswith(".png") else "image/jpeg"
            content = job.result_image.open("rb").read()
            etag = hashlib.sha1(content).hexdigest()
            if_none = request.META.get("HTTP_IF_NONE_MATCH")
            if if_none and if_none.strip('"') == etag:
                return HttpResponse(status=304)
            resp = HttpResponse(content, content_type=ctype)
            resp["ETag"] = f"\"{etag}\""
            resp["Cache-Control"] = "public, max-age=31536000, immutable"
            return resp
        except Exception:
            pass

    # 2) из кэша байтов
    content = cache.get(_image_cache_key(job.pk))
    content_type = "image/jpeg" if content else None

    # 2.1) внешний URL
    if not content:
        ext_url = cache.get(_image_url_cache_key(job.pk))
        if ext_url:
            return redirect(str(ext_url))

    # 3) плейсхолдер
    if not content:
        try:
            text = (job.prompt or "AI Gallery").strip()[:24]
            img = Image.new("RGB", (512, 512), (18, 18, 22))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 28)
            except Exception:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            w, h = img.size
            draw.text(((w - tw) // 2, (h - th) // 2), text, fill=(220, 220, 220), font=font)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            content = buf.getvalue()
            content_type = "image/png"
            cache.set(_image_cache_key(job.pk), content, timeout=60 * 60 * 24 * 7)
        except Exception:
            content = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc\x00\x01"
                b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            content_type = "image/png"

    etag = hashlib.sha1(content).hexdigest()
    if_none = request.META.get("HTTP_IF_NONE_MATCH")
    if if_none and if_none.strip('"') == etag:
        return HttpResponse(status=304)

    resp = HttpResponse(content, content_type=content_type)
    resp["ETag"] = f"\"{etag}\""
    resp["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp


# =======================
#   Delete: confirm + post
# =======================
@login_required
@require_http_methods(["GET"])
def job_confirm_delete(request: HttpRequest, pk: int) -> HttpResponse:
    job = get_object_or_404(GenerationJob, pk=pk)

    default_next = reverse("dashboard:my_jobs")
    next_url = request.GET.get("next") or default_next
    if not url_has_allowed_host_and_scheme(
        next_url, {request.get_host()}, require_https=request.is_secure()
    ):
        next_url = default_next

    if getattr(job, "is_public", False) and not request.user.is_staff:
        messages.error(request, "Публичные работы может удалять только администратор.")
        return redirect(next_url)
    if not (request.user.is_staff or job.user_id == request.user.id):
        messages.error(request, "Нет прав на удаление этой генерации.")
        return redirect(next_url)

    return render(
        request,
        "generate/job_confirm_delete.html",
        {"job": job, "next": next_url},
    )


@login_required
@require_POST
def job_delete(request, pk: int):
    job = get_object_or_404(GenerationJob, pk=pk)

    next_url = request.POST.get("next") or reverse("dashboard:my_jobs")
    if not url_has_allowed_host_and_scheme(
        next_url, {request.get_host()}, require_https=request.is_secure()
    ):
        next_url = reverse("dashboard:my_jobs")

    if getattr(job, "is_public", False) and not request.user.is_staff:
        messages.error(request, "Публичные работы может удалять только администратор.")
        return redirect(next_url)
    if not (request.user.is_staff or job.user_id == request.user.id):
        messages.error(request, "Нет прав на удаление этой генерации.")
        return redirect(next_url)

    try:
        if getattr(job, "result_image", None) and job.result_image.name:
            job.result_image.delete(save=False)
    except Exception:
        pass
    try:
        cache.delete(_image_cache_key(job.pk))
        cache.delete(_image_url_cache_key(job.pk))
    except Exception:
        pass

    try:
        job.delete()
    except (db_utils.OperationalError, db_utils.IntegrityError, TypeError):
        tbl = job._meta.db_table
        with transaction.atomic():
            with connection.cursor() as cur:
                if connection.vendor == "sqlite":
                    sql = f"DELETE FROM {connection.ops.quote_name(tbl)} WHERE id = {int(job.pk)}"
                    cur.execute(sql)
                else:
                    placeholder = "%s"
                    sql = f"DELETE FROM {connection.ops.quote_name(tbl)} WHERE id = {placeholder}"
                    cur.execute(sql, (job.pk,))
    except Exception:
        raise

    messages.success(request, f"Генерация #{pk} удалена.")
    return redirect(next_url)


@login_required
def my_jobs_all(request: HttpRequest) -> HttpResponse:
    # на всякий случай перед показом — привяжем гостевые задачи к юзеру
    _claim_guest_jobs_for_user(request)

    qs = (
        GenerationJob.objects.filter(user_id=request.user.id)
        .order_by("-created_at")
        .select_related("user")
    )

    paginator = Paginator(qs, 24)
    page_obj = paginator.get_page(request.GET.get("page"))

    jobs_cards = []
    for obj in page_obj.object_list:
        s = slugify((obj.prompt or "image"), allow_unicode=True) or "image"
        try:
            img_url = reverse("generate:job_image", args=[obj.pk, s])
        except NoReverseMatch:
            img_url = ""
        try:
            detail_url = reverse("generate:job_detail", args=[obj.pk, s])
        except NoReverseMatch:
            detail_url = ""
        try:
            delete_url = reverse("generate:job_confirm_delete", args=[obj.pk])
        except NoReverseMatch:
            delete_url = ""

        jobs_cards.append(
            {
                "obj": obj,
                "img_url": img_url,
                "share_url": detail_url,
                "delete_url": delete_url,
                "title": (obj.prompt or "Моя генерация")[:42],
                "created_at": obj.created_at,
                "status": obj.status,
            }
        )

    ctx = {"page_obj": page_obj, "jobs_cards": jobs_cards}
    return render(request, "gallery/my_jobs.html", ctx)


# =======================
#   SUGGESTIONS CRUD (AJAX)
# =======================
@staff_member_required
@require_POST
def api_suggestion_create(request: HttpRequest) -> JsonResponse:
    title = (request.POST.get("title") or "").strip()
    text = (request.POST.get("text") or "").strip()
    order = int(request.POST.get("order") or 0)
    cat_slug = (request.POST.get("category") or "").strip()

    if not title or not text:
        return JsonResponse({"ok": False, "error": "title и text обязательны"}, status=400)

    cat = None
    if cat_slug:
        cat = SuggestionCategory.objects.filter(slug=cat_slug).first()

    s = Suggestion.objects.create(title=title, text=text, category=cat, is_active=True, order=order)
    return JsonResponse(
        {"ok": True, "id": s.id, "title": s.title, "text": s.text, "category": (s.category.slug if s.category_id else None)},
        status=201,
    )


@staff_member_required
@require_POST
def api_suggestion_update(request: HttpRequest, pk: int) -> JsonResponse:
    s = get_object_or_404(Suggestion, pk=pk)
    title = request.POST.get("title")
    text = request.POST.get("text")
    order = request.POST.get("order")
    is_active = request.POST.get("is_active")
    cat_slug = request.POST.get("category")

    if title is not None:
        s.title = title.strip()
    if text is not None:
        s.text = text.strip()
    if order is not None:
        try:
            s.order = int(order)
        except ValueError:
            pass
    if is_active is not None:
        s.is_active = str(is_active).lower() in {"1", "true", "yes", "on"}
    if cat_slug is not None:
        s.category = SuggestionCategory.objects.filter(slug=cat_slug).first() if cat_slug else None

    s.save()
    return JsonResponse({"ok": True})


@staff_member_required
@require_POST
def api_suggestion_delete(request: HttpRequest, pk: int) -> JsonResponse:
    s = get_object_or_404(Suggestion, pk=pk)
    s.delete()
    return JsonResponse({"ok": True})
