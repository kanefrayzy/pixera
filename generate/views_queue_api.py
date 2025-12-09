from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.cache import cache
from django.conf import settings

from .models import GenerationJob


# Ownership check (parity with generate/views_api.py api_status)
def _owner_ok(request: HttpRequest, job: GenerationJob) -> bool:
    try:
        if job.user_id:
            return bool(request.user.is_authenticated and request.user.id == job.user_id)
        # guest: accept same session_key/gid/fp
        # Session key
        try:
            if not request.session.session_key:
                request.session.save()
        except Exception:
            pass
        sk = request.session.session_key or ""
        gid = request.COOKIES.get("gid", "")
        # "hard" fp hash kept by the same logic as in views_api
        try:
            from .views_api import _hard_fingerprint
            fp = _hard_fingerprint(request)
        except Exception:
            fp = ""
        return (job.guest_session_key == sk) or (job.guest_gid == gid) or (job.guest_fp == fp)
    except Exception:
        return False


def _delete_local_video_if_any(job: GenerationJob) -> None:
    """
    Delete locally stored video file if result_video_url points to MEDIA_URL.
    We do best-effort mapping URL -> storage path.
    """
    url = (job.result_video_url or "").strip()
    if not url:
        return
    try:
        media_url = str(getattr(settings, "MEDIA_URL", "/media/") or "/media/")
        if url.startswith(media_url) or (url.startswith("/") and "/media/" in media_url):
            # Strip MEDIA_URL prefix to get storage-relative path
            path = url[len(media_url):].lstrip("/") if url.startswith(media_url) else url.split("/media/", 1)[-1]
            if path:
                try:
                    default_storage.delete(path)
                except Exception:
                    pass
        else:
            # Handle absolute http(s)://host/media/... URLs
            parsed = urlparse(url)
            if parsed.path and "/media/" in parsed.path:
                path = parsed.path.split("/media/", 1)[-1]
                if path:
                    try:
                        default_storage.delete(path.lstrip("/"))
                    except Exception:
                        pass
    except Exception:
        pass


def _hard_delete_job(job: GenerationJob) -> None:
    """Permanently delete a job and all locally stored assets and caches."""
    # Delete result image file if any
    try:
        if getattr(job, "result_image", None) and job.result_image.name:
            job.result_image.delete(save=False)
    except Exception:
        pass

    # Delete local video file if any
    try:
        _delete_local_video_if_any(job)
    except Exception:
        pass

    # Purge caches used by job image endpoint
    try:
        cache.delete(f"genimg:{job.pk}")
        cache.delete(f"genimgurl:{job.pk}")
    except Exception:
        pass

    # Remove any personal gallery mapping if present
    try:
        from gallery.models import Image as GalleryImage
        GalleryImage.objects.filter(generation_job=job).delete()
    except Exception:
        pass

    # Finally delete the job row
    try:
        job.delete()
    except Exception:
        # As a safe fallback, mark as failed and hidden
        try:
            job.status = GenerationJob.Status.FAILED
            job.is_public = False
            job.persisted = False
            job.save(update_fields=["status", "is_public", "persisted"])
        except Exception:
            pass


@require_POST
@transaction.atomic
def queue_remove(request: HttpRequest) -> JsonResponse:
    """
    Permanently remove a single generation from the queue.
    Body can be form or JSON: { job_id: <id> }
    """
    job_id = request.POST.get("job_id")
    if not job_id:
        # Try JSON body
        try:
            import json
            data = json.loads(request.body.decode("utf-8") or "{}")
            job_id = str(data.get("job_id") or "").strip()
        except Exception:
            job_id = ""
    if not job_id:
        return JsonResponse({"ok": False, "error": "job_id required"}, status=400)

    job = get_object_or_404(GenerationJob, pk=int(job_id))
    if not _owner_ok(request, job):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    _hard_delete_job(job)
    return JsonResponse({"ok": True})


@require_POST
@transaction.atomic
def queue_clear(request: HttpRequest) -> JsonResponse:
    """
    Permanently clear the entire non-persisted queue for the current owner
    (user or same guest). Persisted items (saved to "Мои генерации") are kept.
    """
    # Determine owner scope
    jobs_qs = GenerationJob.objects.filter(persisted=False)
    if request.user.is_authenticated:
        jobs_qs = jobs_qs.filter(user=request.user)
    else:
        # Match by session/gid/fp
        try:
            if not request.session.session_key:
                request.session.save()
        except Exception:
            pass
        sk = request.session.session_key or ""
        gid = request.COOKIES.get("gid", "")
        try:
            from .views_api import _hard_fingerprint
            fp = _hard_fingerprint(request)
        except Exception:
            fp = ""
        jobs_qs = jobs_qs.filter(Q(guest_session_key=sk) | Q(guest_gid=gid) | Q(guest_fp=fp))

    # Delete jobs in small batches to keep transactions short
    ids = list(jobs_qs.values_list("id", flat=True)[:500])
    count_total = 0
    while ids:
        for jid in ids:
            try:
                job = GenerationJob.objects.get(pk=jid)
            except GenerationJob.DoesNotExist:
                continue
            if _owner_ok(request, job):
                _hard_delete_job(job)
                count_total += 1
        # Next batch
        ids = list(
            GenerationJob.objects.filter(persisted=False, id__lt=min(ids)).values_list("id", flat=True)[:500]
        )

    return JsonResponse({"ok": True, "deleted": count_total})
