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
from django.db.models import F, Value, Case, When, IntegerField, Count, Exists, OuterRef, Q
from django.db.models.functions import Greatest
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST, require_http_methods
from django.conf import settings

from generate.models import GenerationJob
from .forms import SharePhotoFromJobForm, PhotoCommentForm
from .models import (
    PublicPhoto,
    Category,
    VideoCategory,
    PhotoLike,
    PhotoComment,
    CommentLike,
    Image,
    PublicVideo,
    VideoLike,
    PhotoSave,
    VideoSave,
)
from dashboard.models import Follow, Notification

import os
import tempfile
import subprocess
from django.core.files import File
import io
from PIL import Image

def _save_optimized_webp_bytes(data: bytes, subdir: str = "public", filename_base: str = "image") -> str:
    """
    Сжать байты изображения в WEBP и сохранить в сторадж проекта.
    - Конвертация в RGB
    - Даунскейл до макс 2048px по длинной стороне
    - WEBP quality=75, method=6 (лёгкий вес, хорошее качество)
    Возвращает storage name (относительный путь), не URL.
    """
    base = slugify(filename_base)[:60] or "image"
    im = Image.open(io.BytesIO(data))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    # Downscale
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
    # Encode WEBP
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=75, method=6)
    buf.seek(0)
    dst_dir = f"{subdir}/{timezone.now():%Y/%m}/"
    storage_name = default_storage.generate_filename(f"{dst_dir}{base}.webp")
    return default_storage.save(storage_name, ContentFile(buf.read()))

MIN_THUMB_SIZE = 1024  # 1 KiB — меньше считаем «пустышкой»


def _save_optimized_mp4(upload, subdir: str = "public_videos") -> str:
    """
    Сохраняет загруженный MP4 как оптимизированный файл:
    - H.264/AAC, faststart
    - ограничивает ширину до 1280px, CRF=28 для лёгкого веса
    - если ffmpeg недоступен — сохраняет как есть
    Возвращает публичный URL (storage.url).
    """
    # безопасное имя
    base = slugify(getattr(upload, "name", "video").rsplit(".", 1)[0])[
        :60] or "video"
    tmp_in = None
    tmp_out = None
    try:
        fd, tmp_in = tempfile.mkstemp(suffix=".mp4")
        with os.fdopen(fd, "wb") as fh:
            for chunk in upload.chunks():
                fh.write(chunk)
        tmp_out = tempfile.mktemp(suffix="-opt.mp4")
        cmd = [
            "ffmpeg", "-y", "-i", tmp_in,
            "-vf", "scale='min(1280,iw)':-2",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            tmp_out,
        ]
        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            final_path = tmp_out if os.path.exists(
                tmp_out) and os.path.getsize(tmp_out) > 0 else tmp_in
        except Exception:
            final_path = tmp_in
        # сохраняем в сторадж
        dst_dir = f"{subdir}/{timezone.now():%Y/%m}/"
        filename = f"{base}.mp4"
        storage_name = default_storage.generate_filename(dst_dir + filename)
        with open(final_path, "rb") as fobj:
            storage_name = default_storage.save(storage_name, File(fobj))
        return default_storage.url(storage_name)
    finally:
        try:
            if tmp_in and os.path.exists(tmp_in):
                os.remove(tmp_in)
        except Exception:
            pass
        try:
            if tmp_out and os.path.exists(tmp_out):
                os.remove(tmp_out)
        except Exception:
            pass


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
    fp = (request.META.get(
        f"HTTP_{hdr.upper().replace('-', '_')}", "") or "").strip()
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
    PublicPhoto.objects.filter(pk=photo_id).update(
        view_count=F("view_count") + 1)


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
                messages.error(
                    request, "Категория с таким слагом уже существует.")
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

            # Сохранить изображение как WEBP в медиа-папку проекта
            try:
                data = file.read()
                saved_name = _save_optimized_webp_bytes(
                    data,
                    subdir="public",
                    filename_base=(title or getattr(file, "name", "image"))
                )
            except Exception:
                # Фолбэк: сохранить исходник как есть
                try:
                    dst_dir = f"public/{timezone.now():%Y/%m}/"
                    storage_name = default_storage.generate_filename(
                        dst_dir + (getattr(file, "name", "image.jpg")))
                    saved_name = default_storage.save(
                        storage_name,
                        ContentFile(data if 'data' in locals() and data else file.read())
                    )
                except Exception:
                    saved_name = default_storage.save(getattr(file, "name", "image.jpg"), file)

            photo = PublicPhoto.objects.create(
                image=saved_name,
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

        elif action == "add_video":
            title = (request.POST.get("video_title") or "").strip()
            desc = (request.POST.get("video_desc") or "").strip()
            cat_id = request.POST.get("video_category")
            is_public = bool(request.POST.get("video_is_public"))
            video_file = request.FILES.get("video_file")
            thumbnail_file = request.FILES.get("video_thumbnail")

            if not title:
                messages.error(request, "Введите заголовок видео.")
                return redirect("gallery:index")
            if not video_file:
                messages.error(request, "Загрузите MP4 файл.")
                return redirect("gallery:index")
            ctype = (getattr(video_file, "content_type", "") or "").lower()
            if "mp4" not in ctype and not (getattr(video_file, "name", "").lower().endswith(".mp4")):
                messages.error(request, "Поддерживается только MP4.")
                return redirect("gallery:index")

            try:
                optimized_url = _save_optimized_mp4(video_file)
            except Exception:
                # Фолбэк — сохраняем исходник как есть
                dst_dir = f"public_videos/{timezone.now():%Y/%m}/"
                storage_name = default_storage.generate_filename(
                    dst_dir + (getattr(video_file, "name", "video.mp4")))
                storage_name = default_storage.save(storage_name, video_file)
                optimized_url = default_storage.url(storage_name)

            video = PublicVideo.objects.create(
                video_url=optimized_url,
                thumbnail=thumbnail_file,
                title=title,
                caption=desc,
                uploaded_by=request.user,
                is_active=is_public,
            )

            try:
                cat = VideoCategory.objects.get(pk=cat_id) if cat_id else None
            except VideoCategory.DoesNotExist:
                cat = None

            if cat and hasattr(video, "category"):
                video.category = cat
                video.save(update_fields=["category"])

            messages.success(request, "Видео добавлено в публичную ленту.")
            return redirect("gallery:index")

        elif action == "add_video_category":
            name = (request.POST.get("video_cat_name") or "").strip()
            slug = (request.POST.get("video_cat_slug") or "").strip()

            if not name:
                messages.error(request, "Введите название категории видео.")
                return redirect("gallery:index")

            if not slug:
                slug = slugify(name)[:80]

            if VideoCategory.objects.filter(slug=slug).exists():
                messages.error(
                    request, "Категория видео с таким слагом уже существует.")
                return redirect("gallery:index")

            VideoCategory.objects.create(name=name, slug=slug)
            messages.success(request, f"Категория видео «{name}» создана.")
            return redirect("gallery:index")

        elif action == "del_video_category":
            cat_id = request.POST.get("video_cat_id")
            try:
                cat = VideoCategory.objects.get(pk=cat_id)
            except (VideoCategory.DoesNotExist, ValueError, TypeError):
                messages.error(request, "Категория видео не найдена.")
                return redirect("gallery:index")

            name = cat.name
            cat.delete()
            messages.success(request, f"Категория видео «{name}» удалена.")
            return redirect("gallery:index")

        # неизвестное действие
        messages.error(request, "Неизвестное действие.")
        return redirect("gallery:index")

    # ───────── Дальше — обычный GET ─────────
    # ФОТО: только изображения (НЕ видео)
    if request.user.is_authenticated:
        # Общее количество фото (как в my-jobs)
        my_photos_total = (
            GenerationJob.objects
            .filter(
                user=request.user,
                status__in=[GenerationJob.Status.DONE,
                            GenerationJob.Status.PENDING_MODERATION]
            )
            .exclude(generation_type='video')
            .filter(persisted=True)
            .count()
        )

        # Берем только 6 для отображения
        my_thumbs = (
            GenerationJob.objects
            .filter(
                user=request.user,
                status__in=[GenerationJob.Status.DONE,
                            GenerationJob.Status.PENDING_MODERATION]
            )
            .exclude(generation_type='video')
            .filter(persisted=True)
            .order_by("-created_at")[:6]
        )
    else:
        # Для гостей ищем по всем возможным идентификаторам
        from django.db.models import Q

        skey = _ensure_session_key(request)
        gid = _guest_cookie_id(request) or ""
        fp = _get_fp_from_request(request) or _hard_fingerprint(request)

        # Строим запрос с учетом всех идентификаторов
        q = Q(user__isnull=True, status__in=[
              GenerationJob.Status.DONE, GenerationJob.Status.PENDING_MODERATION])
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

        # Общее количество фото для гостей
        my_photos_total = GenerationJob.objects.filter(
            q).exclude(generation_type='video').filter(persisted=True).count()

        # Берем только 6 для отображения
        my_thumbs = (
            GenerationJob.objects
            .filter(q)
            .exclude(generation_type='video')
            .filter(persisted=True)
            .order_by("-created_at")[:6]
        )

    cat_slug = (request.GET.get("cat") or "").strip()
    vcat_slug = (request.GET.get("vcat") or "").strip()
    vcat_id_raw = request.GET.get("vcat_id")
    categories = Category.objects.all()
    video_categories = VideoCategory.objects.all()

    # ПУБЛИЧНЫЕ ФОТО
    photos_qs = (
        PublicPhoto.objects.filter(is_active=True)
        .annotate(saves_count=Count("saves", distinct=True))
        .select_related("uploaded_by", "category")
        .order_by("order", "-created_at")
    )

    # ПУБЛИЧНЫЕ ВИДЕО
    videos_qs = (
        PublicVideo.objects.filter(is_active=True)
        .annotate(saves_count=Count("saves", distinct=True))
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

    # Video category filtering (independent from photo category)
    active_video_category = None
    # Prefer explicit vcat_id if provided (robust even if some categories have empty slug)
    if vcat_id_raw:
        try:
            vcat_id = int(vcat_id_raw)
        except (TypeError, ValueError):
            vcat_id = None
        if vcat_id:
            active_video_category = VideoCategory.objects.filter(pk=vcat_id).first()
            if active_video_category:
                # Keep slug in sync for templates / JS helpers
                if not vcat_slug:
                    vcat_slug = active_video_category.slug or ""
                videos_qs = videos_qs.filter(category=active_video_category)
    elif vcat_slug:
        active_video_category = VideoCategory.objects.filter(slug=vcat_slug).first()
        if active_video_category:
            videos_qs = videos_qs.filter(category__slug=vcat_slug)

    # Hide publications linked to hidden source jobs (not visible to others)
    try:
        from .models import JobHide
        # Determine relation name on PublicPhoto dynamically: source_job or job
        pf_names = {f.name for f in PublicPhoto._meta.get_fields()}
        photo_rel_id = "source_job_id" if "source_job" in pf_names else (
            "job_id" if "job" in pf_names else None)
        if photo_rel_id:
            photos_qs = photos_qs.annotate(
                hidden_by_owner=Exists(
                    JobHide.objects.filter(user=OuterRef(
                        "uploaded_by_id"), job_id=OuterRef(photo_rel_id))
                )
            )
        videos_qs = videos_qs.annotate(
            hidden_by_owner=Exists(
                JobHide.objects.filter(user=OuterRef(
                    "uploaded_by_id"), job_id=OuterRef("source_job_id"))
            )
        )
        if request.user.is_authenticated:
            if photo_rel_id:
                photos_qs = photos_qs.filter(
                    Q(hidden_by_owner=False) | Q(uploaded_by_id=request.user.id))
            videos_qs = videos_qs.filter(
                Q(hidden_by_owner=False) | Q(uploaded_by_id=request.user.id))
        else:
            if photo_rel_id:
                photos_qs = photos_qs.filter(hidden_by_owner=False)
            videos_qs = videos_qs.filter(hidden_by_owner=False)
    except Exception:
        pass

    # Instagram-like feed ordering for authenticated users:
    #  - first show posts from followings
    #  - then recommendations (others), keeping overall recency/popularity order
    if request.user.is_authenticated:
        try:
            followed_ids = list(Follow.objects.filter(
                follower=request.user).values_list("following_id", flat=True))
        except Exception:
            followed_ids = []

        if followed_ids:
            photos_qs = photos_qs.annotate(
                feed_priority=Case(
                    When(uploaded_by_id__in=followed_ids, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            ).order_by("feed_priority", "-created_at", "-likes_count", "-view_count")

            videos_qs = videos_qs.annotate(
                feed_priority=Case(
                    When(uploaded_by_id__in=followed_ids, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            ).order_by("feed_priority", "-created_at", "-likes_count", "-view_count")

    paginator = Paginator(photos_qs, 500)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    videos_paginator = Paginator(videos_qs, 500)
    videos_page_obj = videos_paginator.get_page(request.GET.get("vpage") or 1)

    # Определяем лайкнутые ФОТО на странице
    liked_photo_ids: set[int] = set()
    page_photo_ids = list(page_obj.object_list.values_list(
        "id", flat=True)) if page_obj.object_list else []
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

    # Определяем сохранённые ФОТО на странице (только для авторизованных)
    saved_photo_ids: set[int] = set()
    if page_photo_ids and request.user.is_authenticated:
        saved_photo_ids = set(
            PhotoSave.objects.filter(
                user=request.user, photo_id__in=page_photo_ids)
            .values_list("photo_id", flat=True)
        )

    # Определяем лайкнутые ВИДЕО на странице
    liked_video_ids: set[int] = set()
    page_video_ids = list(videos_page_obj.object_list.values_list(
        "id", flat=True)) if videos_page_obj.object_list else []
    if page_video_ids:
        if request.user.is_authenticated:
            liked_video_ids = set(
                VideoLike.objects.filter(
                    user=request.user, video_id__in=page_video_ids
                ).values_list("video_id", flat=True)
            )
        else:
            skey = _ensure_session_key(request)
            liked_video_ids = set(
                VideoLike.objects.filter(
                    user__isnull=True, session_key=skey, video_id__in=page_video_ids
                ).values_list("video_id", flat=True)
            )

    # Определяем сохранённые ВИДЕО на странице (только для авторизованных)
    saved_video_ids: set[int] = set()
    if page_video_ids and request.user.is_authenticated:
        saved_video_ids = set(
            VideoSave.objects.filter(
                user=request.user, video_id__in=page_video_ids)
            .values_list("video_id", flat=True)
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

    # Получаем видео для пользователя С ПРЕВЬЮ
    my_videos = []
    my_videos_total = 0
    if request.user.is_authenticated:
        # Общее количество видео (как в my-jobs)
        my_videos_total = (
            GenerationJob.objects
            .filter(
                user=request.user,
                generation_type='video',
                status__in=[GenerationJob.Status.DONE,
                            GenerationJob.Status.PENDING_MODERATION]
            )
            .filter(persisted=True)
            .count()
        )

        # ВАЖНО: формируем список из GenerationJob, чтобы удалённые в my_jobs не попадали в «Мои генерации»
        video_jobs = (
            GenerationJob.objects
            .filter(
                user=request.user,
                generation_type='video',
                status__in=[GenerationJob.Status.DONE,
                            GenerationJob.Status.PENDING_MODERATION]
            )
            .filter(persisted=True)
            .select_related("video_model")
            .order_by("-created_at")[:6]
        )
        my_videos = [
            {
                'id': job.id,
                'video_url': (job.result_video_url or ''),
                'thumbnail_url': (job.result_image.url if job.result_image else None),
                'prompt': job.prompt,
                'created_at': job.created_at,
                'model_id': job.model_id,
                'video_model': job.video_model,
            }
            for job in video_jobs if job.result_video_url
        ]
    else:
        # Для гостей ищем видео по идентификаторам через GenerationJob
        from django.db.models import Q
        skey = _ensure_session_key(request)
        gid = _guest_cookie_id(request) or ""
        fp = _get_fp_from_request(request) or _hard_fingerprint(request)

        q = Q(user__isnull=True, generation_type='video', status__in=[
              GenerationJob.Status.DONE, GenerationJob.Status.PENDING_MODERATION])
        guest_filters = Q()

        if skey:
            guest_filters |= Q(guest_session_key=skey)
        if gid:
            guest_filters |= Q(guest_gid=gid)
        if fp:
            guest_filters |= Q(guest_fp=fp)

        if guest_filters:
            q &= guest_filters
        else:
            q &= Q(pk__isnull=True)

        # Общее количество видео для гостей
        my_videos_total = GenerationJob.objects.filter(q).filter(persisted=True).count()

        video_jobs = (
            GenerationJob.objects
            .filter(q)
            .filter(persisted=True)
            .select_related("video_model")
            .order_by("-created_at")[:6]
        )
        my_videos = [
            {
                'id': job.id,
                'video_url': job.result_video_url,
                'thumbnail_url': (job.result_image.url if job.result_image else None),
                'prompt': job.prompt,
                'created_at': job.created_at,
                'model_id': job.model_id,
                'video_model': job.video_model,
            }
            for job in video_jobs if job.result_video_url
        ]

    return render(
        request,
        "gallery/index.html",
        {
            "my_thumbs": my_thumbs,
            "my_photos_total": my_photos_total,
            "my_videos": my_videos,
            "my_videos_total": my_videos_total,
            "published_job_ids": published_job_ids,
            "categories": categories,
            "video_categories": video_categories,
            "active_category": active_category,
            "active_video_category": active_video_category,
            "public_photos": page_obj.object_list,
            "page_obj": page_obj,
            "liked_photo_ids": liked_photo_ids,
            "saved_photo_ids": saved_photo_ids,
            "public_videos": videos_page_obj.object_list,
            "videos_page_obj": videos_page_obj,
            "liked_video_ids": liked_video_ids,
            "saved_video_ids": saved_video_ids,
            "cat_slug": cat_slug,
            "vcat_slug": vcat_slug,
            "pending_count": PublicPhoto.objects.filter(is_active=False).count()
            if request.user.is_staff else 0,
            "pending_videos_count": PublicVideo.objects.filter(is_active=False).count()
            if request.user.is_staff else 0,
        },
    )


# ───────────────────────── TRENDING ─────────────────────────
def trending(request: HttpRequest) -> HttpResponse:
    """
    Тренды:
      - by=views : по просмотрам (за всё время)
      - by=likes : по количеству лайков
      - by=new   : «самые залайканные за 10 дней»
    """
    mode = (request.GET.get("by") or "views").lower()
    page_num = request.GET.get("page", 1)

    user_key = f"u{request.user.id}" if request.user.is_authenticated else "anon"
    cache_key = f"trending_{mode}_{page_num}_{user_key}"
    cached_result = cache.get(cache_key)
    if cached_result and not settings.DEBUG:
        return cached_result

    now = timezone.now()

    base_qs = (
        PublicPhoto.objects.filter(is_active=True)
        .annotate(saves_count=Count("saves", distinct=True))
        .select_related("category", "uploaded_by")
        .only("id", "image", "title", "caption", "created_at", "view_count", "likes_count",
              "category__name", "uploaded_by__username")
    )
    # Hide publications with hidden source jobs (not visible to others)
    try:
        from .models import JobHide
        # Detect relation name dynamically on PublicPhoto
        pf_names = {f.name for f in PublicPhoto._meta.get_fields()}
        photo_rel_id = "source_job_id" if "source_job" in pf_names else (
            "job_id" if "job" in pf_names else None)
        if photo_rel_id:
            base_qs = base_qs.annotate(
                hidden_by_owner=Exists(
                    JobHide.objects.filter(user=OuterRef(
                        "uploaded_by_id"), job_id=OuterRef(photo_rel_id))
                )
            )
            if request.user.is_authenticated:
                base_qs = base_qs.filter(Q(hidden_by_owner=False) | Q(
                    uploaded_by_id=request.user.id))
            else:
                base_qs = base_qs.filter(hidden_by_owner=False)
    except Exception:
        pass

    if mode == "likes":
        photos_qs = base_qs.order_by(
            "-likes_count", "-view_count", "-created_at")
    elif mode == "new":
        photos_qs = (
            base_qs.filter(created_at__gte=now - timedelta(days=10))
                   .order_by("-created_at", "-likes_count", "-view_count")
        )
    else:  # views
        photos_qs = base_qs.order_by(
            "-view_count", "-likes_count", "-created_at")

    paginator = Paginator(photos_qs, 500)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    liked_photo_ids: set[int] = set()
    page_photo_ids = list(page_obj.object_list.values_list(
        "id", flat=True)) if page_obj.object_list else []
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
    # Saved photos on page (for initial bookmark state)
    saved_photo_ids: set[int] = set()
    if page_photo_ids and request.user.is_authenticated:
        saved_photo_ids = set(
            PhotoSave.objects.filter(
                user=request.user, photo_id__in=page_photo_ids)
            .values_list("photo_id", flat=True)
        )

    # Precompute all photo modes for in-place switching (no network on click)
    photos_views_qs = base_qs.order_by("-view_count", "-likes_count", "-created_at")
    photos_likes_qs = base_qs.order_by("-likes_count", "-view_count", "-created_at")
    photos_new_qs = base_qs.filter(created_at__gte=now - timedelta(days=10)).order_by("-created_at", "-likes_count", "-view_count")

    def _ids_for_photos(qs):
        ids = list(qs.values_list("id", flat=True)[:500])
        _liked = set()
        _saved = set()
        if ids:
            if request.user.is_authenticated:
                _liked = set(PhotoLike.objects.filter(user=request.user, photo_id__in=ids).values_list("photo_id", flat=True))
                _saved = set(PhotoSave.objects.filter(user=request.user, photo_id__in=ids).values_list("photo_id", flat=True))
            else:
                skey2 = _ensure_session_key(request)
                _liked = set(PhotoLike.objects.filter(user__isnull=True, session_key=skey2, photo_id__in=ids).values_list("photo_id", flat=True))
        return ids, _liked, _saved

    ids_v, liked_photo_ids_views, saved_photo_ids_views = _ids_for_photos(photos_views_qs)
    ids_l, liked_photo_ids_likes, saved_photo_ids_likes = _ids_for_photos(photos_likes_qs)
    ids_n, liked_photo_ids_new, saved_photo_ids_new = _ids_for_photos(photos_new_qs)

    photos_views = list(photos_views_qs.filter(id__in=ids_v))
    photos_likes = list(photos_likes_qs.filter(id__in=ids_l))
    photos_new = list(photos_new_qs.filter(id__in=ids_n))

    # Precompute all video modes for in-place switching
    videos_base_qs = (
        PublicVideo.objects.filter(is_active=True)
        .annotate(saves_count=Count("saves", distinct=True))
        .select_related("category", "uploaded_by")
        .only(
            "id",
            "thumbnail",
            "video_url",
            "title",
            "caption",
            "created_at",
            "view_count",
            "likes_count",
            "category__name",
            "uploaded_by__username",
        )
    )
    try:
        from .models import JobHide
        videos_base_qs = videos_base_qs.annotate(
            hidden_by_owner=Exists(
                JobHide.objects.filter(user=OuterRef("uploaded_by_id"), job_id=OuterRef("source_job_id"))
            )
        )
        if request.user.is_authenticated:
            videos_base_qs = videos_base_qs.filter(Q(hidden_by_owner=False) | Q(uploaded_by_id=request.user.id))
        else:
            videos_base_qs = videos_base_qs.filter(hidden_by_owner=False)
    except Exception:
        pass

    videos_views_qs = videos_base_qs.order_by("-view_count", "-likes_count", "-created_at")
    videos_likes_qs = videos_base_qs.order_by("-likes_count", "-view_count", "-created_at")
    videos_new_qs = videos_base_qs.filter(created_at__gte=now - timedelta(days=10)).order_by("-created_at", "-likes_count", "-view_count")

    def _ids_for_videos(qs):
        ids = list(qs.values_list("id", flat=True)[:500])
        _liked = set()
        _saved = set()
        if ids:
            if request.user.is_authenticated:
                _liked = set(VideoLike.objects.filter(user=request.user, video_id__in=ids).values_list("video_id", flat=True))
                _saved = set(VideoSave.objects.filter(user=request.user, video_id__in=ids).values_list("video_id", flat=True))
            else:
                skey2 = _ensure_session_key(request)
                _liked = set(VideoLike.objects.filter(user__isnull=True, session_key=skey2, video_id__in=ids).values_list("video_id", flat=True))
        return ids, _liked, _saved

    vids_v, liked_video_ids_views, saved_video_ids_views = _ids_for_videos(videos_views_qs)
    vids_l, liked_video_ids_likes, saved_video_ids_likes = _ids_for_videos(videos_likes_qs)
    vids_n, liked_video_ids_new, saved_video_ids_new = _ids_for_videos(videos_new_qs)

    videos_views = list(videos_views_qs.filter(id__in=vids_v))
    videos_likes = list(videos_likes_qs.filter(id__in=vids_l))
    videos_new = list(videos_new_qs.filter(id__in=vids_n))

    return render(
        request,
        "gallery/trending.html",
        {
            # Current (for initial view/render)
            "trending_photos": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "active_mode": mode,
            "liked_photo_ids": liked_photo_ids,
            "saved_photo_ids": saved_photo_ids,

            # Pre-rendered photos (all modes)
            "photos_views": photos_views,
            "photos_likes": photos_likes,
            "photos_new": photos_new,
            "liked_photo_ids_views": liked_photo_ids_views,
            "liked_photo_ids_likes": liked_photo_ids_likes,
            "liked_photo_ids_new": liked_photo_ids_new,
            "saved_photo_ids_views": saved_photo_ids_views,
            "saved_photo_ids_likes": saved_photo_ids_likes,
            "saved_photo_ids_new": saved_photo_ids_new,

            # Pre-rendered videos (all modes)
            "videos_views": videos_views,
            "videos_likes": videos_likes,
            "videos_new": videos_new,
            "liked_video_ids_views": liked_video_ids_views,
            "liked_video_ids_likes": liked_video_ids_likes,
            "liked_video_ids_new": liked_video_ids_new,
            "saved_video_ids_views": saved_video_ids_views,
            "saved_video_ids_likes": saved_video_ids_likes,
            "saved_video_ids_new": saved_video_ids_new,
        },
    )


def trending_snippet(request: HttpRequest) -> HttpResponse:
    """
    Возвращает HTML-фрагмент сетки трендов для подгрузки на главной странице без перехода.
    Поддерживает параметры: by=views|likes|new.
    Выводим смешанную ленту (фото + видео) с тем же режимом сортировки.
    """
    mode = (request.GET.get("by") or "likes").lower()
    now = timezone.now()

    # Photos base
    photos_base_qs = (
        PublicPhoto.objects.filter(is_active=True)
        .annotate(saves_count=Count("saves", distinct=True))
        .select_related("category", "uploaded_by")
    )
    # Hide hidden-by-owner photos
    try:
        from .models import JobHide
        pf_names = {f.name for f in PublicPhoto._meta.get_fields()}
        photo_rel_id = "source_job_id" if "source_job" in pf_names else (
            "job_id" if "job" in pf_names else None)
        if photo_rel_id:
            photos_base_qs = photos_base_qs.annotate(
                hidden_by_owner=Exists(
                    JobHide.objects.filter(user=OuterRef("uploaded_by_id"), job_id=OuterRef(photo_rel_id))
                )
            )
            if request.user.is_authenticated:
                photos_base_qs = photos_base_qs.filter(Q(hidden_by_owner=False) | Q(uploaded_by_id=request.user.id))
            else:
                photos_base_qs = photos_base_qs.filter(hidden_by_owner=False)
    except Exception:
        pass

    if mode == "likes":
        photos_qs = photos_base_qs.order_by("-likes_count", "-view_count", "-created_at")
    elif mode == "new":
        photos_qs = photos_base_qs.filter(created_at__gte=now - timedelta(days=10)).order_by("-created_at", "-likes_count", "-view_count")
    else:  # views
        photos_qs = photos_base_qs.order_by("-view_count", "-likes_count", "-created_at")

    # Videos base
    videos_base_qs = (
        PublicVideo.objects.filter(is_active=True)
        .annotate(saves_count=Count("saves", distinct=True))
        .select_related("category", "uploaded_by")
    )
    try:
        from .models import JobHide
        videos_base_qs = videos_base_qs.annotate(
            hidden_by_owner=Exists(
                JobHide.objects.filter(user=OuterRef("uploaded_by_id"), job_id=OuterRef("source_job_id"))
            )
        )
        if request.user.is_authenticated:
            videos_base_qs = videos_base_qs.filter(Q(hidden_by_owner=False) | Q(uploaded_by_id=request.user.id))
        else:
            videos_base_qs = videos_base_qs.filter(hidden_by_owner=False)
    except Exception:
        pass

    if mode == "likes":
        videos_qs = videos_base_qs.order_by("-likes_count", "-view_count", "-created_at")
    elif mode == "new":
        videos_qs = videos_base_qs.filter(created_at__gte=now - timedelta(days=10)).order_by("-created_at", "-likes_count", "-view_count")
    else:
        videos_qs = videos_base_qs.order_by("-view_count", "-likes_count", "-created_at")

    # Pick top items and mix
    photos_list = list(photos_qs[:8])
    videos_list = list(videos_qs[:8])

    def _mix_lists(a, b, limit=8):
        out = []
        i = j = 0
        while len(out) < limit and (i < len(a) or j < len(b)):
            if i < len(a):
                out.append({"kind": "photo", "obj": a[i]})
                i += 1
                if len(out) >= limit:
                    break
            if j < len(b):
                out.append({"kind": "video", "obj": b[j]})
                j += 1
        return out

    trending_items = _mix_lists(photos_list, videos_list, 8)

    # Liked sets for current page items
    liked_photo_ids: set[int] = set()
    page_photo_ids = [p.id for p in photos_list]
    if page_photo_ids:
        if request.user.is_authenticated:
            liked_photo_ids = set(
                PhotoLike.objects.filter(user=request.user, photo_id__in=page_photo_ids).values_list("photo_id", flat=True)
            )
        else:
            skey = _ensure_session_key(request)
            liked_photo_ids = set(
                PhotoLike.objects.filter(user__isnull=True, session_key=skey, photo_id__in=page_photo_ids).values_list("photo_id", flat=True)
            )

    liked_video_ids: set[int] = set()
    page_video_ids = [v.id for v in videos_list]
    if page_video_ids:
        if request.user.is_authenticated:
            liked_video_ids = set(
                VideoLike.objects.filter(user=request.user, video_id__in=page_video_ids).values_list("video_id", flat=True)
            )
        else:
            skey = _ensure_session_key(request)
            liked_video_ids = set(
                VideoLike.objects.filter(user__isnull=True, session_key=skey, video_id__in=page_video_ids).values_list("video_id", flat=True)
            )

    return render(
        request,
        "includes/trending_gallery_grid.html",
        {
            "trending_items": trending_items,
            "active_mode": mode,
            "liked_photo_ids": liked_photo_ids,
            "liked_video_ids": liked_video_ids,
        },
    )


# ───────────────────────── DETAIL (с инкрементом просмотров) ─────────────────────────

def photo_detail(request: HttpRequest, pk: int) -> HttpResponse:
    photo = get_object_or_404(
        PublicPhoto.objects.select_related("uploaded_by", "category"),
        pk=pk,
        is_active=True,
    )
    # Canonicalize: always redirect legacy /gallery/photo/<pk> to slug URL /gallery/<slug>
    if getattr(photo, "slug", None):
        return redirect(photo.get_absolute_url())

    # Respect owner's hide setting: hidden publications are not visible to others
    try:
        from .models import JobHide
        job_id = getattr(photo, "source_job_id", None)
        if job_id is None:
            job_id = getattr(photo, "job_id", None)
        if job_id:
            is_hidden = JobHide.objects.filter(
                user=photo.uploaded_by, job_id=job_id).exists()
            if is_hidden and (not request.user.is_authenticated or request.user.id != photo.uploaded_by_id):
                from django.http import Http404
                raise Http404()
    except Exception:
        pass

    # инкремент view_count
    _ensure_session_key(request)
    _mark_photo_viewed_once(request, photo.pk)
    try:
        photo.refresh_from_db(
            fields=["view_count", "likes_count", "comments_count"])
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
        liked = PhotoLike.objects.filter(
            user=request.user, photo=photo).exists()
    else:
        skey = _ensure_session_key(request)
        liked = PhotoLike.objects.filter(
            user__isnull=True, session_key=skey, photo=photo).exists()

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
        # Исключаем скрытые работы владельца (JobHide)
        try:
            from .models import JobHide
            from django.db.models import Exists, OuterRef, Q
            base_qs = base_qs.annotate(
                hidden_by_owner=Exists(
                    JobHide.objects.filter(user=OuterRef("uploaded_by_id"), job_id=OuterRef("source_job_id"))
                )
            )
            if request.user.is_authenticated:
                base_qs = base_qs.filter(Q(hidden_by_owner=False) | Q(uploaded_by_id=request.user.id))
            else:
                base_qs = base_qs.filter(hidden_by_owner=False)
        except Exception:
            pass
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

    # Проверяем лайки для похожих фото (важно для гостей!)
    liked_photo_ids: set[int] = set()
    related_photo_ids = [p.id for p in related_photos]
    if related_photo_ids:
        if request.user.is_authenticated:
            liked_photo_ids = set(
                PhotoLike.objects.filter(
                    user=request.user, photo_id__in=related_photo_ids
                ).values_list("photo_id", flat=True)
            )
        else:
            skey = _ensure_session_key(request)
            liked_photo_ids = set(
                PhotoLike.objects.filter(
                    user__isnull=True, session_key=skey, photo_id__in=related_photo_ids
                ).values_list("photo_id", flat=True)
            )

    return render(
        request,
        "gallery/detail.html",
        {
            "photo": photo,
            "comments": comments,
            "liked": liked,
            "liked_comment_ids": liked_comment_ids,
            "liked_photo_ids": liked_photo_ids,
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
            existing = PhotoLike.objects.select_for_update().filter(
                photo=photo, user=request.user).first()
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
                PhotoLike.objects.create(
                    photo=photo, user=request.user, session_key="")
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
                PhotoLike.objects.create(
                    photo=photo, user=None, session_key=skey)
                delta += 1
                liked = True

        # Атомарно обновляем счётчик с защитой от отрицательных значений
        if delta != 0:
            PublicPhoto.objects.filter(pk=photo.pk).update(
                likes_count=Greatest(F("likes_count") + delta, Value(0))
            )

        # Берём актуальное значение из БД
        new_count = PublicPhoto.objects.filter(pk=photo.pk).values_list(
            "likes_count", flat=True).first() or 0

        # Уведомление автору фото о лайке
        try:
            if liked and request.user.is_authenticated and getattr(photo, "uploaded_by_id", None) and request.user.id != photo.uploaded_by_id:
                Notification.create(
                    recipient=photo.uploaded_by,
                    actor=request.user,
                    type=Notification.Type.LIKE_PHOTO,
                    message=f"@{request.user.username} понравилось ваше фото",
                    link=photo.get_absolute_url(),
                    payload={"photo_id": photo.pk, "count": int(new_count)},
                )
        except Exception:
            pass

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "liked": liked, "count": new_count})
    return redirect(
        request.META.get("HTTP_REFERER")
        or reverse("gallery:photo_detail", args=[pk])
    )


@login_required
@require_POST
def photo_save_toggle(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Тоггл «Сохранить» (закладка) для публичного фото. Только для авторизованных.
    Возвращает JSON: { ok, saved, count }
    """
    try:
        photo = PublicPhoto.objects.get(pk=pk, is_active=True)
    except PublicPhoto.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Photo not found"}, status=404)

    saved = False
    with transaction.atomic():
        existing = PhotoSave.objects.select_for_update().filter(
            photo=photo, user=request.user).first()
        if existing:
            existing.delete()
            saved = False
        else:
            PhotoSave.objects.create(photo=photo, user=request.user)
            saved = True

    new_count = PhotoSave.objects.filter(photo=photo).count()
    return JsonResponse({"ok": True, "saved": saved, "count": new_count}, status=200)


def photo_likers(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Список лайкнувших фото (только пользователи, без гостевых лайков).
    Возвращает JSON: [{username, name, avatar, is_following}]
    """
    from dashboard.models import Follow
    photo = get_object_or_404(PublicPhoto, pk=pk, is_active=True)

    likes_qs = (
        PhotoLike.objects
        .select_related("user", "user__profile")
        .filter(photo=photo, user__isnull=False)
        .order_by("-id")
    )

    user_ids = list(likes_qs.values_list("user_id", flat=True))
    following_set: set[int] = set()
    if request.user.is_authenticated and user_ids:
        following_set = set(
            Follow.objects.filter(follower=request.user,
                                  following_id__in=user_ids)
            .values_list("following_id", flat=True)
        )

    def _avatar(u) -> str:
        try:
            prof = getattr(u, "profile", None)
            av = getattr(prof, "avatar", None)
            return av.url if (av and getattr(av, "url", None)) else ""
        except Exception:
            return ""

    data = []
    for pl in likes_qs:
        u = pl.user
        if not u:
            continue
        data.append({
            "username": u.username,
            "name": (u.get_full_name() or u.username),
            "avatar": _avatar(u),
            "is_following": (u.id in following_set),
        })

    return JsonResponse({"ok": True, "likers": data})


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
            existing = CommentLike.objects.select_for_update().filter(
                comment=comment, user=request.user).first()
            if existing:
                existing.delete()
                delta -= 1
                liked = False
            else:
                # Консолидация гостевого лайка этой сессии (если есть)
                if skey:
                    CommentLike.objects.filter(
                        comment=comment, user__isnull=True, session_key=skey).delete()
                CommentLike.objects.create(
                    comment=comment, user=request.user, session_key="")
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
                CommentLike.objects.create(
                    comment=comment, user=None, session_key=skey)
                delta += 1
                liked = True

        # Атомарно обновляем denorm-счётчик на комментарии
        if delta != 0:
            PhotoComment.objects.filter(pk=comment.pk).update(
                likes_count=Greatest(F("likes_count") + delta, Value(0))
            )
        new_count = PhotoComment.objects.filter(pk=comment.pk).values_list(
            "likes_count", flat=True).first() or 0

        # Уведомление автору комментария о лайке
        try:
            if liked and request.user.is_authenticated and getattr(comment, "user_id", None) and request.user.id != comment.user_id:
                anchor_id = comment.pk
                Notification.create(
                    recipient=comment.user,
                    actor=request.user,
                    type=Notification.Type.COMMENT_LIKE_PHOTO,
                    message=f"@{request.user.username} понравился ваш комментарий",
                    link=reverse("gallery:photo_detail", args=[
                                 comment.photo_id]) + f"#c{anchor_id}",
                    payload={
                        "comment_id": comment.pk,
                        "parent_id": comment.parent_id or 0,
                        "photo_id": comment.photo_id,
                        "count": int(new_count),
                    },
                )
        except Exception:
            pass

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
        child = PhotoComment.objects.create(
            photo=parent.photo,
            user=request.user,
            text=form.cleaned_data["text"],
            parent=parent,
        )
        # Инкремент счётчика комментариев на фото (учитываем и ответы)
        PublicPhoto.objects.filter(pk=parent.photo_id).update(
            comments_count=F("comments_count") + 1
        )

        # Уведомление автору комментария об ответе
        try:
            if request.user.is_authenticated and getattr(parent, "user_id", None) and request.user.id != parent.user_id:
                # Получаем первую строку ответа для превью
                reply_preview = (text or "").strip().split('\n')[0][:50]
                if len((text or "").strip()) > 50:
                    reply_preview += "..."

                Notification.create(
                    recipient=parent.user,
                    actor=request.user,
                    type=Notification.Type.REPLY_PHOTO,
                    message=f"@{request.user.username} ответил(а) на ваш комментарий",
                    link=reverse("gallery:photo_detail", args=[
                                 parent.photo_id]) + f"#c{child.pk}",
                    payload={"comment_id": parent.pk,
                             "reply_id": child.pk, "photo_id": parent.photo_id, "comment_text": reply_preview},
                )
        except Exception:
            pass

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
        # ФОТО: используем форму с категориями фото
        form = SharePhotoFromJobForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data.get("title", "")
            caption = form.cleaned_data.get("caption", "")

            # Сжать изображение в WEBP и сохранить в медиа-папку проекта
            try:
                with default_storage.open(job.result_image.name, "rb") as fh:
                    data = fh.read()
                saved_name = _save_optimized_webp_bytes(
                    data,
                    subdir="public",
                    filename_base=f"job_{job.pk}"
                )
            except Exception:
                # Фолбэк: копия исходника как есть
                src_file = job.result_image
                src_name = src_file.name.rsplit("/", 1)[-1]
                dst_dir = f"public/{job.created_at:%Y/%m}/"
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
        # ФОТО: форма с категорий фото (без автозаполнения промпта)
        form = SharePhotoFromJobForm(
            initial={"title": "", "caption": ""})

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
    """Список работ, ожидающих публикации - фото и видео."""
    pending_photos = PublicPhoto.objects.filter(
        is_active=False).select_related("uploaded_by").order_by("-created_at")
    pending_videos = PublicVideo.objects.filter(
        is_active=False).select_related("uploaded_by").order_by("-created_at")

    return render(request, "gallery/moderation.html", {
        "pending_photos": pending_photos,
        "pending_videos": pending_videos,
        "total_pending": pending_photos.count() + pending_videos.count(),
    })


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
        messages.error(
            request, "Публичные работы может удалять только администратор.")
        return redirect(request.POST.get("next") or "dashboard:my_jobs")

    if (job.user_id != request.user.id) and (not request.user.is_staff):
        messages.error(request, "Нет прав на удаление этой генерации.")
        return redirect(request.POST.get("next") or "dashboard:my_jobs")

    try:
        if getattr(job, "result_image", None) and job.result_image.name:
            job.result_image.delete(save=False)
    except Exception:
        pass

    # Удаляем связанные элементы личной галереи (включая видео-плитки в «Мои генерации»)
    try:
        Image.objects.filter(generation_job=job).delete()
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

    # Сохранить изображение как WEBP в медиа-папку проекта
    try:
        data = file.read()
        saved_name = _save_optimized_webp_bytes(
            data,
            subdir="public",
            filename_base=(title or getattr(file, "name", "image"))
        )
    except Exception:
        # Фолбэк: сохранить исходник как есть
        try:
            dst_dir = f"public/{timezone.now():%Y/%m}/"
            storage_name = default_storage.generate_filename(
                dst_dir + (getattr(file, "name", "image.jpg")))
            saved_name = default_storage.save(
                storage_name,
                ContentFile(data if 'data' in locals() and data else file.read())
            )
        except Exception:
            saved_name = default_storage.save(getattr(file, "name", "image.jpg"), file)

    PublicPhoto.objects.create(
        image=saved_name, title=title, caption=caption, uploaded_by=request.user
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
                messages.error(
                    request, "Категория с таким слагом уже существует.")
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
    next_url = request.GET.get("next") or reverse(
        "gallery:photo_detail", args=[photo.pk])

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

        # Уведомление автору фото о новом комментарии
        try:
            if request.user.is_authenticated and getattr(photo, "uploaded_by_id", None) and request.user.id != photo.uploaded_by_id:
                # Получаем первую строку комментария для превью
                comment_preview = (text or "").strip().split('\n')[0][:50]
                if len((text or "").strip()) > 50:
                    comment_preview += "..."

                Notification.create(
                    recipient=photo.uploaded_by,
                    actor=request.user,
                    type=Notification.Type.COMMENT_PHOTO,
                    message=f"@{request.user.username} прокомментировал(а) ваше фото",
                    link=reverse("gallery:photo_detail", args=[
                                 photo.pk]) + "#comments",
                    payload={"photo_id": photo.pk, "comment_text": comment_preview},
                )
        except Exception:
            pass

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})

    return redirect(reverse("gallery:photo_detail", args=[pk]))


# ───────────────────────── SLUG DETAIL (фото/видео) ─────────────────────────

def photo_detail_by_slug(request: HttpRequest, slug: str) -> HttpResponse:
    """Детальная страница фото по slug без префикса /photo/."""
    photo = get_object_or_404(
        PublicPhoto.objects.select_related("uploaded_by", "category"),
        slug=slug,
        is_active=True,
    )

    # Respect owner's hide setting
    try:
        from .models import JobHide
        job_id = getattr(photo, "source_job_id", None)
        if job_id is None:
            job_id = getattr(photo, "job_id", None)
        if job_id:
            is_hidden = JobHide.objects.filter(
                user=photo.uploaded_by, job_id=job_id).exists()
            if is_hidden and (not request.user.is_authenticated or request.user.id != photo.uploaded_by_id):
                from django.http import Http404
                raise Http404()
    except Exception:
        pass

    # increment views
    _ensure_session_key(request)
    _mark_photo_viewed_once(request, photo.pk)
    try:
        photo.refresh_from_db(fields=["view_count", "likes_count", "comments_count"])
    except Exception:
        pass

    # root comments
    comments = (
        photo.comments.select_related("user")
        .prefetch_related("replies__user", "likes")
        .filter(is_visible=True, parent__isnull=True)
        .order_by("created_at")
    )

    # already liked
    if request.user.is_authenticated:
        liked = PhotoLike.objects.filter(user=request.user, photo=photo).exists()
    else:
        skey = _ensure_session_key(request)
        liked = PhotoLike.objects.filter(user__isnull=True, session_key=skey, photo=photo).exists()

    # liked comment ids
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

    # Related photos (by category or top)
    try:
        related_photos = []
        base_qs = PublicPhoto.objects.filter(is_active=True).exclude(pk=photo.pk)
        # Exclude hidden jobs by owner (JobHide)
        try:
            from .models import JobHide
            from django.db.models import Exists, OuterRef, Q
            base_qs = base_qs.annotate(
                hidden_by_owner=Exists(
                    JobHide.objects.filter(user=OuterRef("uploaded_by_id"), job_id=OuterRef("source_job_id"))
                )
            )
            if request.user.is_authenticated:
                base_qs = base_qs.filter(Q(hidden_by_owner=False) | Q(uploaded_by_id=request.user.id))
            else:
                base_qs = base_qs.filter(hidden_by_owner=False)
        except Exception:
            pass
        if getattr(photo, "category_id", None):
            related_photos = list(
                base_qs.filter(category_id=photo.category_id)
                .order_by("-likes_count", "-view_count", "-created_at")[:8]
            )
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


def category_photo_detail(request: HttpRequest, category_slug: str, content_slug: str) -> HttpResponse:
    """
    SEO-friendly URL для фото: /gallery/photo/<category-slug>/<content-slug-id>
    content_slug в формате: "slug-123" (извлекаем ID из конца)
    """
    from django.http import Http404
    
    try:
        # Извлекаем ID из конца slug
        try:
            photo_id = int(content_slug.split('-')[-1])
        except (ValueError, IndexError):
            raise Http404("Invalid photo slug format")
        
        category = Category.objects.filter(slug=category_slug).first()
        if not category:
            raise Http404("Category not found")

        photo = PublicPhoto.objects.filter(
            pk=photo_id,
            category=category,
            is_active=True
        ).first()

        if not photo:
            raise Http404("Photo not found")

        # Используем существующую функцию photo_detail с ID
        return photo_detail(request, photo_id)
    except Http404:
        raise
    except Exception as e:
        raise Http404(f"Photo not found: {e}")


def category_content_detail(request: HttpRequest, category_slug: str, content_slug: str) -> HttpResponse:
    """
    Legacy SEO-friendly URL с категорией: /gallery/<category-slug>/<content-slug>
    - Сначала ищем фото по Category.slug + PublicPhoto.slug
    - Если не нашли — ищем видео по VideoCategory.slug + PublicVideo.slug
    """
    # Пытаемся как фото
    try:
        category = Category.objects.filter(slug=category_slug).first()
        if category:
            photo = PublicPhoto.objects.filter(
                slug=content_slug,
                category=category,
                is_active=True
            ).first()
            if photo:
                return photo_detail_by_slug(request, content_slug)
    except Exception:
        pass

    # Пытаемся как видео
    try:
        video_category = VideoCategory.objects.filter(slug=category_slug).first()
        if video_category:
            video = PublicVideo.objects.filter(
                slug=content_slug,
                category=video_category,
                is_active=True
            ).first()
            if video:
                from . import views_video as vvid
                return vvid.video_detail(request, content_slug)
    except Exception:
        pass

    # Если не нашли ни фото, ни видео - 404
    from django.http import Http404
    raise Http404("Content not found")


def slug_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Универсальный детальный маршрут по слагу с ID: slug-123
    - Сначала ищем фото по ID
    - Если не нашли — ищем видео по ID
    """
    from django.http import Http404
    
    # Извлекаем ID из конца slug
    try:
        content_id = int(slug.split('-')[-1])
    except (ValueError, IndexError):
        raise Http404("Invalid slug format")
    
    # Пытаемся как фото
    try:
        if PublicPhoto.objects.filter(pk=content_id, is_active=True).exists():
            return photo_detail(request, content_id)
    except Exception:
        pass

    # Пытаемся как видео
    from . import views_video as vvid
    try:
        if vvid.PublicVideo.objects.filter(pk=content_id, is_active=True).exists():
            return vvid.video_detail_by_pk(request, content_id)
    except Exception:
        pass

    raise Http404("Content not found")
    return vvid.video_detail(request, slug)
