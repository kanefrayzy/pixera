from __future__ import annotations

from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import Notification, Profile
from django.contrib.auth import get_user_model


def _actor_info(user):
    if not user:
        return {"username": "", "avatar_url": ""}
    try:
        prof = getattr(user, "profile", None)
        avatar_url = getattr(getattr(prof, "avatar", None), "url", "") if prof else ""
    except Exception:
        avatar_url = ""
    return {"username": user.username, "avatar_url": avatar_url}


@login_required
@require_http_methods(["GET"])
def notifications_unread_count(request: HttpRequest):
    cnt = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({"ok": True, "unread": int(cnt)})


@login_required
@require_http_methods(["GET"])
def notifications_list(request: HttpRequest):
    """
    Возвращает список уведомлений пользователя.
    GET:
      - limit: 1..50 (по умолчанию 20)
      - cursor: id (int) — пагинация назад (id < cursor)
    Возвращает:
      { ok, items: [...], next_cursor }
    Также «иногда» подмешивает RECOMMENDATION (раз в 6 часов), как просили.
    """
    try:
        limit = int(request.GET.get("limit") or "20")
    except Exception:
        limit = 20
    limit = max(1, min(limit, 50))

    try:
        cursor = int(request.GET.get("cursor") or "0")
    except Exception:
        cursor = 0

    now = timezone.now()
    # Иногда добавляем рекомендацию (если не было за последние 6 часов)
    try:
        six_hours_ago = now - timedelta(hours=6)
        has_recent_rec = Notification.objects.filter(
            recipient=request.user,
            type=Notification.Type.RECOMMENDATION,
            created_at__gte=six_hours_ago,
        ).exists()
        if not has_recent_rec:
            # Простая рекомендация — посмотреть тренды/профили
            Notification.create(
                recipient=request.user,
                actor=None,
                type=Notification.Type.RECOMMENDATION,
                message="Вам могут понравиться тренды и новые авторы",
                link="/gallery/trending",
                payload={"kind": "trending"},
            )
    except Exception:
        pass

    qs = Notification.objects.filter(recipient=request.user)
    if cursor > 0:
        qs = qs.filter(id__lt=cursor)
    qs = qs.select_related("actor").order_by("-created_at", "-id")[:limit + 1]

    items = []
    next_cursor = None
    slice_qs = list(qs)
    if len(slice_qs) > limit:
        next_cursor = slice_qs[-1].id
        slice_qs = slice_qs[:limit]

    # Helper to enrich notification with preview and robust link
    from django.utils.text import slugify
    from django.urls import reverse
    try:
        from gallery.models import PublicPhoto, PublicVideo, PhotoComment, VideoComment, JobComment
    except Exception:
        PublicPhoto = PublicVideo = PhotoComment = VideoComment = JobComment = None
    try:
        from generate.models import GenerationJob
    except Exception:
        GenerationJob = None

    def _preview_for(n):
        payload = getattr(n, "payload", {}) or {}
        kind = None
        image_url = ""
        video_url = ""
        poster_url = ""
        text = ""
        link = n.link or ""
        t = n.type or ""
        is_deleted = False

        # Photo notifications
        if t in ("like_photo", "comment_photo", "reply_photo", "comment_like_photo"):
            pid = int(payload.get("photo_id") or 0)
            cid = int(payload.get("comment_id") or 0)
            rid = int(payload.get("reply_id") or 0)
            if pid and PublicPhoto:
                try:
                    p = PublicPhoto.objects.filter(id=pid, is_active=True).only("image", "title", "slug").first()
                except Exception:
                    p = None
                if p and getattr(p, "image", None):
                    try:
                        image_url = getattr(p.image, "url", "") or ""
                        kind = "photo"  # Always set kind for photos
                    except Exception:
                        pass
                else:
                    # Photo doesn't exist or is deleted/inactive
                    is_deleted = True
                    kind = "photo_deleted"
            # Build/fix link
            if pid:
                if is_deleted:
                    link = "/dashboard/publication-deleted"
                elif not link:
                    try:
                        # Use slug if available
                        if p and getattr(p, "slug", None):
                            link = reverse("gallery:slug_detail", args=[p.slug])
                        else:
                            link = reverse("gallery:photo_detail", args=[pid])
                    except Exception:
                        link = f"/gallery/photo/{pid}"
            # Prefer reply text/anchor if present
            anchor_id = rid or cid
            if anchor_id and not is_deleted:
                # Используем превью из payload, если есть, иначе запрашиваем из БД
                text = payload.get("comment_text", "")
                if not text and PhotoComment:
                    try:
                        c = PhotoComment.objects.filter(id=anchor_id).only("text").first()
                        text = ((c.text or "")[:140]) if c else ""
                    except Exception:
                        pass
                link = f"{link}#c{anchor_id}" if link else link

        # Video notifications
        elif t in ("like_video", "comment_video", "reply_video", "comment_like_video"):
            vid = int(payload.get("video_id") or 0)
            cid = int(payload.get("comment_id") or 0)
            rid = int(payload.get("reply_id") or 0)
            if vid and PublicVideo:
                try:
                    v = PublicVideo.objects.filter(id=vid, is_active=True).first()
                except Exception:
                    v = None
                if v:
                    try:
                        # Get thumbnail URL
                        thumb_field = getattr(v, "thumbnail", None)
                        if thumb_field and hasattr(thumb_field, "url"):
                            poster_url = thumb_field.url or ""
                        elif thumb_field and hasattr(thumb_field, "name") and thumb_field.name:
                            from django.core.files.storage import default_storage
                            poster_url = default_storage.url(thumb_field.name)
                        else:
                            poster_url = ""

                        # Get video URL - try video_url field first, then video field
                        video_url = ""
                        if hasattr(v, "video_url") and v.video_url:
                            video_url = str(v.video_url)
                        elif hasattr(v, "video") and v.video:
                            try:
                                video_url = v.video.url
                            except Exception:
                                pass

                        # If no direct URL, use stream endpoint
                        if not video_url:
                            try:
                                from django.urls import reverse
                                video_url = reverse("gallery:video_stream", args=[vid])
                            except Exception:
                                video_url = f"/gallery/video/{vid}/stream"

                        image_url = poster_url

                        if not image_url:
                            # Inline SVG placeholder for video preview (avoids black box)
                            from urllib.parse import quote as _uq
                            svg = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="150" viewBox="0 0 120 150"><rect width="120" height="150" rx="12" fill="#0f0f12"/><circle cx="60" cy="75" r="26" fill="#000" opacity="0.4"/><polygon points="54,62 54,88 78,75" fill="#fff"/></svg>'
                            image_url = "data:image/svg+xml;utf8," + _uq(svg)
                        kind = "video"
                    except Exception:
                        pass
                elif vid:
                    # Video exists but is deleted/inactive
                    is_deleted = True
                    kind = "video_deleted"
            # Build/fix link (always force to video detail when we know video_id)
            if vid:
                if is_deleted:
                    link = "/dashboard/publication-deleted"
                else:
                    try:
                        # Use slug if available
                        if v and getattr(v, "slug", None):
                            link = reverse("gallery:slug_detail", args=[v.slug])
                        else:
                            link = reverse("gallery:video_detail_by_pk", args=[vid])
                    except Exception:
                        link = f"/gallery/video/{vid}"
            # Prefer reply text/anchor if present
            anchor_id = rid or cid
            if anchor_id and not is_deleted:
                # Используем превью из payload, если есть, иначе запрашиваем из БД
                text = payload.get("comment_text", "")
                if not text and VideoComment:
                    try:
                        c = VideoComment.objects.filter(id=anchor_id).only("text").first()
                        text = ((c.text or "")[:140]) if c else ""
                    except Exception:
                        pass
                link = f"{link}#c{anchor_id}" if link else link

        # Job (unpublished generation) notifications
        elif t in ("like_job", "comment_job", "reply_job", "comment_like_job"):
            jid = int(payload.get("job_id") or 0)
            cid = int(payload.get("comment_id") or 0)
            rid = int(payload.get("reply_id") or 0)
            gen_type = payload.get("generation_type", "image")  # Get generation type from payload

            if jid and GenerationJob:
                try:
                    j = GenerationJob.objects.filter(id=jid).only("user_id", "prompt", "result_image", "persisted", "generation_type", "result_video_url").first()
                except Exception:
                    j = None

                # Update gen_type from job if available
                if j and hasattr(j, "generation_type"):
                    gen_type = getattr(j, "generation_type", "image")

                # Check if job is deleted
                if not j or not getattr(j, "persisted", True):
                    is_deleted = True
                    # Set kind based on generation type
                    if gen_type == "video":
                        kind = "video_deleted"
                    else:
                        kind = "photo_deleted"
                # Preview only для владельца (job_image требует owner)
                elif j and getattr(j, "user_id", None) == getattr(request.user, "id", None):
                    try:
                        # Set kind based on generation type
                        if gen_type == "video":
                            kind = "video"
                            # For video jobs, get video URL from result_video_url
                            video_url = getattr(j, "result_video_url", "") or ""
                            # Use video URL itself as poster (browser will show first frame)
                            # Or use SVG placeholder
                            from urllib.parse import quote as _uq
                            svg = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="150" viewBox="0 0 120 150"><rect width="120" height="150" rx="12" fill="#1a1a1a"/><circle cx="60" cy="75" r="26" fill="#000" opacity="0.4"/><polygon points="54,62 54,88 78,75" fill="#fff"/></svg>'
                            poster_url = "data:image/svg+xml;utf8," + _uq(svg)
                            image_url = poster_url
                            # Also set poster_url for video element
                        else:
                            kind = "photo"
                            # Use direct image URL if available, otherwise use job_image endpoint
                            if hasattr(j, 'result_image') and j.result_image:
                                try:
                                    image_url = j.result_image.url
                                except Exception:
                                    s = slugify((j.prompt or "job"), allow_unicode=True) or "job"
                                    image_url = reverse("generate:job_image", args=[j.id, s])
                            else:
                                s = slugify((j.prompt or "job"), allow_unicode=True) or "job"
                                image_url = reverse("generate:job_image", args=[j.id, s])
                    except Exception:
                        image_url = ""
                # Build/fix link to job detail with anchor
                if is_deleted:
                    link = "/dashboard/publication-deleted"
                elif not link:
                    try:
                        s = slugify((getattr(j, "prompt", "") or "job"), allow_unicode=True) or "job"
                        link = reverse("generate:job_detail", args=[jid, s])
                    except Exception:
                        link = f"/generate/job/{jid}"
                anchor_id = rid or cid
                if anchor_id and not is_deleted:
                    link = f"{link}#c{anchor_id}"
                # For replies/likes, try include comment/reply snippet
                text_id = rid or cid
                if text_id and JobComment and not is_deleted:
                    try:
                        c = JobComment.objects.filter(id=text_id).only("text").first()
                        text = ((c.text or "")[:140]) if c else ""
                    except Exception:
                        pass

        # Wallet/admin/recommendation — no preview image, keep link as provided
        return {
            "kind": kind,
            "image_url": image_url,
            "video_url": video_url,
            "poster_url": poster_url,
            "text": text,
            "link": link or (n.link or ""),
            "is_deleted": is_deleted,
        }

    for n in slice_qs:
        prev = _preview_for(n)
        items.append({
            "id": n.id,
            "type": n.type,
            "message": n.message,
            "link": prev.get("link") or n.link,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
            "actor": _actor_info(n.actor),
            "preview": {
                "kind": prev.get("kind"),
                "image_url": prev.get("image_url") or "",
                "video_url": prev.get("video_url") or "",
                "poster_url": prev.get("poster_url") or "",
                "text": prev.get("text") or "",
            },
        })
    return JsonResponse({"ok": True, "items": items, "next_cursor": next_cursor})


@login_required
@require_http_methods(["POST"])
def notifications_mark_read(request: HttpRequest):
    """
    Пометить уведомления как прочитанные.
    In:
      - id: одно id (int) или
      - ids: CSV строка id (например "1,2,3")
    """
    try:
        ids_raw = request.POST.get("ids") or ""
        if ids_raw:
            ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]
        else:
            one_id = int(request.POST.get("id") or "0")
            ids = [one_id] if one_id > 0 else []
    except Exception:
        ids = []

    if not ids:
        return JsonResponse({"ok": False, "error": "no ids"}, status=400)

    updated = Notification.objects.filter(recipient=request.user, id__in=ids, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True, "updated": int(updated)})


@login_required
@require_http_methods(["POST"])
def notifications_mark_all_read(request: HttpRequest):
    updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True, "updated": int(updated)})
