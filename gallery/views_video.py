# gallery/views_video.py
"""
Views для работы с публичными видео в галерее.
Аналог views для PublicPhoto, но для видео.
"""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.http import JsonResponse, HttpRequest, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_POST, require_http_methods

from generate.models import GenerationJob
from .models import (
    PublicVideo,
    VideoLike,
    VideoComment,
    VideoCommentLike,
    Category,
    VideoSave,
    PublicPhoto,
    PhotoLike,
    PhotoSave,
)
from .forms import PhotoCommentForm  # Переиспользуем ту же форму

# Доп. импорты для прокси/стриминга и фоновой оптимизации
import os
import mimetypes
import threading
import tempfile
import shutil
import subprocess
from typing import Iterator, Optional

import requests
from django.utils import timezone
import io
from PIL import Image


# ───────────────────────── HELPERS ─────────────────────────

def _ensure_session_key(request: HttpRequest) -> str:
    """Гарантируем наличие session_key."""
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _mark_video_viewed_once(_request: HttpRequest, video_id: int) -> None:
    """Инкремент счётчика просмотров видео."""
    PublicVideo.objects.filter(pk=video_id).update(view_count=F("view_count") + 1)


def _save_optimized_webp_bytes(data: bytes, subdir: str = "public_videos/thumbs", filename_base: str = "thumb") -> str:
    """
    Сжать байты изображения в WEBP и сохранить в сторадж проекта.
    - Конвертация в RGB
    - Даунскейл до макс 2048px по длинной стороне
    - WEBP quality=75, method=6
    Возвращает storage name (относительный путь), не URL.
    """
    base = slugify(filename_base)[:60] or "thumb"
    im = Image.open(io.BytesIO(data))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
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
    im.save(buf, format="WEBP", quality=75, method=6)
    buf.seek(0)
    dst_dir = f"{subdir}/{timezone.now():%Y/%m}/"
    storage_name = default_storage.generate_filename(f"{dst_dir}{base}.webp")
    return default_storage.save(storage_name, ContentFile(buf.read()))


# ───────────────────────── TRENDING VIDEOS ─────────────────────────
def trending_videos(request: HttpRequest) -> HttpResponse:
    """
    Тренды видео:
      - by=views : по просмотрам (за всё время)
      - by=likes : по количеству лайков
      - by=new   : «самые новые за 10 дней» (с приоритетом по лайкам/просмотрам)
    """
    from datetime import timedelta
    from django.utils import timezone
    from django.core.paginator import Paginator
    from django.db.models import Count, Exists, OuterRef, Q

    mode = (request.GET.get("by") or "views").lower()

    now = timezone.now()
    base_qs = (
        PublicVideo.objects.filter(is_active=True)
        .annotate(
            saves_count=Count("saves", distinct=True),
        )
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

    # Hide publications linked to hidden source jobs (not visible to others)
    from .models import JobHide
    base_qs = base_qs.annotate(
        hidden_by_owner=Exists(
            JobHide.objects.filter(user=OuterRef("uploaded_by_id"), job_id=OuterRef("source_job_id"))
        )
    )
    if request.user.is_authenticated:
        base_qs = base_qs.filter(Q(hidden_by_owner=False) | Q(uploaded_by_id=request.user.id))
    else:
        base_qs = base_qs.filter(hidden_by_owner=False)

    if mode == "likes":
        videos_qs = base_qs.order_by("-likes_count", "-view_count", "-created_at")
    elif mode == "new":
        videos_qs = (
            base_qs.filter(created_at__gte=now - timedelta(days=10))
            .order_by("-created_at", "-likes_count", "-view_count")
        )
    else:  # views
        videos_qs = base_qs.order_by("-view_count", "-likes_count", "-created_at")

    paginator = Paginator(videos_qs, 500)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    # Лайкнутые видео на странице
    liked_video_ids: set[int] = set()
    page_video_ids = list(page_obj.object_list.values_list("id", flat=True)) if page_obj.object_list else []
    if page_video_ids:
        if request.user.is_authenticated:
            liked_video_ids = set(
                VideoLike.objects.filter(user=request.user, video_id__in=page_video_ids)
                .values_list("video_id", flat=True)
            )
        else:
            skey = _ensure_session_key(request)
            liked_video_ids = set(
                VideoLike.objects.filter(user__isnull=True, session_key=skey, video_id__in=page_video_ids)
                .values_list("video_id", flat=True)
            )

    # Сохранённые видео (только для авторизованных)
    saved_video_ids: set[int] = set()
    if page_video_ids and request.user.is_authenticated:
        saved_video_ids = set(
            VideoSave.objects.filter(user=request.user, video_id__in=page_video_ids)
            .values_list("video_id", flat=True)
        )

    # Precompute all photos modes for in-place switching on videos page (no network on click)
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count, Exists, OuterRef, Q

    now = timezone.now()

    photos_base_qs = (
        PublicPhoto.objects.filter(is_active=True)
        .annotate(saves_count=Count("saves", distinct=True))
        .select_related("category", "uploaded_by")
        .only("id", "image", "title", "caption", "created_at", "view_count", "likes_count",
              "category__name", "uploaded_by__username")
    )
    try:
        from .models import JobHide
        pf_names = {f.name for f in PublicPhoto._meta.get_fields()}
        photo_rel_id = "source_job_id" if "source_job" in pf_names else ("job_id" if "job" in pf_names else None)
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

    photos_views_qs = photos_base_qs.order_by("-view_count", "-likes_count", "-created_at")
    photos_likes_qs = photos_base_qs.order_by("-likes_count", "-view_count", "-created_at")
    photos_new_qs = photos_base_qs.filter(created_at__gte=now - timedelta(days=10)).order_by("-created_at", "-likes_count", "-view_count")

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

    p_ids_v, liked_photo_ids_views, saved_photo_ids_views = _ids_for_photos(photos_views_qs)
    p_ids_l, liked_photo_ids_likes, saved_photo_ids_likes = _ids_for_photos(photos_likes_qs)
    p_ids_n, liked_photo_ids_new, saved_photo_ids_new = _ids_for_photos(photos_new_qs)

    photos_views = list(photos_views_qs.filter(id__in=p_ids_v))
    photos_likes = list(photos_likes_qs.filter(id__in=p_ids_l))
    photos_new = list(photos_new_qs.filter(id__in=p_ids_n))

    # Precompute all video modes too (already have page_obj for current mode)
    videos_views_qs = base_qs.order_by("-view_count", "-likes_count", "-created_at")
    videos_likes_qs = base_qs.order_by("-likes_count", "-view_count", "-created_at")
    videos_new_qs = base_qs.filter(created_at__gte=now - timedelta(days=10)).order_by("-created_at", "-likes_count", "-view_count")

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

    v_ids_v, liked_video_ids_views_all, saved_video_ids_views_all = _ids_for_videos(videos_views_qs)
    v_ids_l, liked_video_ids_likes_all, saved_video_ids_likes_all = _ids_for_videos(videos_likes_qs)
    v_ids_n, liked_video_ids_new_all, saved_video_ids_new_all = _ids_for_videos(videos_new_qs)

    videos_views_all = list(videos_views_qs.filter(id__in=v_ids_v))
    videos_likes_all = list(videos_likes_qs.filter(id__in=v_ids_l))
    videos_new_all = list(videos_new_qs.filter(id__in=v_ids_n))

    return render(
        request,
        "gallery/trending_videos.html",
        {
            # Current (for initial video view)
            "trending_videos": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "active_mode": mode,
            "liked_video_ids": liked_video_ids,
            "saved_video_ids": saved_video_ids,

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
            "videos_views": videos_views_all,
            "videos_likes": videos_likes_all,
            "videos_new": videos_new_all,
            "liked_video_ids_views": liked_video_ids_views_all,
            "liked_video_ids_likes": liked_video_ids_likes_all,
            "liked_video_ids_new": liked_video_ids_new_all,
            "saved_video_ids_views": saved_video_ids_views_all,
            "saved_video_ids_likes": saved_video_ids_likes_all,
            "saved_video_ids_new": saved_video_ids_new_all,
        },
    )

# ───────────────────────── STREAM/PROXY + OPTIMIZATION HELPERS ─────────────────────────

_OPT_DIR = "public_videos_optimized"


def _optimized_relpath(pk: int) -> str:
    # Храним оптимизированные копии по ключу видео
    return f"{_OPT_DIR}/{pk}.mp4"


def _parse_range(range_header: Optional[str], size: int) -> Optional[tuple[int, int]]:
    """
    Парсим заголовок Range: bytes=start-end.
    Возвращаем (start, end) или None если невалиден.
    """
    try:
        if not range_header:
            return None
        if not range_header.startswith("bytes="):
            return None
        rng = range_header.split("=", 1)[1].strip()
        if "," in rng:
            rng = rng.split(",")[0]  # несколько диапазонов не поддерживаем
        if "-" not in rng:
            return None
        start_s, end_s = rng.split("-", 1)
        if start_s == "":
            # суффиксная форма: bytes=-500 (последние 500 байт)
            length = int(end_s)
            if length <= 0:
                return None
            start = max(0, size - length)
            end = size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else size - 1
        start = max(0, start)
        end = min(size - 1, end)
        if start > end:
            return None
        return start, end
    except Exception:
        return None


def _serve_local_file_with_range(request: HttpRequest, storage_path: str, content_type: str = "video/mp4") -> HttpResponse:
    """
    Отдаём локальный файл из default_storage с поддержкой Range.
    """
    try:
        size = default_storage.size(storage_path)
    except Exception:
        size = None

    if size is None or size <= 0:
        # запасной вариант — обычный стрим без Range
        f = default_storage.open(storage_path, "rb")

        def iterator():
            try:
                chunk = f.read(64 * 1024)
                while chunk:
                    yield chunk
                    chunk = f.read(64 * 1024)
            finally:
                try:
                    f.close()
                except Exception:
                    pass

        resp = StreamingHttpResponse(iterator(), content_type=content_type, status=200)
        resp["Cache-Control"] = "public, max-age=31536000"
        resp["Accept-Ranges"] = "bytes"
        return resp

    # нормальная отдача с Range
    rng = _parse_range(request.headers.get("Range"), size)
    f = default_storage.open(storage_path, "rb")
    if not rng:
        # без диапазона — обычный 200
        def iterator_full():
            try:
                chunk = f.read(64 * 1024)
                while chunk:
                    yield chunk
                    chunk = f.read(64 * 1024)
            finally:
                try:
                    f.close()
                except Exception:
                    pass

        resp = StreamingHttpResponse(iterator_full(), content_type=content_type, status=200)
        resp["Content-Length"] = str(size)
        resp["Cache-Control"] = "public, max-age=31536000"
        resp["Accept-Ranges"] = "bytes"
        return resp

    start, end = rng
    length = end - start + 1
    try:
        f.seek(start)
    except Exception:
        pass

    def iterator_range():
        remaining = length
        try:
            while remaining > 0:
                chunk = f.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
        finally:
            try:
                f.close()
            except Exception:
                pass

    resp = StreamingHttpResponse(iterator_range(), content_type=content_type, status=206)
    resp["Content-Length"] = str(length)
    resp["Content-Range"] = f"bytes {start}-{end}/{size}"
    resp["Accept-Ranges"] = "bytes"
    resp["Cache-Control"] = "public, max-age=31536000"
    return resp


def _proxy_remote_stream(request: HttpRequest, url: str, content_type: str = "video/mp4") -> HttpResponse:
    """
    Прокси-стрим внешнего MP4 с поддержкой Range.
    Используем stream=True и пробрасываем Range-заголовок.
    """
    headers = {}
    rng = request.headers.get("Range")
    if rng:
        headers["Range"] = rng

    # Таймаут консервативный, чтобы не «висеть»
    try:
        r = requests.get(url, headers=headers, stream=True, timeout=(5, 30))
    except Exception:
        # если удалённый источник не ответил — 502
        return HttpResponse(status=502)

    status = 206 if r.status_code == 206 else 200
    # Пытаемся выяснить длину по заголовкам
    content_length = r.headers.get("Content-Length")
    content_range = r.headers.get("Content-Range")
    ctype = r.headers.get("Content-Type") or content_type

    def generate():
        try:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        finally:
            try:
                r.close()
            except Exception:
                pass

    resp = StreamingHttpResponse(generate(), content_type=ctype, status=status)
    resp["Accept-Ranges"] = "bytes"
    if content_length:
        resp["Content-Length"] = content_length
    if content_range:
        resp["Content-Range"] = content_range
    # даём браузеру кэшировать
    resp["Cache-Control"] = "public, max-age=600"
    return resp


def _optimize_video_async(pk: int, src_url: str, dst_rel: str) -> None:
    """
    Фоновая оптимизация: скачиваем внешний файл и пытаемся пережать до «лёгкой» копии (720p, CRF 28, faststart).
    Если ffmpeg недоступен — просто закешируем оригинал для локальной раздачи.
    """
    lock_rel = f"{dst_rel}.lock"
    try:
        if default_storage.exists(dst_rel) or default_storage.exists(lock_rel):
            return
        # ставим lock-файл
        default_storage.save(lock_rel, ContentFile(b""))

        # скачиваем во временный файл
        with tempfile.TemporaryDirectory() as td:
            src_path = os.path.join(td, "src.mp4")
            opt_path = os.path.join(td, "opt.mp4")

            try:
                with requests.get(src_url, stream=True, timeout=(5, 120)) as rr:
                    rr.raise_for_status()
                    with open(src_path, "wb") as fw:
                        for chunk in rr.iter_content(chunk_size=256 * 1024):
                            if chunk:
                                fw.write(chunk)
            except Exception:
                # не удалось скачать — выходим
                return

            ffmpeg = shutil.which("ffmpeg")
            if ffmpeg:
                # пережимаем в 720p с faststart
                # -preset veryfast, H.264 + AAC, CRF 28
                cmd = [
                    ffmpeg,
                    "-y",
                    "-i", src_path,
                    "-vf", "scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "28",
                    "-movflags", "+faststart",
                    "-c:a", "aac",
                    "-b:a", "96k",
                    opt_path,
                ]
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    out_path = opt_path if os.path.exists(opt_path) else src_path
                except Exception:
                    out_path = src_path
            else:
                # ffmpeg нет — оставляем исходник
                out_path = src_path

            # Сохраняем в storage потоково
            try:
                with open(out_path, "rb") as fr:
                    # По возможности — писать без загрузки в память
                    # В FileSystemStorage можно сохранить напрямую через .save(name, file)
                    default_storage.save(dst_rel, ContentFile(fr.read()))
            except Exception:
                return
    finally:
        # снимаем lock
        try:
            if default_storage.exists(lock_rel):
                default_storage.delete(lock_rel)
        except Exception:
            pass


def _ensure_optimize_in_background(video: PublicVideo) -> None:
    """
    Стартуем оптимизацию в фоне (однажды). Ничего не ждём.
    """
    try:
        dst_rel = _optimized_relpath(video.pk)
        if default_storage.exists(dst_rel):
            return
        t = threading.Thread(target=_optimize_video_async, args=(video.pk, video.video_url, dst_rel), daemon=True)
        t.start()
    except Exception:
        pass


# ───────────────────────── VIDEO STREAM (PROXY/LOCAL) ─────────────────────────

@require_http_methods(["GET", "HEAD"])
def video_stream(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Унифицированная точка отдачи видео:
      1) Если есть локальная оптимизированная копия — отдаём её (с Range).
      2) Если video_url — локальный путь (/media/...) — отдаём из storage напрямую.
      3) Иначе запускаем фоновую оптимизацию и проксируем внешний video_url c поддержкой Range.
    """
    video = get_object_or_404(PublicVideo.objects.only("id", "video_url", "uploaded_by", "source_job_id", "is_active"), pk=pk, is_active=True)

    # Уважаем скрытие (как и в деталке)
    try:
        from .models import JobHide
        if getattr(video, "source_job_id", None):
            is_hidden = JobHide.objects.filter(user=video.uploaded_by, job_id=video.source_job_id).exists()
            if is_hidden and (not request.user.is_authenticated or request.user.id != video.uploaded_by_id):
                from django.http import Http404
                raise Http404()
    except Exception:
        pass

    # 1) локальная оптимизированная
    try:
        dst_rel = _optimized_relpath(video.pk)
        if default_storage.exists(dst_rel):
            ctype = mimetypes.guess_type(dst_rel)[0] or "video/mp4"
            return _serve_local_file_with_range(request, dst_rel, ctype)
    except Exception:
        pass

    # 2) проверяем, является ли video_url локальным путем
    video_url = video.video_url or ""
    if video_url.startswith("/media/"):
        # Локальный путь — убираем префикс /media/ и отдаём из storage
        storage_path = video_url[len("/media/"):]
        try:
            if default_storage.exists(storage_path):
                ctype = mimetypes.guess_type(storage_path)[0] or "video/mp4"
                return _serve_local_file_with_range(request, storage_path, ctype)
        except Exception:
            pass
        # Если не нашли в storage — 404
        from django.http import Http404
        raise Http404("Video file not found in storage")

    # 3) запустить фон — и проксировать удалённый сейчас
    _ensure_optimize_in_background(video)
    return _proxy_remote_stream(request, video.video_url, "video/mp4")

# ───────────────────────── VIDEO DETAIL ─────────────────────────

def video_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Детальная страница видео с комментариями."""
    video = get_object_or_404(
        PublicVideo.objects.select_related("uploaded_by", "category"),
        slug=slug,
        is_active=True,
    )

    # Respect owner's hide setting: hidden publications are not visible to others
    try:
        from .models import JobHide
        if getattr(video, "source_job_id", None):
            is_hidden = JobHide.objects.filter(user=video.uploaded_by, job_id=video.source_job_id).exists()
            if is_hidden and (not request.user.is_authenticated or request.user.id != video.uploaded_by_id):
                from django.http import Http404
                raise Http404()
    except Exception:
        pass

    # Инкремент просмотров
    _ensure_session_key(request)
    _mark_video_viewed_once(request, video.pk)
    try:
        video.refresh_from_db(fields=["view_count", "likes_count", "comments_count"])
    except Exception:
        pass

    # Корневые комментарии
    comments = (
        video.comments.select_related("user")
        .prefetch_related("replies__user", "likes")
        .filter(is_visible=True, parent__isnull=True)
        .order_by("created_at")
    )

    # Лайкнуто ли видео
    liked = False
    if request.user.is_authenticated:
        liked = VideoLike.objects.filter(user=request.user, video=video).exists()
    else:
        skey = _ensure_session_key(request)
        liked = VideoLike.objects.filter(user__isnull=True, session_key=skey, video=video).exists()

    # Лайкнутые комментарии
    liked_comment_ids: set[int] = set()
    all_comment_ids = []
    for c in comments:
        all_comment_ids.append(c.pk)
        for r in c.replies.all():
            all_comment_ids.append(r.pk)

    if all_comment_ids:
        if request.user.is_authenticated:
            liked_comment_ids = set(
                VideoCommentLike.objects.filter(
                    user=request.user, comment_id__in=all_comment_ids
                ).values_list("comment_id", flat=True)
            )
        else:
            skey = _ensure_session_key(request)
            liked_comment_ids = set(
                VideoCommentLike.objects.filter(
                    user__isnull=True, session_key=skey, comment_id__in=all_comment_ids
                ).values_list("comment_id", flat=True)
            )

    # Похожие видео (по категории или топ)
    try:
        related_videos = []
        base_qs = PublicVideo.objects.filter(is_active=True).exclude(pk=video.pk)
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
        if getattr(video, "category_id", None):
            related_videos = list(
                base_qs.filter(category_id=video.category_id)
                       .order_by("-likes_count", "-view_count", "-created_at")[:8]
            )
        if len(related_videos) < 8:
            exclude_ids = [video.pk] + [v.pk for v in related_videos]
            fill = list(
                base_qs.exclude(pk__in=exclude_ids)
                       .order_by("-likes_count", "-view_count", "-created_at")[: 8 - len(related_videos)]
            )
            related_videos.extend(fill)
    except Exception:
        related_videos = []

    # Проверяем лайки для похожих видео (важно для гостей!)
    liked_video_ids: set[int] = set()
    related_video_ids = [v.id for v in related_videos]
    if related_video_ids:
        if request.user.is_authenticated:
            liked_video_ids = set(
                VideoLike.objects.filter(
                    user=request.user, video_id__in=related_video_ids
                ).values_list("video_id", flat=True)
            )
        else:
            skey = _ensure_session_key(request)
            liked_video_ids = set(
                VideoLike.objects.filter(
                    user__isnull=True, session_key=skey, video_id__in=related_video_ids
                ).values_list("video_id", flat=True)
            )

    return render(
        request,
        "gallery/video_detail.html",
        {
            "video": video,
            "comments": comments,
            "liked": liked,
            "liked_comment_ids": liked_comment_ids,
            "liked_video_ids": liked_video_ids,
            "comment_form": PhotoCommentForm(),
            "related_videos": related_videos,
        },
    )


def video_detail_by_pk(request: HttpRequest, pk: int) -> HttpResponse:
    """Legacy: редирект со старого URL /video/<pk> на человеко-понятный /video/<slug>."""
    video = get_object_or_404(
        PublicVideo.objects.only("id", "slug", "is_active", "uploaded_by"),
        pk=pk,
        is_active=True,
    )
    # уважаем скрытие (аналогично detail)
    try:
        from .models import JobHide
        if getattr(video, "source_job_id", None):
            is_hidden = JobHide.objects.filter(user=video.uploaded_by, job_id=video.source_job_id).exists()
            if is_hidden and (not request.user.is_authenticated or request.user.id != video.uploaded_by_id):
                from django.http import Http404
                raise Http404()
    except Exception:
        pass

    # Ensure slug exists to avoid legacy redirect loops
    if not getattr(video, "slug", None):
        base = slugify(video.title or "")[:120] or "video"
        candidate = base
        i = 1
        from .models import PublicVideo as PV
        while PV.objects.filter(slug=candidate).exclude(pk=video.pk).exists():
            candidate = (f"{base}-{i}")[:180]
            i += 1
        try:
            PV.objects.filter(pk=video.pk).update(slug=candidate)
            video.slug = candidate
        except Exception:
            pass

    return redirect(video.get_absolute_url())


def category_video_detail(request: HttpRequest, category_slug: str, content_slug: str) -> HttpResponse:
    """
    SEO-friendly URL для видео: /gallery/video/<category-slug>/<content-slug-id>
    content_slug в формате: "slug-123" (извлекаем ID из конца)
    """
    from .models import VideoCategory
    from django.http import Http404

    try:
        # Извлекаем ID из конца slug
        try:
            video_id = int(content_slug.split('-')[-1])
        except (ValueError, IndexError):
            raise Http404("Invalid video slug format")
        
        category = VideoCategory.objects.filter(slug=category_slug).first()
        if not category:
            raise Http404("Video category not found")

        video = PublicVideo.objects.filter(
            pk=video_id,
            category=category,
            is_active=True
        ).first()

        if not video:
            raise Http404("Video not found")

        # Используем существующую функцию video_detail_by_pk с ID
        return video_detail_by_pk(request, video_id)
    except Http404:
        raise
    except Exception as e:
        raise Http404(f"Video not found: {e}")


# ───────────────────────── VIDEO LIKE ─────────────────────────

@require_POST
def video_like(request: HttpRequest, pk: int) -> HttpResponse:
    """Тоггл лайка видео."""
    try:
        video = PublicVideo.objects.get(pk=pk, is_active=True)
    except PublicVideo.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Video not found"}, status=404)

    # Block interactions on hidden publications for non-owners
    try:
        from .models import JobHide
        if getattr(video, "source_job_id", None):
            is_hidden = JobHide.objects.filter(user=video.uploaded_by, job_id=video.source_job_id).exists()
            if is_hidden and (not request.user.is_authenticated or request.user.id != video.uploaded_by_id):
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"ok": False, "error": "hidden"}, status=403)
                from django.http import Http404
                raise Http404()
    except Exception:
        pass

    skey = _ensure_session_key(request)

    with transaction.atomic():
        delta = 0
        liked = False

        if request.user.is_authenticated:
            existing = VideoLike.objects.select_for_update().filter(video=video, user=request.user).first()
            if existing:
                existing.delete()
                delta -= 1
                liked = False
            else:
                # Консолидация гостевого лайка
                removed_guest = 0
                if skey:
                    removed_guest = VideoLike.objects.filter(
                        video=video, user__isnull=True, session_key=skey
                    ).delete()[0]
                VideoLike.objects.create(video=video, user=request.user, session_key="")
                delta += 1
                delta -= removed_guest
                liked = True
        else:
            if not skey:
                return JsonResponse({"ok": False, "error": "no-session"}, status=400)

            existing = VideoLike.objects.select_for_update().filter(
                video=video, user__isnull=True, session_key=skey
            ).first()
            if existing:
                existing.delete()
                delta -= 1
                liked = False
            else:
                VideoLike.objects.create(video=video, user=None, session_key=skey)
                delta += 1
                liked = True

        if delta != 0:
            PublicVideo.objects.filter(pk=video.pk).update(
                likes_count=Greatest(F("likes_count") + delta, Value(0))
            )

        new_count = PublicVideo.objects.filter(pk=video.pk).values_list("likes_count", flat=True).first() or 0
        # Notify owner about like
        try:
            from dashboard.models import Notification
            if liked and request.user.is_authenticated and getattr(video, "uploaded_by_id", None) and request.user.id != video.uploaded_by_id:
                Notification.create(
                    recipient=video.uploaded_by,
                    actor=request.user,
                    type=Notification.Type.LIKE_VIDEO,
                    message=f"@{request.user.username} понравилось ваше видео",
                    link=video.get_absolute_url(),
                    payload={"video_id": video.pk, "count": int(new_count)},
                )
        except Exception:
            pass

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "liked": liked, "count": new_count})
    return redirect(
        request.META.get("HTTP_REFERER")
        or video.get_absolute_url()
    )


@login_required
@require_POST
def video_save_toggle(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Тоггл «Сохранить» (закладка) для публичного видео. Только для авторизованных.
    Возвращает JSON: { ok, saved, count }
    """
    try:
        video = PublicVideo.objects.get(pk=pk, is_active=True)
    except PublicVideo.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Video not found"}, status=404)

    # Block saving on hidden publications for non-owners
    try:
        from .models import JobHide
        if getattr(video, "source_job_id", None):
            is_hidden = JobHide.objects.filter(user=video.uploaded_by, job_id=video.source_job_id).exists()
            if is_hidden and (not request.user.is_authenticated or request.user.id != video.uploaded_by_id):
                return JsonResponse({"ok": False, "error": "hidden"}, status=403)
    except Exception:
        pass

    saved = False
    with transaction.atomic():
        existing = VideoSave.objects.select_for_update().filter(video=video, user=request.user).first()
        if existing:
            existing.delete()
            saved = False
        else:
            VideoSave.objects.create(video=video, user=request.user)
            saved = True

    new_count = VideoSave.objects.filter(video=video).count()
    return JsonResponse({"ok": True, "saved": saved, "count": new_count}, status=200)


def video_likers(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Список лайкнувших видео (только пользователи, без гостевых лайков).
    JSON: { ok: true, likers: [{username, name, avatar, is_following}] }
    """
    from dashboard.models import Follow
    video = get_object_or_404(PublicVideo, pk=pk, is_active=True)

    # Block likers list for hidden publications for non-owners
    try:
        from .models import JobHide
        if getattr(video, "source_job_id", None):
            is_hidden = JobHide.objects.filter(user=video.uploaded_by, job_id=video.source_job_id).exists()
            if is_hidden and (not request.user.is_authenticated or request.user.id != video.uploaded_by_id):
                return JsonResponse({"ok": False, "error": "hidden"}, status=403)
    except Exception:
        pass

    likes_qs = (
        VideoLike.objects
        .select_related("user", "user__profile")
        .filter(video=video, user__isnull=False)
        .order_by("-id")
    )

    user_ids = list(likes_qs.values_list("user_id", flat=True))
    following_set: set[int] = set()
    if request.user.is_authenticated and user_ids:
        following_set = set(
            Follow.objects.filter(follower=request.user, following_id__in=user_ids)
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


# ───────────────────────── VIDEO COMMENT ─────────────────────────

@login_required
@require_POST
def video_comment(request: HttpRequest, pk: int) -> HttpResponse:
    """Добавить корневой комментарий к видео."""
    video = get_object_or_404(PublicVideo, pk=pk, is_active=True)
    # Block commenting on hidden publications for non-owners
    try:
        from .models import JobHide
        if getattr(video, "source_job_id", None):
            is_hidden = JobHide.objects.filter(user=video.uploaded_by, job_id=video.source_job_id).exists()
            if is_hidden and (not request.user.is_authenticated or request.user.id != video.uploaded_by_id):
                return JsonResponse({"ok": False, "error": "hidden"}, status=403)
    except Exception:
        pass

    form = PhotoCommentForm(request.POST)
    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
        messages.error(request, "Введите корректный комментарий.")
        return redirect(video.get_absolute_url() + "#comments")

    with transaction.atomic():
        VideoComment.objects.create(
            video=video,
            user=request.user,
            text=form.cleaned_data["text"],
            parent=None,
        )
        PublicVideo.objects.filter(pk=video.pk).update(
            comments_count=F("comments_count") + 1
        )
        # Notify owner about comment
        try:
            from dashboard.models import Notification
            if request.user.is_authenticated and getattr(video, "uploaded_by_id", None) and request.user.id != video.uploaded_by_id:
                text = form.cleaned_data["text"]
                # Получаем первую строку комментария для превью
                comment_preview = (text or "").strip().split('\n')[0][:50]
                if len((text or "").strip()) > 50:
                    comment_preview += "..."

                Notification.create(
                    recipient=video.uploaded_by,
                    actor=request.user,
                    type=Notification.Type.COMMENT_VIDEO,
                    message=f"@{request.user.username} прокомментировал(а) ваше видео",
                    link=video.get_absolute_url() + "#comments",
                    payload={"video_id": video.pk, "comment_text": comment_preview},
                )
        except Exception:
            pass

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})

    return redirect(video.get_absolute_url())


# ───────────────────────── VIDEO COMMENT REPLY ─────────────────────────

@login_required
@require_POST
def video_comment_reply(request: HttpRequest, pk: int) -> HttpResponse:
    """Ответ на комментарий к видео."""
    parent = get_object_or_404(VideoComment, pk=pk, is_visible=True)
    # Block replying on hidden publications for non-owners
    try:
        from .models import JobHide
        video = parent.video
        if getattr(video, "source_job_id", None):
            is_hidden = JobHide.objects.filter(user=video.uploaded_by, job_id=video.source_job_id).exists()
            if is_hidden and (not request.user.is_authenticated or request.user.id != video.uploaded_by_id):
                return JsonResponse({"ok": False, "error": "hidden"}, status=403)
    except Exception:
        pass

    form = PhotoCommentForm(request.POST)
    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
        messages.error(request, "Введите корректный ответ.")
        return redirect(parent.video.get_absolute_url())

    with transaction.atomic():
        jc = VideoComment.objects.create(
            video=parent.video,
            user=request.user,
            text=form.cleaned_data["text"],
            parent=parent,
        )
        PublicVideo.objects.filter(pk=parent.video_id).update(
            comments_count=F("comments_count") + 1
        )
        # Notify comment author about reply
        try:
            from dashboard.models import Notification
            if request.user.is_authenticated and getattr(parent, "user_id", None) and request.user.id != parent.user_id:
                text = form.cleaned_data["text"]
                # Получаем первую строку ответа для превью
                reply_preview = (text or "").strip().split('\n')[0][:50]
                if len((text or "").strip()) > 50:
                    reply_preview += "..."

                Notification.create(
                    recipient=parent.user,
                    actor=request.user,
                    type=Notification.Type.REPLY_VIDEO,
                    message=f"@{request.user.username} ответил(а) на ваш комментарий",
                    link=parent.video.get_absolute_url() + f"#c{jc.pk}",
                    payload={"comment_id": parent.pk, "reply_id": jc.pk, "video_id": parent.video_id, "comment_text": reply_preview},
                )
        except Exception:
            pass

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})

    return redirect(
        parent.video.get_absolute_url() + f"#c{parent.pk}"
    )


# ───────────────────────── VIDEO COMMENT LIKE ─────────────────────────

@require_POST
def video_comment_like(request: HttpRequest, pk: int) -> HttpResponse:
    """Тоггл лайка комментария к видео."""
    comment = get_object_or_404(VideoComment, pk=pk, is_visible=True)
    # Block comment-like on hidden publications for non-owners
    try:
        from .models import JobHide
        video = comment.video
        if getattr(video, "source_job_id", None):
            is_hidden = JobHide.objects.filter(user=video.uploaded_by, job_id=video.source_job_id).exists()
            if is_hidden and (not request.user.is_authenticated or request.user.id != video.uploaded_by_id):
                return JsonResponse({"ok": False, "error": "hidden"}, status=403)
    except Exception:
        pass

    skey = _ensure_session_key(request)

    with transaction.atomic():
        delta = 0
        liked = False

        if request.user.is_authenticated:
            existing = VideoCommentLike.objects.select_for_update().filter(comment=comment, user=request.user).first()
            if existing:
                existing.delete()
                delta -= 1
                liked = False
            else:
                if skey:
                    VideoCommentLike.objects.filter(comment=comment, user__isnull=True, session_key=skey).delete()
                VideoCommentLike.objects.create(comment=comment, user=request.user, session_key="")
                delta += 1
                liked = True
        else:
            if not skey:
                return JsonResponse({"ok": False, "error": "no-session"}, status=400)
            existing = VideoCommentLike.objects.select_for_update().filter(
                comment=comment, user__isnull=True, session_key=skey
            ).first()
            if existing:
                existing.delete()
                delta -= 1
                liked = False
            else:
                VideoCommentLike.objects.create(comment=comment, user=None, session_key=skey)
                delta += 1
                liked = True

        if delta != 0:
            VideoComment.objects.filter(pk=comment.pk).update(
                likes_count=Greatest(F("likes_count") + delta, Value(0))
            )
        new_count = VideoComment.objects.filter(pk=comment.pk).values_list("likes_count", flat=True).first() or 0
        # Notify comment author about like
        try:
            from dashboard.models import Notification
            if liked and request.user.is_authenticated and getattr(comment, "user_id", None) and request.user.id != comment.user_id:
                Notification.create(
                    recipient=comment.user,
                    actor=request.user,
                    type=Notification.Type.COMMENT_LIKE_VIDEO,
                    message=f"@{request.user.username} понравился ваш комментарий",
                    link=comment.video.get_absolute_url() + f"#c{comment.pk}",
                    payload={"comment_id": comment.pk, "parent_id": comment.parent_id or 0, "video_id": comment.video_id, "count": int(new_count)},
                )
        except Exception:
            pass

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "liked": liked, "count": new_count})
    return redirect(
        request.META.get("HTTP_REFERER")
        or comment.video.get_absolute_url()
    )


# ───────────────────────── SHARE VIDEO FROM JOB ─────────────────────────

@login_required
def share_video_from_job(request, job_id: int):
    """Публикация видео из задачи генерации в галерее."""
    try:
        job = GenerationJob.objects.select_related("user").get(pk=job_id)
    except GenerationJob.DoesNotExist:
        messages.error(request, "Эта генерация недоступна или была удалена.")
        return redirect("dashboard:my_jobs")

    # Проверки владельца/типа/статуса
    if job.user_id != request.user.id:
        messages.error(request, "Нет прав на публикацию этой генерации.")
        return redirect("dashboard:my_jobs")

    if getattr(job, "generation_type", "") != "video":
        messages.error(request, "Это не видео-генерация.")
        return redirect("dashboard:my_jobs")

    if job.status not in (GenerationJob.Status.DONE, GenerationJob.Status.PENDING_MODERATION):
        messages.error(request, "Генерация ещё не завершена.")
        return redirect("dashboard:my_jobs")

    if not job.result_video_url:
        messages.error(request, "У этой генерации нет готового видео.")
        return redirect("dashboard:my_jobs")

    if request.method == "POST":
        from .forms import ShareFromJobForm
        form = ShareFromJobForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data.get("title", "")
            caption = form.cleaned_data.get("caption", "")

            # Persist video locally into project storage (compressed if ffmpeg available)
            # NOTE: для обычных пользователей не выполняем повторное сетевое скачивание — используем уже сохранённый файл.
            persisted_video_url = None
            tmp_in = None
            tmp_out = None

            # 1) Предпочитаем уже сохранённое локальное видео из result_image (оно сохраняется при генерации)
            try:
                local_video_url = None
                if job.result_image and job.result_image.name:
                    # result_image для видео содержит mp4 под MEDIA_ROOT (например "videos/<job_id>.mp4")
                    local_video_url = default_storage.url(job.result_image.name)
            except Exception:
                local_video_url = None

            # 2) Для staff дополнительно пробуем пережатую копию в public_videos (необязательно)
            if request.user.is_staff:
                try:
                    # Источник для пережатия: сначала локальный файл, затем fallback на исходный URL
                    src_url = (job.result_video_url or local_video_url or "").strip()
                    if not src_url:
                        raise RuntimeError("empty video url")
                    r = requests.get(src_url, timeout=40, stream=True)
                    r.raise_for_status()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as fin:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                fin.write(chunk)
                        tmp_in = fin.name
                    tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                    ffmpeg_bin = shutil.which("ffmpeg") or os.getenv("FFMPEG_BIN", "ffmpeg")
                    try:
                        subprocess.run(
                            [
                                ffmpeg_bin,
                                "-y",
                                "-i", tmp_in,
                                "-c:v", "libx264",
                                "-preset", "veryfast",
                                "-crf", "28",
                                "-movflags", "+faststart",
                                "-c:a", "aac",
                                "-b:a", "128k",
                                tmp_out,
                            ],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=True,
                        )
                        with open(tmp_out, "rb") as f:
                            storage_name = default_storage.save(
                                f"public_videos/{timezone.now():%Y/%m}/job_{job.pk}.mp4",
                                ContentFile(f.read())
                            )
                        persisted_video_url = default_storage.url(storage_name)
                    except Exception:
                        # Fallback store original
                        if tmp_in and os.path.exists(tmp_in):
                            with open(tmp_in, "rb") as f:
                                storage_name = default_storage.save(
                                    f"public_videos/{timezone.now():%Y/%m}/job_{job.pk}.mp4",
                                    ContentFile(f.read())
                                )
                            persisted_video_url = default_storage.url(storage_name)
                except Exception:
                    # Любая ошибка сети/ffmpeg не должна мешать созданию записи — используем уже имеющийся URL
                    persisted_video_url = None
                finally:
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

            # Thumbnail: compress to WEBP and save in project media
            saved_thumb_name = None
            if job.result_image and job.result_image.name:
                try:
                    with default_storage.open(job.result_image.name, "rb") as fh:
                        img_bytes = fh.read()
                    saved_thumb_name = _save_optimized_webp_bytes(
                        img_bytes,
                        subdir="public_videos/thumbs",
                        filename_base=f"job_{job.pk}_thumb"
                    )
                except Exception:
                    saved_thumb_name = None

            will_publish_now = request.user.is_staff

            # Итоговый URL видео: сначала пережатая копия, затем локальный result_image, затем исходный result_video_url
            final_video_url = (persisted_video_url or local_video_url or job.result_video_url)

            video = PublicVideo.objects.create(
                video_url=final_video_url,
                thumbnail=saved_thumb_name,
                title=title,
                caption=caption,
                uploaded_by=request.user,
                is_active=will_publish_now,
                source_job=job,
            )

            if not will_publish_now:
                job.status = GenerationJob.Status.PENDING_MODERATION
                job.save(update_fields=['status'])

            cats = form.cleaned_data.get("categories")
            if cats:
                if hasattr(video, "categories"):
                    video.categories.set(cats)
                elif hasattr(video, "category"):
                    first = cats.first()
                    if first:
                        video.category = first
                        video.save(update_fields=["category"])

            messages.success(
                request,
                "Видео опубликовано в галерее." if will_publish_now
                else "Видео отправлено на модерацию. После проверки оно появится в галерее."
            )
            return redirect("gallery:index")
    else:
        from .forms import ShareFromJobForm
        # Не подставляем промпт вообще (исключаем любые автозаполнения из prompt)
        form = ShareFromJobForm(initial={"title": "", "caption": ""})

    return render(
        request,
        "gallery/share_video.html",
        {
            "form": form,
            "job": job,
            "video_url": job.result_video_url,
            "thumb_url": job.result_image.url if job.result_image else None,
        },
    )


# ───────────────────────── MODERATION ─────────────────────────

@staff_member_required
@require_POST
def moderation_approve_video(request: HttpRequest, pk: int) -> HttpResponse:
    """Одобрить видео (модератор)."""
    video = get_object_or_404(PublicVideo, pk=pk, is_active=False)
    video.is_active = True
    video.save(update_fields=["is_active"])

    if video.source_job and video.source_job.status == GenerationJob.Status.PENDING_MODERATION:
        video.source_job.status = GenerationJob.Status.DONE
        video.source_job.save(update_fields=['status'])

    messages.success(request, f"Видео №{pk} опубликовано.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("gallery:moderation"))


@staff_member_required
@require_POST
def moderation_reject_video(request: HttpRequest, pk: int) -> HttpResponse:
    """Отклонить видео (модератор)."""
    video = get_object_or_404(PublicVideo, pk=pk)

    if video.source_job and video.source_job.status == GenerationJob.Status.PENDING_MODERATION:
        video.source_job.status = GenerationJob.Status.DONE
        video.source_job.save(update_fields=['status'])

    try:
        if video.thumbnail and video.thumbnail.name:
            video.thumbnail.delete(save=False)
    except Exception:
        pass
    video.delete()
    messages.info(request, f"Видео №{pk} отклонено и удалено.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("gallery:moderation"))


# ───────────────────────── DELETE VIDEO ─────────────────────────

@staff_member_required
@require_http_methods(["GET", "POST"])
def video_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Удалить видео (только staff)."""
    video = get_object_or_404(PublicVideo, pk=pk)
    next_url = request.GET.get("next") or reverse("gallery:index")

    if request.method == "POST":
        if hasattr(video, "is_active"):
            video.is_active = False
            video.save(update_fields=["is_active"])
        messages.success(request, "Видео скрыто из галереи.")
        return redirect(next_url)

    return render(
        request,
        "gallery/video_confirm_delete.html",
        {"video": video, "next": next_url},
    )
