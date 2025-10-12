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
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_http_methods

from generate.models import GenerationJob
from .models import (
    PublicVideo,
    VideoLike,
    VideoComment,
    VideoCommentLike,
    Category,
)
from .forms import PhotoCommentForm  # Переиспользуем ту же форму


# ───────────────────────── HELPERS ─────────────────────────

def _ensure_session_key(request: HttpRequest) -> str:
    """Гарантируем наличие session_key."""
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _mark_video_viewed_once(_request: HttpRequest, video_id: int) -> None:
    """Инкремент счётчика просмотров видео."""
    PublicVideo.objects.filter(pk=video_id).update(view_count=F("view_count") + 1)


# ───────────────────────── VIDEO DETAIL ─────────────────────────

def video_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Детальная страница видео с комментариями."""
    video = get_object_or_404(
        PublicVideo.objects.select_related("uploaded_by", "category"),
        pk=pk,
        is_active=True,
    )

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
        if getattr(video, "category_id", None):
            related_videos = list(
                base_qs.filter(category_id=video.category_id)
                       .order_by("-likes_count", "-view_count", "-created_at")[:8]
            )
        if len(related_videos) < 8:
            exclude_ids = [video.pk] + [v.pk for v in related_videos]
            fill = list(
                PublicVideo.objects.filter(is_active=True)
                .exclude(pk__in=exclude_ids)
                .order_by("-likes_count", "-view_count", "-created_at")[: 8 - len(related_videos)]
            )
            related_videos.extend(fill)
    except Exception:
        related_videos = []

    return render(
        request,
        "gallery/video_detail.html",
        {
            "video": video,
            "comments": comments,
            "liked": liked,
            "liked_comment_ids": liked_comment_ids,
            "comment_form": PhotoCommentForm(),
            "related_videos": related_videos,
        },
    )


# ───────────────────────── VIDEO LIKE ─────────────────────────

@require_POST
def video_like(request: HttpRequest, pk: int) -> HttpResponse:
    """Тоггл лайка видео."""
    try:
        video = PublicVideo.objects.get(pk=pk, is_active=True)
    except PublicVideo.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Video not found"}, status=404)

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

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "liked": liked, "count": new_count})
    return redirect(
        request.META.get("HTTP_REFERER")
        or reverse("gallery:video_detail", args=[pk])
    )


# ───────────────────────── VIDEO COMMENT ─────────────────────────

@login_required
@require_POST
def video_comment(request: HttpRequest, pk: int) -> HttpResponse:
    """Добавить корневой комментарий к видео."""
    video = get_object_or_404(PublicVideo, pk=pk, is_active=True)
    form = PhotoCommentForm(request.POST)
    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
        messages.error(request, "Введите корректный комментарий.")
        return redirect(reverse("gallery:video_detail", args=[pk]))

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

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})

    return redirect(reverse("gallery:video_detail", args=[pk]))


# ───────────────────────── VIDEO COMMENT REPLY ─────────────────────────

@login_required
@require_POST
def video_comment_reply(request: HttpRequest, pk: int) -> HttpResponse:
    """Ответ на комментарий к видео."""
    parent = get_object_or_404(VideoComment, pk=pk, is_visible=True)
    form = PhotoCommentForm(request.POST)
    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
        messages.error(request, "Введите корректный ответ.")
        return redirect(reverse("gallery:video_detail", args=[parent.video_id]))

    with transaction.atomic():
        VideoComment.objects.create(
            video=parent.video,
            user=request.user,
            text=form.cleaned_data["text"],
            parent=parent,
        )
        PublicVideo.objects.filter(pk=parent.video_id).update(
            comments_count=F("comments_count") + 1
        )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})

    return redirect(
        f"{reverse('gallery:video_detail', args=[parent.video_id])}#c{parent.pk}"
    )


# ───────────────────────── VIDEO COMMENT LIKE ─────────────────────────

@require_POST
def video_comment_like(request: HttpRequest, pk: int) -> HttpResponse:
    """Тоггл лайка комментария к видео."""
    comment = get_object_or_404(VideoComment, pk=pk, is_visible=True)
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

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "liked": liked, "count": new_count})
    return redirect(
        request.META.get("HTTP_REFERER")
        or reverse("gallery:video_detail", args=[comment.video_id])
    )


# ───────────────────────── SHARE VIDEO FROM JOB ─────────────────────────

@login_required
def share_video_from_job(request, job_id: int):
    """Публикация видео из задачи генерации в галерею."""
    job = get_object_or_404(
        GenerationJob.objects.select_related("user"),
        pk=job_id,
        user=request.user,
        generation_type='video',
        status=GenerationJob.Status.DONE,
    )

    if not job.result_video_url:
        messages.error(request, "У этой генерации нет готового видео.")
        return redirect("dashboard:my_jobs")

    if request.method == "POST":
        from .forms import ShareFromJobForm
        form = ShareFromJobForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data.get("title", "")
            caption = form.cleaned_data.get("caption", "")

            # Thumbnail - из result_image задачи
            thumbnail_file = None
            if job.result_image and job.result_image.name:
                try:
                    src_name = job.result_image.name.rsplit("/", 1)[-1]
                    dst_dir = f"public_videos/{job.created_at:%Y/%m}/"
                    dst_path = default_storage.generate_filename(dst_dir + src_name)
                    with default_storage.open(job.result_image.name, "rb") as fh:
                        thumbnail_file = ContentFile(fh.read())
                        thumbnail_file.name = dst_path
                except Exception:
                    thumbnail_file = None

            will_publish_now = request.user.is_staff

            video = PublicVideo.objects.create(
                video_url=job.result_video_url,
                thumbnail=thumbnail_file,
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
        form = ShareFromJobForm(initial={"title": (job.prompt or "").strip()[:140], "caption": ""})

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
