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
from django.db.models import Q, F, Value
from django.db.models.functions import Greatest
from django.http import (
    Http404,
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
from gallery.models import Like, JobComment, JobCommentLike, JobSave, Image as GalleryImage
from .models_image import ImageModelConfiguration
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

# Список категорий для блока подсказок (из static/img/category)
CATEGORY_NAMES = [
    'абстракция', 'Архитектура', 'будущее', 'винтаж', 'времена года', 'города',
    'детство', 'для разработки', 'еда', 'животные', 'интерьер', 'исскуство',
    'история', 'космос', 'макросъемка', 'медитация', 'минимализм', 'мифология',
    'мода', 'музыка', 'наука', 'ночь', 'пейзажи', 'подводный мир', 'портреты',
    'праздники', 'приключения', 'природа', 'профессии', 'романтика', 'свет и тень',
    'спорт', 'текстуры', 'технологии', 'транспорт', 'уют', 'Фэнтези', 'экстрим',
    'эмоции', 'Эстетика'
]


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
    ОБНОВЛЁННАЯ СИСТЕМА: Использует ensure_guest_grant_with_security
    с полной защитой от Tor/VPN обхода через кластеризацию по UA_HASH.

    Возвращает (grant|None, set_cookie_gid_if_needed|None).
    """
    from .security import ensure_guest_grant_with_security

    # Получаем грант через новую систему безопасности
    grant, device, error = ensure_guest_grant_with_security(request)

    if error:
        # Ошибка безопасности - не даём токены
        return None, None

    if not grant:
        # Не удалось получить грант
        return None, None

    # GID уже управляется middleware, не нужно ставить cookie здесь
    return grant, None


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

# Opportunistic cleanup: remove non-persisted jobs older than 24h
# This keeps only "saved to My Jobs" items; others are auto-pruned.
from django.utils import timezone as _tz  # local alias to avoid clashes
from datetime import timedelta as _td

def _cleanup_unpersisted_jobs(limit: int = 100) -> None:
    try:
        cutoff = _tz.now() - _td(hours=24)
        qs = GenerationJob.objects.filter(persisted=False, created_at__lt=cutoff).order_by("id")[:limit]
        ids = list(qs.values_list("id", flat=True))
        for job in qs:
            # Remove stored files and caches (same as delete flow)
            # 1) Image file (if any)
            try:
                if getattr(job, "result_image", None) and job.result_image.name:
                    job.result_image.delete(save=False)
            except Exception:
                pass
            # 2) Video file (if any persisted under MEDIA_URL)
            try:
                from django.conf import settings as _s
                from django.core.files.storage import default_storage as _ds
                from urllib.parse import urlparse as _u
                vurl = (getattr(job, "result_video_url", "") or "").strip()
                if vurl:
                    media_url = str(getattr(_s, "MEDIA_URL", "/media/") or "/media/")
                    rel = None
                    if vurl.startswith(media_url):
                        rel = vurl[len(media_url):].lstrip("/")
                    else:
                        parsed = _u(vurl)
                        if parsed.path and "/media/" in parsed.path:
                            rel = parsed.path.split("/media/", 1)[-1].lstrip("/")
                    if rel:
                        try:
                            _ds.delete(rel)
                        except Exception:
                            pass
            except Exception:
                pass
            # 3) Cache keys
            try:
                cache.delete(_image_cache_key(job.pk))
                cache.delete(_image_url_cache_key(job.pk))
            except Exception:
                pass
        if ids:
            GenerationJob.objects.filter(id__in=ids).delete()
    except Exception:
        # never break page render on cleanup errors
        pass


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


def _viewer_allowed_on_job(request: HttpRequest, job: GenerationJob) -> bool:
    """
    Разрешаем взаимодействия с job не только владельцу:
    - владелец/тот же гость — как раньше (_owner_allowed)
    - если job опубликован (PublicPhoto/PublicVideo) — доступен всем
    - если профиль автора НЕ приватный — позволяем лайки/комментарии другим пользователям
      (используется на странице профиля открытых аккаунтов).
    Для приватного профиля оставляем запрет.
    По умолчанию (если Profile отсутствует) считаем профиль открытым.
    """
    if _owner_allowed(request, job):
        return True

    # Проверяем, опубликован ли этот job (PublicPhoto или PublicVideo)
    try:
        from gallery.models import PublicPhoto, PublicVideo
        if job.generation_type == 'image':
            if PublicPhoto.objects.filter(source_job_id=job.pk).exists():
                return True
        elif job.generation_type == 'video':
            if PublicVideo.objects.filter(source_job_id=job.pk).exists():
                return True
    except Exception:
        pass

    try:
        from dashboard.models import Profile
        prof = Profile.objects.filter(user_id=job.user_id).only("is_private").first()
        if prof is None:
            # Нет записи профиля — трактуем как открытый профиль
            return True
        return not bool(getattr(prof, "is_private", False))
    except Exception:
        # На сбоях не блокируем лайки/комменты для открытых профилей
        return True


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

    # Auto-cleanup: drop non-persisted jobs older than 24h (only for new logic)
    try:
        _cleanup_unpersisted_jobs()
    except Exception:
        pass

    # если пользователь уже вошёл — «подцепим» его прошлые гостевые задачи
    if request.user.is_authenticated:
        _claim_guest_jobs_for_user(request)

    # --- подсказки/витрина ---
    suggestion_categories: List[SuggestionCategory] = list(
        SuggestionCategory.objects.filter(is_active=True)
        .prefetch_related("suggestions")
        .order_by("name")
    )
    suggestions_flat: List[Suggestion] = list(
        Suggestion.objects.filter(is_active=True).order_by("order", "title")
    )

    # Категории промптов с изображениями и пагинацией (для изображений)
    from .models import PromptCategory, VideoPromptCategory, ShowcaseVideo
    prompt_categories_queryset = PromptCategory.objects.filter(is_active=True).prefetch_related("prompts").order_by("order", "name")
    prompt_categories_paginator = Paginator(prompt_categories_queryset, 24)  # 24 категории на странице
    prompt_page_number = request.GET.get('prompt_page', 1)
    prompt_page_obj = prompt_categories_paginator.get_page(prompt_page_number)
    prompt_categories: List[PromptCategory] = list(prompt_page_obj.object_list)

    # Категории промптов для ВИДЕО (отдельные)
    video_prompt_categories_queryset = VideoPromptCategory.objects.filter(is_active=True).prefetch_related("video_prompts").order_by("order", "name")
    video_prompt_categories_paginator = Paginator(video_prompt_categories_queryset, 24)
    video_prompt_page_number = request.GET.get('video_prompt_page', 1)
    video_prompt_page_obj = video_prompt_categories_paginator.get_page(video_prompt_page_number)
    video_prompt_categories: List[VideoPromptCategory] = list(video_prompt_page_obj.object_list)

    showcase_categories: List[ShowcaseCategory] = list(
        ShowcaseCategory.objects.filter(is_active=True).order_by("order", "name")
    )
    # Пагинация для showcase ИЗОБРАЖЕНИЙ (16 на страницу) + серверная фильтрация по категории
    page_number = request.GET.get('showcase_page', 1)
    active_scat = (request.GET.get('scat') or '').strip()
    showcase_queryset = ShowcaseImage.objects.filter(is_active=True)
    if active_scat:
        showcase_queryset = showcase_queryset.filter(category__slug=active_scat)
    showcase_queryset = showcase_queryset.order_by("order", "-created_at")
    showcase_paginator = Paginator(showcase_queryset, 16)
    showcase_page = showcase_paginator.get_page(page_number)
    showcase_images: List[ShowcaseImage] = list(showcase_page.object_list)

    # Пагинация для showcase ВИДЕО (отдельные, 12 на страницу)
    video_showcase_page_number = request.GET.get('video_showcase_page', 1)
    active_video_scat = (request.GET.get('video_scat') or '').strip()
    video_showcase_queryset = ShowcaseVideo.objects.filter(is_active=True)
    if active_video_scat:
        video_showcase_queryset = video_showcase_queryset.filter(category__slug=active_video_scat)
    video_showcase_queryset = video_showcase_queryset.order_by("order", "-created_at")
    video_showcase_paginator = Paginator(video_showcase_queryset, 12)
    video_showcase_page = video_showcase_paginator.get_page(video_showcase_page_number)
    showcase_videos: List[ShowcaseVideo] = list(video_showcase_page.object_list)

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
                    guest_gens_cap = int(getattr(cluster, "jobs_left", 3))
                    guest_gens_left = min(guest_gens_cap, (guest_tokens // int(price or 1)) if price else guest_gens_cap)
            except Exception:
                # Если кластер не найден (новый пользователь), показываем токены из гранта
                try:
                    guest_tokens = int(getattr(grant, "left", max(grant.total - grant.consumed, 0)))
                except Exception:
                    guest_tokens = 0
                guest_gens_cap = 3
                guest_gens_left = min(guest_gens_cap, (guest_tokens // int(price or 1)) if price else guest_gens_cap)
        else:
            # Защита сработала: без fp новый грант не создан → ничего не добавляем
            guest_tokens = 0
            guest_gens_left = 0

    user_key = f"u:{request.user.id}" if request.user.is_authenticated else f"g:{_ensure_session_key(request)}:{_guest_cookie_id(request) or ''}"

    # Получить активные модели изображений
    image_models = ImageModelConfiguration.objects.filter(is_active=True).order_by('order', 'name')

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
        # Категории и промпты для ИЗОБРАЖЕНИЙ
        "prompt_categories": prompt_categories,
        "prompt_page_obj": prompt_page_obj,
        # Категории и промпты для ВИДЕО (отдельные)
        "video_prompt_categories": video_prompt_categories,
        "video_prompt_page_obj": video_prompt_page_obj,
        # Showcase
        "showcase_categories": showcase_categories,
        "showcase_images": showcase_images,
        "showcase_page": showcase_page,
        "showcase_videos": showcase_videos,
        "video_showcase_page": video_showcase_page,
        "category_names": CATEGORY_NAMES,
        "active_scat": active_scat,
        "active_video_scat": active_video_scat,
        "DEFAULT_IMAGE_MODEL": getattr(settings, "RUNWARE_DEFAULT_MODEL", "runware:101@1"),
        "user_key": user_key,
        "image_models": image_models,
    }

    resp = render(request, "generate/new.html", ctx)
    if set_cookie_gid:
        # ставим gid только если грант найден/создан — без фанатизма
        resp.set_cookie("gid", set_cookie_gid, max_age=60 * 60 * 24 * 730, httponly=False, samesite="Lax")
    return resp


def job_detail(request: HttpRequest, pk: int, slug: str) -> HttpResponse:
    job = get_object_or_404(GenerationJob, pk=pk)
    if not _viewer_allowed_on_job(request, job):
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

    # Comments and likes context for job modal
    root_comments = (
        JobComment.objects.select_related("user")
        .prefetch_related("user__profile", "replies__user", "replies__user__profile", "likes")
        .filter(job=job, is_visible=True, parent__isnull=True)
        .order_by("created_at")
    )
    # Liked job?
    job_liked = False
    if request.user.is_authenticated:
        job_liked = Like.objects.filter(user=request.user, job=job).exists()
    job_like_count = Like.objects.filter(job=job).count()

    liked_comment_ids = set()
    all_ids = []
    for c in root_comments:
        all_ids.append(c.pk)
        for r in c.replies.all():
            all_ids.append(r.pk)
    if all_ids and request.user.is_authenticated:
        liked_comment_ids = set(
            JobCommentLike.objects.filter(user=request.user, comment_id__in=all_ids)
            .values_list("comment_id", flat=True)
        )

    return render(
        request,
        "generate/job_detail.html",
        {
            "job": job,
            "poll_url": poll_url,
            "estimate_ms": 60000,
            "image_url": image_url,
            "comments": root_comments,
            "job_liked": job_liked,
            "job_like_count": job_like_count,
            "liked_comment_ids": liked_comment_ids,
        },
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
    if not _viewer_allowed_on_job(request, job):
        return HttpResponseForbidden("Forbidden")

    # Редирект на новый URL формат: photo/<slug>-<pk> или video/<slug>-<pk>
    slug = _job_slug(job)
    slug_with_id = f"{slug}-{job.pk}"
    if job.generation_type == 'video':
        return redirect("generate:video_detail", slug=slug_with_id)
    else:
        return redirect("generate:photo_detail", slug=slug_with_id)


def photo_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Детали фото по slug (формат: slug-ID)"""
    # Извлекаем ID из конца slug
    parts = slug.rsplit('-', 1)
    if len(parts) == 2 and parts[1].isdigit():
        pk = int(parts[1])
        job = get_object_or_404(GenerationJob, pk=pk, generation_type='image')
    else:
        raise Http404("Invalid slug format")

    if not _viewer_allowed_on_job(request, job):
        return HttpResponseForbidden("Forbidden")

    # Проверка корректности slug
    expected_slug = f"{_job_slug(job)}-{job.pk}"
    if slug != expected_slug:
        return redirect("generate:photo_detail", slug=expected_slug)

    # Используем существующую логику job_detail
    return job_detail(request, pk=job.pk, slug=_job_slug(job))


def video_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Детали видео по slug (формат: slug-ID)"""
    # Извлекаем ID из конца slug
    parts = slug.rsplit('-', 1)
    if len(parts) == 2 and parts[1].isdigit():
        pk = int(parts[1])
        job = get_object_or_404(GenerationJob, pk=pk, generation_type='video')
    else:
        raise Http404("Invalid slug format")

    if not _viewer_allowed_on_job(request, job):
        return HttpResponseForbidden("Forbidden")

    # Проверка корректности slug
    expected_slug = f"{_job_slug(job)}-{job.pk}"
    if slug != expected_slug:
        return redirect("generate:video_detail", slug=expected_slug)

    # Используем существующую логику job_detail
    return job_detail(request, pk=job.pk, slug=_job_slug(job))


def job_status_no_slug(request: HttpRequest, pk: int) -> HttpResponse:
    job = get_object_or_404(GenerationJob, pk=pk)
    if not _viewer_allowed_on_job(request, job):
        return JsonResponse({"error": "forbidden"}, status=403)
    return redirect("generate:job_status", pk=pk, slug=_job_slug(job))


def job_image(request: HttpRequest, pk: int, slug: str) -> HttpResponse:
    job = get_object_or_404(GenerationJob, pk=pk)
    if not _viewer_allowed_on_job(request, job):
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
            text = (job.prompt or "Pixera").strip()[:24]
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

    # Remove related personal gallery entries for this job (prevents stale tiles in "Мои генерации")
    try:
        GalleryImage.objects.filter(generation_job=job).delete()
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
    """
    Canonical redirect: unify 'My Jobs' under /dashboard/my-jobs
    so cabinet and gallery use the same URL (with any query preserved).
    """
    base = reverse("dashboard:my_jobs")
    qs = request.META.get("QUERY_STRING", "")
    if qs:
        return redirect(f"{base}?{qs}", permanent=True)
    return redirect(base, permanent=True)


# =======================
#   JOB INTERACTIONS (likes/comments for unpublished jobs)
# =======================

@login_required
@require_POST
def job_like_toggle(request: HttpRequest, pk: int) -> JsonResponse:
    job = get_object_or_404(GenerationJob, pk=pk)
    if not _viewer_allowed_on_job(request, job):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    liked = False
    with transaction.atomic():
        existing = Like.objects.select_for_update().filter(user=request.user, job=job).first()
        if existing:
            existing.delete()
            liked = False
        else:
            Like.objects.create(user=request.user, job=job)
            liked = True

    count = Like.objects.filter(job=job).count()
    # Notify owner about job like
    try:
        from dashboard.models import Notification
        if liked and request.user.is_authenticated and getattr(job, "user_id", None) and request.user.id != job.user_id:
            # Determine if it's photo or video based on generation_type
            gen_type = getattr(job, "generation_type", "image")
            if gen_type == "video":
                message_text = f"@{request.user.username} понравилось ваше видео"
                slug_with_id = f"{_job_slug(job)}-{job.pk}"
                link_url = reverse("generate:video_detail", args=[slug_with_id])
            else:
                message_text = f"@{request.user.username} понравилось ваше фото"
                slug_with_id = f"{_job_slug(job)}-{job.pk}"
                link_url = reverse("generate:photo_detail", args=[slug_with_id])

            Notification.create(
                recipient=job.user,
                actor=request.user,
                type=Notification.Type.LIKE_JOB,
                message=message_text,
                link=link_url,
                payload={"job_id": job.pk, "count": int(count), "generation_type": gen_type},
            )
    except Exception:
        pass
    return JsonResponse({"ok": True, "liked": liked, "count": count})


@login_required
@require_POST
def job_comment_add(request: HttpRequest, pk: int) -> JsonResponse:
    job = get_object_or_404(GenerationJob, pk=pk)
    if not _viewer_allowed_on_job(request, job):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    text = (request.POST.get("text") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "empty"}, status=400)

    jc = JobComment.objects.create(job=job, user=request.user, text=text, parent=None)
    # Notify owner about new job comment
    try:
        from dashboard.models import Notification
        if request.user.is_authenticated and getattr(job, "user_id", None) and request.user.id != job.user_id:
            Notification.create(
                recipient=job.user,
                actor=request.user,
                type=Notification.Type.COMMENT_JOB,
                message=f"@{request.user.username} прокомментировал(а) вашу генерацию",
                link=reverse("generate:job_detail", args=[job.pk, _job_slug(job)]) + "#comments",
                payload={"job_id": job.pk, "comment_id": jc.pk},
            )
    except Exception:
        pass
    return JsonResponse({"ok": True})


@login_required
@require_POST
def job_comment_reply(request: HttpRequest, pk: int) -> JsonResponse:
    parent = get_object_or_404(JobComment, pk=pk, is_visible=True)
    job = parent.job
    if not _viewer_allowed_on_job(request, job):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    text = (request.POST.get("text") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "empty"}, status=400)

    jc = JobComment.objects.create(job=job, user=request.user, text=text, parent=parent)
    # Notify comment author about reply on job
    try:
        from dashboard.models import Notification
        if request.user.is_authenticated and getattr(parent, "user_id", None) and request.user.id != parent.user_id:
                Notification.create(
                    recipient=parent.user,
                    actor=request.user,
                    type=Notification.Type.REPLY_JOB,
                    message=f"@{request.user.username} ответил(а) на ваш комментарий",
                    link=reverse("generate:job_detail", args=[job.pk, _job_slug(job)]) + f"#c{jc.pk}",
                    payload={"job_id": job.pk, "comment_id": parent.pk, "reply_id": jc.pk},
                )
    except Exception:
        pass
    return JsonResponse({"ok": True})


@login_required
@require_POST
def job_save_toggle(request: HttpRequest, pk: int) -> JsonResponse:
    """
    Toggle save (bookmark) for ANY GenerationJob (published or not).
    Returns: { ok: true, saved: bool, count: int }
    """
    job = get_object_or_404(GenerationJob, pk=pk)
    if not _viewer_allowed_on_job(request, job):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    saved = False
    with transaction.atomic():
        existing = JobSave.objects.select_for_update().filter(user=request.user, job=job).first()
        if existing:
            existing.delete()
            saved = False
        else:
            JobSave.objects.create(user=request.user, job=job)
            saved = True

    count = JobSave.objects.filter(job=job).count()
    return JsonResponse({"ok": True, "saved": saved, "count": count})


@login_required
@require_POST
def job_comment_like_toggle(request: HttpRequest, pk: int) -> JsonResponse:
    comment = get_object_or_404(JobComment, pk=pk, is_visible=True)
    job = comment.job
    if not _viewer_allowed_on_job(request, job):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    liked = False
    with transaction.atomic():
        existing = JobCommentLike.objects.select_for_update().filter(user=request.user, comment=comment).first()
        if existing:
            existing.delete()
            liked = False
        else:
            JobCommentLike.objects.create(user=request.user, comment=comment)
            liked = True

        # denorm counter on JobComment
        if liked:
            JobComment.objects.filter(pk=comment.pk).update(likes_count=F("likes_count") + 1)
        else:
            JobComment.objects.filter(pk=comment.pk).update(likes_count=Greatest(F("likes_count") - 1, Value(0)))

    new_count = JobComment.objects.filter(pk=comment.pk).values_list("likes_count", flat=True).first() or 0
    # Notify comment author about like on job comment
    try:
        from dashboard.models import Notification
        if liked and request.user.is_authenticated and getattr(comment, "user_id", None) and request.user.id != comment.user_id:
            Notification.create(
                recipient=comment.user,
                actor=request.user,
                type=Notification.Type.COMMENT_LIKE_JOB,
                message=f"@{request.user.username} понравился ваш комментарий",
                link=reverse("generate:job_detail", args=[comment.job_id, _job_slug(comment.job)]) + f"#c{comment.pk}",
                payload={"job_id": comment.job_id, "comment_id": comment.pk, "count": int(new_count)},
            )
    except Exception:
        pass
    return JsonResponse({"ok": True, "liked": liked, "count": new_count})


def job_likers(request: HttpRequest, pk: int) -> JsonResponse:
    """
    Список пользователей, лайкнувших задачу (GenerationJob).
    Доступ разрешён владельцу/тому же гостю и зрителям открытого профиля (_viewer_allowed_on_job).
    Формат ответа:
      { ok: true, likers: [{username, name, avatar, is_following}] }
    """
    job = get_object_or_404(GenerationJob, pk=pk)
    if not _viewer_allowed_on_job(request, job):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    # Берём только пользовательские лайки (user != null)
    likes_qs = (
        Like.objects
        .select_related("user", "user__profile")
        .filter(job=job, user__isnull=False)
        .order_by("-id")
    )

    user_ids = list(likes_qs.values_list("user_id", flat=True))

    # Кто из них уже «в подписках» у текущего пользователя
    following_set = set()
    if request.user.is_authenticated and user_ids:
        try:
            from dashboard.models import Follow
            following_set = set(
                Follow.objects.filter(follower=request.user, following_id__in=user_ids)
                .values_list("following_id", flat=True)
            )
        except Exception:
            following_set = set()

    def _avatar(u) -> str:
        try:
            prof = getattr(u, "profile", None)
            av = getattr(prof, "avatar", None)
            return av.url if (av and getattr(av, "url", None)) else ""
        except Exception:
            return ""

    data = []
    for lk in likes_qs:
        u = lk.user
        if not u:
            continue
        data.append({
            "username": u.username,
            "name": (u.get_full_name() or u.username),
            "avatar": _avatar(u),
            "is_following": (u.id in following_set),
        })

    return JsonResponse({"ok": True, "likers": data})


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


# =======================
#   PROMPT CATEGORIES
# =======================
@require_http_methods(["GET"])
def prompts_page(request: HttpRequest) -> HttpResponse:
    """Страница с категориями промптов"""
    from .models import PromptCategory

    # Получаем все активные категории с пагинацией
    categories_queryset = PromptCategory.objects.filter(is_active=True).prefetch_related('prompts').order_by('order', 'name')

    # Пагинация - 24 категории на страницу
    paginator = Paginator(categories_queryset, 24)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Добавляем счетчик активных промптов для каждой категории
    categories = list(page_obj.object_list)

    return render(request, 'generate/prompts.html', {
        'categories': categories,
        'page_obj': page_obj,
    })


def category_prompts_api(request: HttpRequest, category_id: int) -> JsonResponse:
    """API для получения промптов категории"""
    from .models import PromptCategory

    category = get_object_or_404(PromptCategory, id=category_id, is_active=True)
    prompts = category.prompts.filter(is_active=True).order_by('order', 'title')

    prompts_data = [
        {
            'id': p.id,
            'title': p.title,
            'prompt_text': p.prompt_text,
            'prompt_en': p.get_prompt_for_generation(),  # Профессиональный английский промпт (для использования)
            'prompt_en_raw': p.prompt_en,                # Оригинальное значение для редактирования
            'order': p.order,
            'is_active': p.is_active,
        }
        for p in prompts
    ]

    return JsonResponse({
        'category_name': category.name,
        'category_description': category.description,
        'prompts': prompts_data,
    })
