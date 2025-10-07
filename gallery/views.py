# gallery/views.py
from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST, require_http_methods
from django.conf import settings

from generate.models import GenerationJob
from .forms import ShareFromJobForm, PhotoCommentForm
from .models import (
    PublicPhoto,
    Category,
    PhotoLike,
    PhotoComment,
    CommentLike,
)

MIN_THUMB_SIZE = 1024  # 1 KiB — меньше считаем «пустышкой»


# ───────────────────────── helpers ─────────────────────────

def _ensure_session_key(request: HttpRequest) -> str:
    """Гарантируем наличие session_key, возвращаем его."""
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _guest_cookie_id(request: HttpRequest) -> str:
    """Получаем cookie 'gid' для гостя."""
    return (request.COOKIES.get("gid") or "").strip()


def _get_fp_from_request(request: HttpRequest) -> str:
    """Получаем fingerprint из cookie, заголовка или middleware."""
    # 1) middleware мог положить request.fp
    fp = getattr(request, "fp", "") or ""
    if fp:
        return fp.strip()

    # 2) cookie с фронта
    fp_cookie_name = getattr(settings, "FP_COOKIE_NAME", "aid_fp")
    fp = (request.COOKIES.get(fp_cookie_name) or "").strip()
    if fp:
        return fp

    # 3) заголовок (если фронт его шлёт)
    hdr = getattr(settings, "FP_HEADER_NAME", "X-Device-Fingerprint")
    fp = (request.META.get(f"HTTP_{hdr.upper().replace('-', '_')}", "") or "").strip()
    return fp


def _hard_fingerprint(request: HttpRequest) -> str:
    """Стабильный серверный fingerprint (fallback)."""
    import hashlib
    ua = (request.META.get("HTTP_USER_AGENT") or "").strip()
    ip = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip() or \
         (request.META.get("REMOTE_ADDR") or "")
    raw = f"{ua}|{ip}|{settings.SECRET_KEY}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _job_has_file(job: GenerationJob) -> bool:
    """Проверяем, что у задачи есть валидный файл результата."""
    f = getattr(job, "result_image", None)
    if not f or not getattr(f, "name", ""):
        return False
    try:
        if not default_storage.exists(f.name):
            return False
        return (default_storage.size(f.name) or 0) >= MIN_THUMB_SIZE
    except Exception:
        return False


def _mark_photo_viewed_once(_request: HttpRequest, photo_id: int) -> None:
    """Инкремент счётчика просмотров (простая модель, без дедупликации)."""
    PublicPhoto.objects.filter(pk=photo_id).update(view_count=F("view_count") + 1)


# ───────────────────────── LIST / INDEX ─────────────────────────

@require_http_methods(["GET", "POST"])
def index(request: HttpRequest) -> HttpResponse:
    """
    Главная галерея.
    Поддерживает админские POST-действия:
      - add_category  : создать категорию (name, slug?)
      - del_category  : удалить категорию (cat_id)
      - add_photo     : добавить публичное фото
    """
    # ───────── Админские POST-действия ─────────
    if request.method == "POST" and request.user.is_staff:
        action = (request.POST.get("action") or "").strip()

        if action == "add_category":
            name = (request.POST.get("cat_name") or "").strip()
            slug = (request.POST.get("cat_slug") or "").strip()

            if not name:
                messages.error(request, "Введите название категории.")
                return redirect("gallery:index")

            if not slug:
                slug = slugify(name)[:80]

            if Category.objects.filter(slug=slug).exists():
                messages.error(request, "Категория с таким слагом уже существует.")
                return redirect("gallery:index")

            Category.objects.create(name=name, slug=slug)
            messages.success(request, f"Категория «{name}» создана.")
            return redirect("gallery:index")

        elif action == "del_category":
            cat_id = request.POST.get("cat_id")
            try:
                cat = Category.objects.get(pk=cat_id)
            except (Category.DoesNotExist, ValueError, TypeError):
                messages.error(request, "Категория не найдена.")
                return redirect("gallery:index")

            name = cat.name
            cat.delete()
            messages.success(request, f"Категория «{name}» удалена.")
            return redirect("gallery:index")

        elif action == "add_photo":
            title = (request.POST.get("photo_title") or "").strip()
            desc = (request.POST.get("photo_desc") or "").strip()
            cat_id = request.POST.get("photo_category")
            is_public = bool(request.POST.get("photo_is_public"))
            file = request.FILES.get("photo_image")

            if not title:
                messages.error(request, "Введите заголовок.")
                return redirect("gallery:index")
            if not file:
                messages.error(request, "Загрузите файл изображения.")
                return redirect("gallery:index")
            if not (getattr(file, "content_type", "") or "").startswith("image/"):
                messages.error(request, "Можно загружать только изображения.")
                return redirect("gallery:index")

            photo = PublicPhoto.objects.create(
                image=file,
                title=title,
                caption=desc,
                uploaded_by=request.user,
                is_active=is_public,
            )

            try:
                cat = Category.objects.get(pk=cat_id) if cat_id else None
            except Category.DoesNotExist:
                cat = None

            if cat:
                if hasattr(photo, "category"):
                    photo.category = cat
                    photo.save(update_fields=["category"])
                elif hasattr(photo, "categories"):
                    photo.categories.add(cat)

            messages.success(request, "Фото добавлено в публичную ленту.")
            return redirect("gallery:index")

        # неизвестное действие
        messages.error(request, "Неизвестное действие.")
        return redirect("gallery:index")

    # ───────── Дальше — обычный GET ─────────
    if request.user.is_authenticated:
        my_thumbs = (
            GenerationJob.objects
            .filter(
                user=request.user,
                status__in=[GenerationJob.Status.DONE, GenerationJob.Status.PENDING_MODERATION]
            )
            .order_by("-created_at")[:6]
        )
    else:
        # Для гостей ищем по всем возможным идентификаторам
        from django.db.models import Q

        skey = _ensure_session_key(request)
        gid = _guest_cookie_id(request) or ""
        fp = _get_fp_from_request(request) or _hard_fingerprint(request)

        # Строим запрос с учетом всех идентификаторов
        q = Q(user__isnull=True, status__in=[GenerationJob.Status.DONE, GenerationJob.Status.PENDING_MODERATION])
        guest_filters = Q()

        if skey:
            guest_filters |= Q(guest_session_key=skey)
        if gid:
            guest_filters |= Q(guest_gid=gid)
        if fp:
            guest_filters |= Q(guest_fp=fp)

        # Если есть хотя бы один идентификатор, применяем фильтр
        if guest_filters:
            q &= guest_filters
        else:
            # Если нет идентификаторов, возвращаем пустой queryset
            q &= Q(pk__isnull=True)

        my_thumbs = (
            GenerationJob.objects
            .filter(q)
            .order_by("-created_at")[:6]
        )

    cat_slug = (request.GET.get("cat") or "").strip()
    categories = Category.objects.all()

    photos_qs = (
        PublicPhoto.objects.filter(is_active=True)
        .select_related("uploaded_by", "category")
        .order_by("order", "-created_at")
    )

    active_category = None
    if cat_slug:
        active_category = Category.objects.filter(slug=cat_slug).first()
        if active_category:
            if hasattr(PublicPhoto, "categories"):
                photos_qs = photos_qs.filter(categories__slug=cat_slug)
            else:
                photos_qs = photos_qs.filter(category__slug=cat_slug)

    paginator = Paginator(photos_qs, 6)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    # Определяем лайкнутые id на странице — для юзера и для гостя
    liked_photo_ids: set[int] = set()
    page_photo_ids = list(page_obj.object_list.values_list("id", flat=True)) if page_obj.object_list else []
    if page_photo_ids:
        if request.user.is_authenticated:
            liked_photo_ids = set(
                PhotoLike.objects.filter(
                    user=request.user, photo_id__in=page_photo_ids
                ).values_list("photo_id", flat=True)
            )
        else:
            skey = _ensure_session_key(request)
            liked_photo_ids = set(
                PhotoLike.objects.filter(
                    user__isnull=True, session_key=skey, photo_id__in=page_photo_ids
                ).values_list("photo_id", flat=True)
            )

    # Определяем статус публикации для my_thumbs
    published_job_ids = set()
    if my_thumbs:
        job_ids = [j.id for j in my_thumbs]
        published_job_ids = set(
            PublicPhoto.objects.filter(
                source_job__in=job_ids,
                is_active=True
            ).values_list("source_job_id", flat=True)
        )

    return render(
        request,
        "gallery/index.html",
        {
            "my_thumbs": my_thumbs,
            "published_job_ids": published_job_ids,
            "categories": categories,
            "active_category": active_category,
            "public_photos": page_obj.object_list,
            "page_obj": page_obj,
            "liked_photo_ids": liked_photo_ids,
            "cat_slug": cat_slug,
            "pending_count": PublicPhoto.objects.filter(is_active=False).count()
                if request.user.is_staff else 0,
        },
    )


# ───────────────────────── TRENDING ─────────────────────────
# /gallery/trending/?by=views|likes|new
def trending(request: HttpRequest) -> HttpResponse:
    """
    Тренды:
      - by=views : по просмотрам (за всё время)
      - by=likes : по количеству лайков
      - by=new   : «самые залайканные за 10 дней»
    """
    mode = (request.GET.get("by") or "views").lower()
    page_num = request.GET.get("page", 1)

    cache_key = f"trending_{mode}_{page_num}"
    cached_result = cache.get(cache_key)
    if cached_result and not settings.DEBUG:
        return cached_result

    now = timezone.now()

    base_qs = (
        PublicPhoto.objects.filter(is_active=True)
        .select_related("category", "uploaded_by")
        .only("id", "image", "title", "caption", "created_at", "view_count", "likes_count",
              "category__name", "uploaded_by__username")
    )

    if mode == "likes":
        photos_qs = base_qs.order_by("-likes_count", "-view_count", "-created_at")
    elif mode == "new":
        photos_qs = (
            base_qs.filter(created_at__gte=now - timedelta(days=10))
                   .order_by("-created_at", "-likes_count", "-view_count")
        )
    else:  # views
        photos_qs = base_qs.order_by("-view_count", "-likes_count", "-created_at")

    paginator = Paginator(photos_qs, 12)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    liked_photo_ids: set[int] = set()
    page_photo_ids = list(page_obj.object_list.values_list("id", flat=True)) if page_obj.object_list else []
    if page_photo_ids:
        if request.user.is_authenticated:
            liked_photo_ids = set(
                PhotoLike.objects.filter(
                    user=request.user, photo_id__in=page_photo_ids
                ).values_list("photo_id", flat=True)
            )
        else:
            skey = _ensure_session_key(request)
            liked_photo_ids = set(
                PhotoLike.objects.filter(
                    user__isnull=True, session_key=skey, photo_id__in=page_photo_ids
                ).values_list("photo_id", flat=True)
            )

    return render(
        request,
        "gallery/trending.html",
        {
            "trending_photos": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "active_mode": mode,
            "liked_photo_ids": liked_photo_ids,
        },
    )


def trending_snippet(request: HttpRequest) -> HttpResponse:
    """
    Возвращает HTML-фрагмент сетки трендов для подгрузки на главной странице без перехода.
    Поддерживает те же параметры, что и trending: by=views|likes|new, page (по умолчанию 1).
    """
    mode = (request.GET.get("by") or "likes").lower()  # для главной по умолчанию показываем лайки
    now = timezone.now()

    base_qs = (
        PublicPhoto.objects.filter(is_active=True)
        .select_related("category", "uploaded_by")
    )

    if mode == "likes":
        photos_qs = base_qs.order_by("-likes_count", "-view_count", "-created_at")
    elif mode == "new":
        photos_qs = (
            base_qs.filter(created_at__gte=now - timedelta(days=10))
                   .order_by("-created_at", "-likes_count", "-view_count")
        )
    else:  # views
        photos_qs = base_qs.order_by("-view_count", "-likes_count", "-created_at")

    paginator = Paginator(photos_qs, 8)  # на главной выводим 8 карточек
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    liked_photo_ids: set[int] = set()
    page_photo_ids = list(page_obj.object_list.values_list("id", flat=True)) if page_obj.object_list else []
    if page_photo_ids:
        if request.user.is_authenticated:
            liked_photo_ids = set(
                PhotoLike.objects.filter(
                    user=request.user, photo_id__in=page_photo_ids
                ).values_list("photo_id", flat=True)
            )
        else:
            skey = _ensure_session_key(request)
            liked_photo_ids = set(
                PhotoLike.objects.filter(
                    user__isnull=True, session_key=skey, photo_id__in=page_photo_ids
                ).values_list("photo_id", flat=True)
            )

    # Рендерим только сетку карточек, чтобы вставить внутрь контейнера на главной
    return render(
        request,
        "includes/trending_gallery_grid.html",
        {
            "trending_photos": page_obj.object_list,
            "active_mode": mode,
            "liked_photo_ids": liked_photo_ids,
        },
    )


# ───────────────────────── DETAIL (с инкрементом просмотров) ─────────────────────────

def photo_detail(request: HttpRequest, pk: int) -> HttpResponse:
    photo = get_object_or_404(
        PublicPhoto.objects.select_related("uploaded_by", "category"),
        pk=pk,
        is_active=True,
    )

    # инкремент view_count
    _ensure_session_key(request)
    _mark_photo_viewed_once(request, photo.pk)
    try:
        photo.refresh_from_db(fields=["view_count", "likes_count", "comments_count"])
    except Exception:
        pass

    # корневые комментарии
    comments = (
        photo.comments.select_related("user")
        .prefetch_related("replies__user", "likes")
        .filter(is_visible=True, parent__isnull=True)
        .order_by("created_at")
    )

    # «уже лайкнуто» — и для юзера, и для гостя
    liked = False
    if request.user.is_authenticated:
        liked = PhotoLike.objects.filter(user=request.user, photo=photo).exists()
    else:
        skey = _ensure_session_key(request)
        liked = PhotoLike.objects.filter(user__isnull=True, session_key=skey, photo=photo).exists()

    # Определяем лайкнутые комментарии для текущего пользователя/гостя
    liked_comment_ids: set[int] = set()
    all_comment_ids = []
    for c in comments:
        all_comment_ids.append(c.pk)
        for r in c.replies.all():
            all_comment_ids.append(r.pk)

    if all_comment_ids:
        if request.user.is_authenticated:
            liked_comment_ids = set(
                CommentLike.objects.filter(
                    user=request.user, comment_id__in=all_comment_ids
                ).values_list("comment_id", flat=True)
            )
        else:
            skey = _ensure_session_key(request)
            liked_comment_ids = set(
                CommentLike.objects.filter(
                    user__isnull=True, session_key=skey, comment_id__in=all_comment_ids
                ).values_list("comment_id", flat=True)
            )

    # ───────── Похожие изображения (по категории; фолбэк — топ по лайкам) ─────────
    try:
        related_photos = []
        base_qs = PublicPhoto.objects.filter(is_active=True).exclude(pk=photo.pk)
        # По категории
        if getattr(photo, "category_id", None):
            related_photos = list(
                base_qs.filter(category_id=photo.category_id)
                       .order_by("-likes_count", "-view_count", "-created_at")[:8]
            )
        # Фолбэк/дозаполнение до 8
        if len(related_photos) < 8:
            exclude_ids = [photo.pk] + [p.pk for p in related_photos]
            fill = list(
                PublicPhoto.objects.filter(is_active=True)
                .exclude(pk__in=exclude_ids)
                .order_by("-likes_count", "-view_count", "-created_at")[: 8 - len(related_photos)]
            )
            related_photos.extend(fill)
    except Exception:
        related_photos = []

    return render(
        request,
        "gallery/detail.html",
        {
            "photo": photo,
            "comments": comments,
            "liked": liked,
            "liked_comment_ids": liked_comment_ids,
            "comment_form": PhotoCommentForm(),
            "related_photos": related_photos,
        },
    )


# ───────────────────────── LIKE / UNLIKE (фото) ─────────────────────────

@require_POST
def photo_like(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Тоггл лайка фото для авторизованных и гостей.
    Счётчик likes_count у PublicPhoto изменяется атомарно, без скачков
    (с учётом консолидации гостевого лайка в пользовательский).
    """
    try:
        photo = PublicPhoto.objects.get(pk=pk, is_active=True)
    except PublicPhoto.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Photo not found"}, status=404)

    # Rate limiting for likes
    client_ip = request.META.get('REMOTE_ADDR', '')
    rate_key = f"like_rate_{client_ip}_{pk}"
    if cache.get(rate_key):
        return JsonResponse({"ok": False, "error": "Too many requests"}, status=429)
    cache.set(rate_key, True, 2)

    skey = _ensure_session_key(request)

    with transaction.atomic():
        delta = 0
        liked = False

        if request.user.is_authenticated:
            # Есть ли уже пользовательский лайк?
            existing = PhotoLike.objects.select_for_update().filter(photo=photo, user=request.user).first()
            if existing:
                existing.delete()
                delta -= 1
                liked = False
            else:
                # Консолидация: убираем гостевой лайк этой сессии (если был)
                removed_guest = 0
                if skey:
                    removed_guest = PhotoLike.objects.filter(
                        photo=photo, user__isnull=True, session_key=skey
                    ).delete()[0]
                # Создаём пользовательский
                PhotoLike.objects.create(photo=photo, user=request.user, session_key="")
                delta += 1
                # Компенсируем удалённый гостевой, чтобы общий счётчик не «скакал»
                delta -= removed_guest
                liked = True
        else:
            # гость: один лайк на (photo, session_key)
            if not skey:
                return JsonResponse({"ok": False, "error": "no-session"}, status=400)

            existing = PhotoLike.objects.select_for_update().filter(
                photo=photo, user__isnull=True, session_key=skey
            ).first()
            if existing:
                existing.delete()
                delta -= 1
                liked = False
            else:
                PhotoLike.objects.create(photo=photo, user=None, session_key=skey)
                delta += 1
                liked = True

        # Атомарно обновляем счётчик с защитой от отрицательных значений
        if delta != 0:
            PublicPhoto.objects.filter(pk=photo.pk).update(
                likes_count=Greatest(F("likes_count") + delta, Value(0))
            )

        # Берём актуальное значение из БД
        new_count = PublicPhoto.objects.filter(pk=photo.pk).values_list("likes_count", flat=True).first() or 0

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "liked": liked, "count": new_count})
    return redirect(
        request.META.get("HTTP_REFERER")
        or reverse("gallery:photo_detail", args=[pk])
    )


# ───────────────────────── LIKE / UNLIKE (комментарий) ─────────────────────────

@require_POST
def comment_like(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Тоггл лайка комментария (user/guest). Поддерживаем корректные счётчики.
    """
    comment = get_object_or_404(PhotoComment, pk=pk, is_visible=True)
    skey = _ensure_session_key(request)

    with transaction.atomic():
        delta = 0
        liked = False

        if request.user.is_authenticated:
            existing = CommentLike.objects.select_for_update().filter(comment=comment, user=request.user).first()
            if existing:
                existing.delete()
                delta -= 1
                liked = False
            else:
                # Консолидация гостевого лайка этой сессии (если есть)
                if skey:
                    CommentLike.objects.filter(comment=comment, user__isnull=True, session_key=skey).delete()
                CommentLike.objects.create(comment=comment, user=request.user, session_key="")
                delta += 1
                liked = True
        else:
            if not skey:
                return JsonResponse({"ok": False, "error": "no-session"}, status=400)
            existing = CommentLike.objects.select_for_update().filter(
                comment=comment, user__isnull=True, session_key=skey
            ).first()
            if existing:
                existing.delete()
                delta -= 1
                liked = False
            else:
                CommentLike.objects.create(comment=comment, user=None, session_key=skey)
                delta += 1
                liked = True

        # Атомарно обновляем denorm-счётчик на комментарии
        if delta != 0:
            PhotoComment.objects.filter(pk=comment.pk).update(
                likes_count=Greatest(F("likes_count") + delta, Value(0))
            )
        new_count = PhotoComment.objects.filter(pk=comment.pk).values_list("likes_count", flat=True).first() or 0

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "liked": liked, "count": new_count})
    return redirect(
        request.META.get("HTTP_REFERER")
        or reverse("gallery:photo_detail", args=[comment.photo_id])
    )


# ───────────────────────── ADD REPLY (комментарий) ─────────────────────────

@login_required
@require_POST
def comment_reply(request: HttpRequest, pk: int) -> HttpResponse:
    """Ответ на комментарий (дочерний коммент)."""
    parent = get_object_or_404(PhotoComment, pk=pk, is_visible=True)
    form = PhotoCommentForm(request.POST)
    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
        messages.error(request, "Введите корректный ответ.")
        return redirect(reverse("gallery:photo_detail", args=[parent.photo_id]))

    with transaction.atomic():
        PhotoComment.objects.create(
            photo=parent.photo,
            user=request.user,
            text=form.cleaned_data["text"],
            parent=parent,
        )
        # Инкремент счётчика комментариев на фото (учитываем и ответы)
        PublicPhoto.objects.filter(pk=parent.photo_id).update(
            comments_count=F("comments_count") + 1
        )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})

    return redirect(
        f"{reverse('gallery:photo_detail', args=[parent.photo_id])}#c{parent.pk}"
    )


# ───────────────────────── SHARE FROM JOB ─────────────────────────

@login_required
def share_from_job(request, job_id: int):
    job = get_object_or_404(
        GenerationJob.objects.select_related("user"),
        pk=job_id,
        user=request.user,
        status=GenerationJob.Status.DONE,
    )

    if not _job_has_file(job):
        messages.error(request, "У этой генерации нет готового изображения.")
        return redirect("dashboard:my_jobs")

    if request.method == "POST":
        form = ShareFromJobForm(request.POST)
        if form.is_valid():
            title   = form.cleaned_data.get("title", "")
            caption = form.cleaned_data.get("caption", "")

            # скопировать файл из job.result_image в публичную папку
            src_file = job.result_image
            src_name = src_file.name.rsplit("/", 1)[-1]
            dst_dir  = f"public/{job.created_at:%Y/%m}/"
            dst_path = default_storage.generate_filename(dst_dir + src_name)
            with default_storage.open(src_file.name, "rb") as fh:
                saved_name = default_storage.save(dst_path, ContentFile(fh.read()))

            # если не админ — уходит на модерацию
            will_publish_now = request.user.is_staff

            # создаём публикацию — ВАЖНО: без job=..., только source_job!
            photo = PublicPhoto.objects.create(
                image=saved_name,
                title=title,
                caption=caption,
                uploaded_by=request.user,
                is_active=will_publish_now,
                source_job=job,
            )

            # обновляем статус job на "Ожидает модерации" если не админ
            if not will_publish_now:
                job.status = GenerationJob.Status.PENDING_MODERATION
                job.save(update_fields=['status'])

            # категории (в форме — ModelMultipleChoiceField "categories")
            cats = form.cleaned_data.get("categories")
            if cats:
                if hasattr(photo, "categories"):
                    photo.categories.set(cats)           # если у тебя M2M
                elif hasattr(photo, "category"):
                    first = cats.first()
                    if first:
                        photo.category = first           # если у тебя FK
                        photo.save(update_fields=["category"])

            messages.success(
                request,
                "Работа опубликована в галерее." if will_publish_now
                else "Работа отправлена на модерацию. После проверки она появится в галерее."
            )
            return redirect("gallery:index")
    else:
        form = ShareFromJobForm(initial={"title": (job.prompt or "").strip()[:140], "caption": ""})

    return render(
        request,
        "gallery/share.html",
        {
            "form": form,
            "job": job,
            "thumb_url": getattr(job, "result_image", None) and job.result_image.url,
        },
    )


# ───────────────────────── МОДЕРАЦИЯ (только для staff) ─────────────────────────

@staff_member_required
def moderation(request: HttpRequest) -> HttpResponse:
    """Список работ, ожидающих публикации."""
    pendings = PublicPhoto.objects.filter(is_active=False).order_by("-created_at")
    return render(request, "gallery/moderation.html", {"pendings": pendings})


@staff_member_required
@require_POST
def moderation_approve(request: HttpRequest, pk: int) -> HttpResponse:
    photo = get_object_or_404(PublicPhoto, pk=pk, is_active=False)
    photo.is_active = True
    photo.save(update_fields=["is_active"])

    # обновляем статус связанного job обратно на DONE
    if photo.source_job and photo.source_job.status == GenerationJob.Status.PENDING_MODERATION:
        photo.source_job.status = GenerationJob.Status.DONE
        photo.source_job.save(update_fields=['status'])

    messages.success(request, f"Фото №{pk} опубликовано.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("gallery:moderation"))


@staff_member_required
@require_POST
def moderation_reject(request: HttpRequest, pk: int) -> HttpResponse:
    photo = get_object_or_404(PublicPhoto, pk=pk)

    # обновляем статус связанного job обратно на DONE
    if photo.source_job and photo.source_job.status == GenerationJob.Status.PENDING_MODERATION:
        photo.source_job.status = GenerationJob.Status.DONE
        photo.source_job.save(update_fields=['status'])

    try:
        if photo.image and photo.image.name:
            photo.image.delete(save=False)
    except Exception:
        pass
    photo.delete()
    messages.info(request, f"Фото №{pk} отклонено и удалено.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("gallery:moderation"))


# ───────────────────────── DELETE JOB (как было) ─────────────────────────

@login_required
@require_POST
def job_delete(request: HttpRequest, pk: int) -> HttpResponse:
    job = get_object_or_404(GenerationJob, pk=pk)

    if getattr(job, "is_public", False) and not request.user.is_staff:
        messages.error(request, "Публичные работы может удалять только администратор.")
        return redirect(request.POST.get("next") or "dashboard:my_jobs")

    if (job.user_id != request.user.id) and (not request.user.is_staff):
        messages.error(request, "Нет прав на удаление этой генерации.")
        return redirect(request.POST.get("next") or "dashboard:my_jobs")

    try:
        if getattr(job, "result_image", None) and job.result_image.name:
            job.result_image.delete(save=False)
    except Exception:
        pass

    job.delete()
    messages.success(request, f"Генерация #{pk} удалена.")
    return redirect(request.POST.get("next") or "dashboard:my_jobs")


# ───────────────────────── STAFF: ADD / DELETE ─────────────────────────

@staff_member_required
@require_POST
def public_add(request: HttpRequest) -> HttpResponse:
    file = request.FILES.get("image")
    title = (request.POST.get("title") or "").strip()
    caption = (request.POST.get("caption") or "").strip()

    if not file:
        messages.error(request, "Загрузите файл изображения.")
        return redirect("gallery:index")
    if not (getattr(file, "content_type", "") or "").startswith("image/"):
        messages.error(request, "Можно загружать только изображения.")
        return redirect("gallery:index")

    PublicPhoto.objects.create(
        image=file, title=title, caption=caption, uploaded_by=request.user
    )
    messages.success(request, "Фото добавлено в публичную ленту.")
    return redirect("gallery:index")


@staff_member_required
@require_POST
def public_delete(request: HttpRequest, pk: int) -> HttpResponse:
    p = get_object_or_404(PublicPhoto, pk=pk)
    try:
        if p.image and p.image.name:
            p.image.delete(save=False)
    except Exception:
        pass
    p.delete()
    messages.success(request, "Фото удалено из публичной ленты.")
    return redirect("gallery:index")


# ───────────────────────── STAFF: ADD CATEGORY (отдельный экран) ─────────────────────────

@staff_member_required
def category_add(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        slug = (request.POST.get("slug") or "").strip()
        order_raw = (request.POST.get("order") or "").strip()
        is_active = bool(request.POST.get("is_active"))

        if not name:
            messages.error(request, "Введите название категории.")
        else:
            if not slug:
                slug = slugify(name)[:80]
            try:
                order = int(order_raw or 0)
            except ValueError:
                order = 0

            if Category.objects.filter(slug=slug).exists():
                messages.error(request, "Категория с таким слагом уже существует.")
            else:
                Category.objects.create(
                    name=name, slug=slug, order=order, is_active=is_active
                )
                messages.success(request, f"Категория «{name}» создана.")
                return redirect("gallery:index")
    else:
        last = Category.objects.order_by("-order").first()
        next_order = (last.order + 1) if last else 0
        request.order_default = next_order

    return render(
        request,
        "gallery/category_form.html",
        {"order_default": getattr(request, "order_default", 0)},
    )


# Алиасы для admin-роутов в urls
admin_category_add = category_add
admin_public_add = public_add
admin_public_delete = public_delete


# ───────────────────────── STAFF: EDIT/DELETE PUBLIC PHOTO ─────────────────────────

@staff_member_required
@require_http_methods(["GET", "POST"])
def photo_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Мини-редактор публикации. Сохраняем только безопасные поля:
    title, caption, is_active, category (если поле существует у модели).
    """
    photo = get_object_or_404(PublicPhoto, pk=pk)
    next_url = request.GET.get("next") or reverse("gallery:photo_detail", args=[photo.pk])

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        caption = (request.POST.get("caption") or "").strip()
        is_active = bool(request.POST.get("is_active") == "on")
        cat_id = request.POST.get("category_id")

        update_fields: list[str] = []

        if hasattr(photo, "title"):
            photo.title = title
            update_fields.append("title")
        if hasattr(photo, "caption"):
            photo.caption = caption
            update_fields.append("caption")
        if hasattr(photo, "is_active"):
            photo.is_active = is_active
            update_fields.append("is_active")
        if hasattr(photo, "category"):
            if cat_id:
                try:
                    cat = Category.objects.get(pk=int(cat_id))
                    photo.category = cat
                    update_fields.append("category")
                except Exception:
                    pass

        if update_fields:
            photo.save(update_fields=update_fields)

        messages.success(request, "Публикация обновлена.")
        return redirect(next_url)

    return render(
        request,
        "gallery/photo_edit.html",
        {"photo": photo, "next": next_url},
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def photo_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Soft-delete: скрываем публикацию (is_active=False), не вызывая .delete(),
    чтобы обойти проблемы с moderation_* таблицами. Это безопасно и обратимо.
    """
    photo = get_object_or_404(PublicPhoto, pk=pk)
    next_url = request.GET.get("next") or reverse("gallery:index")

    if request.method == "POST":
        if hasattr(photo, "is_active"):
            photo.is_active = False
            photo.save(update_fields=["is_active"])
        messages.success(request, "Публикация скрыта из галереи.")
        return redirect(next_url)

    return render(
        request,
        "gallery/photo_confirm_delete.html",
        {"photo": photo, "next": next_url},
    )


# ───────────────────────── ADD ROOT COMMENT ─────────────────────────

@login_required
@require_POST
def photo_comment(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Добавить корневой комментарий к фото.
    Возвращает JSON для AJAX-запроса, иначе делает редирект обратно на детальную страницу.
    """
    photo = get_object_or_404(PublicPhoto, pk=pk, is_active=True)
    form = PhotoCommentForm(request.POST)
    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
        messages.error(request, "Введите корректный комментарий.")
        return redirect(reverse("gallery:photo_detail", args=[pk]))

    with transaction.atomic():
        PhotoComment.objects.create(
            photo=photo,
            user=request.user,
            text=form.cleaned_data["text"],
            parent=None,
        )
        # Инкремент счётчика комментариев у фото (учитываем и корневые, и ответы)
        PublicPhoto.objects.filter(pk=photo.pk).update(
            comments_count=F("comments_count") + 1
        )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})

    return redirect(reverse("gallery:photo_detail", args=[pk]))
