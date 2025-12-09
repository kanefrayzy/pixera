from __future__ import annotations

from datetime import datetime, date
from typing import Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from generate.models import GenerationJob
from gallery.models import PublicPhoto, PublicVideo, Image  # personal gallery entries

import sys
import re
from urllib.parse import urlparse


def _parse_cutoff(s: str) -> datetime:
    """
    Parse cutoff date string to timezone-aware datetime at start of day.

    Supported formats:
      - YYYY-MM-DD
      - DD.MM
      - DD.MM.YYYY

    If year is omitted (DD.MM), current year is assumed.
    """
    s = (s or "").strip()
    tz = timezone.get_current_timezone()

    # YYYY-MM-DD
    m = re.fullmatch(r"(20\d{2})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = map(int, m.groups())
        return timezone.make_aware(datetime(y, mo, d, 0, 0, 0), tz)

    # DD.MM.YYYY
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(20\d{2})", s)
    if m:
        d, mo, y = map(int, m.groups())
        return timezone.make_aware(datetime(y, mo, d, 0, 0, 0), tz)

    # DD.MM (assume current year)
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})", s)
    if m:
        d, mo = map(int, m.groups())
        y = timezone.now().year
        return timezone.make_aware(datetime(y, mo, d, 0, 0, 0), tz)

    raise CommandError(f"Unrecognized date format: '{s}'. Use YYYY-MM-DD or DD.MM[.YYYY].")


def _url_to_storage_relpath(url: str) -> Optional[str]:
    """
    Convert a media URL (default_storage.url(name)) back to storage-relative path if possible.
    Only works for URLs under MEDIA_URL. Returns None if cannot map.
    """
    if not url:
        return None

    media_url = getattr(settings, "MEDIA_URL", "") or ""
    # Normalize to paths
    try:
        parsed = urlparse(url)
        url_path = parsed.path or url
    except Exception:
        url_path = url

    # MEDIA_URL may be absolute or relative.
    try:
        mu_parsed = urlparse(media_url)
        media_prefix = mu_parsed.path if mu_parsed.scheme else media_url
        if not media_prefix.startswith("/"):
            # ensure leading slash for path compare
            media_prefix = "/" + media_prefix
    except Exception:
        media_prefix = media_url

    if media_prefix and url_path.startswith(media_prefix):
        rel = url_path[len(media_prefix):]
        return rel.lstrip("/")

    # Fallback: if url is already a relative media path
    if media_url == "" and not url_path.startswith("/"):
        return url_path

    return None


def _delete_filefield(ff) -> int:
    """
    Delete a FileField from storage if present. Returns 1 if deleted else 0.
    """
    try:
        if ff and getattr(ff, "name", ""):
            name = ff.name
            if default_storage.exists(name):
                default_storage.delete(name)
                return 1
    except Exception:
        pass
    return 0


def _delete_storage_path(relpath: str) -> int:
    """
    Delete a storage-relative path if exists. Returns 1 if deleted else 0.
    """
    try:
        if relpath and default_storage.exists(relpath):
            default_storage.delete(relpath)
            return 1
    except Exception:
        pass
    return 0


class Command(BaseCommand):
    help = "Purge ALL photos/videos and generation jobs created BEFORE a cutoff date, including media files (my_jobs/layout/gallery)."

    def add_arguments(self, parser):
        parser.add_argument("--before", required=True, help="Cutoff date. Formats: YYYY-MM-DD or DD.MM[.YYYY] (e.g. 2025-11-01 or 1.11)")
        parser.add_argument("--yes", action="store_true", help="Confirm deletion without prompt")
        parser.add_argument("--batch", type=int, default=200, help="Batch size for deletes (default: 200)")

    def handle(self, *args, **options):
        cutoff_str = options["before"]
        batch_size = int(options["batch"] or 200)
        cutoff = _parse_cutoff(cutoff_str)

        self.stdout.write(self.style.WARNING("Purge request:"))
        self.stdout.write(f"  - Cutoff (strictly before): {cutoff.isoformat()}")
        self.stdout.write("  - Targets: PublicPhoto, PublicVideo, GenerationJob (with media files and related personal gallery entries)")
        self.stdout.write("  - Scope: ALL users (global)")

        if not options["yes"]:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("This operation is IRREVERSIBLE. It will DELETE database rows and media files."))
            self.stdout.write("Re-run with --yes to proceed, for example:")
            self.stdout.write(self.style.SQL_FIELD(f"  python manage.py purge_old_content --before {cutoff.date().isoformat()} --yes"))
            return

        total_photo_rows = 0
        total_photo_files = 0
        total_video_rows = 0
        total_video_thumbs = 0
        total_video_files = 0
        total_opt_files = 0
        total_job_rows = 0
        total_job_imgfiles = 0
        total_job_videofiles = 0
        total_job_ref_files = 0
        total_personal_images = 0

        # 1) Delete PublicPhoto older than cutoff
        qs_photos = PublicPhoto.objects.filter(created_at__lt=cutoff).only("id", "image", "created_at")
        self.stdout.write(self.style.NOTICE(f"Deleting PublicPhoto before {cutoff.date().isoformat()}..."))
        while True:
            ids = list(qs_photos.values_list("pk", flat=True)[:batch_size])
            if not ids:
                break
            for photo in PublicPhoto.objects.filter(pk__in=ids):
                total_photo_files += _delete_filefield(getattr(photo, "image", None))
            # Delete rows (cascade handles likes/comments/saves)
            deleted, _ = PublicPhoto.objects.filter(pk__in=ids).delete()
            total_photo_rows += int(deleted)

        # 2) Delete PublicVideo older than cutoff
        qs_videos = PublicVideo.objects.filter(created_at__lt=cutoff).only("id", "thumbnail", "video_url", "created_at")
        self.stdout.write(self.style.NOTICE(f"Deleting PublicVideo before {cutoff.date().isoformat()}..."))
        while True:
            vids = list(qs_videos.values_list("pk", flat=True)[:batch_size])
            if not vids:
                break
            for video in PublicVideo.objects.filter(pk__in=vids):
                # delete thumbnail file (FileField)
                total_video_thumbs += _delete_filefield(getattr(video, "thumbnail", None))
                # try to delete stored video file if URL points to MEDIA_URL
                rel = _url_to_storage_relpath(getattr(video, "video_url", "") or "")
                if rel:
                    total_video_files += _delete_storage_path(rel)
                # also try to delete optimized cache file, if exists
                opt_rel = f"public_videos_optimized/{video.pk}.mp4"
                total_opt_files += _delete_storage_path(opt_rel)

            deleted, _ = PublicVideo.objects.filter(pk__in=vids).delete()
            total_video_rows += int(deleted)

        # 3) Delete GenerationJob older than cutoff (my_jobs/layout)
        qs_jobs = GenerationJob.objects.filter(created_at__lt=cutoff).only(
            "id", "result_image", "result_video_url", "provider_payload", "created_at"
        )
        self.stdout.write(self.style.NOTICE(f"Deleting GenerationJob before {cutoff.date().isoformat()}..."))
        while True:
            jids = list(qs_jobs.values_list("pk", flat=True)[:batch_size])
            if not jids:
                break
            for job in GenerationJob.objects.filter(pk__in=jids):
                # delete personal gallery items tied to job
                try:
                    cnt = Image.objects.filter(generation_job=job).delete()[0]
                    total_personal_images += int(cnt)
                except Exception:
                    pass

                total_job_imgfiles += _delete_filefield(getattr(job, "result_image", None))

                # delete persisted local video (if stored under MEDIA_URL)
                rel2 = _url_to_storage_relpath(getattr(job, "result_video_url", "") or "")
                if rel2:
                    total_job_videofiles += _delete_storage_path(rel2)

                # delete retouch ref file if recorded in provider_payload
                try:
                    payload = getattr(job, "provider_payload", None) or {}
                    ref_path = payload.get("retouch_ref_path") if isinstance(payload, dict) else None
                    if ref_path:
                        total_job_ref_files += _delete_storage_path(str(ref_path))
                except Exception:
                    pass

            deleted, _ = GenerationJob.objects.filter(pk__in=jids).delete()
            total_job_rows += int(deleted)

        self.stdout.write(self.style.SUCCESS("Purge completed. Summary:"))
        self.stdout.write(f"  PublicPhoto: rows={total_photo_rows}, image_files_deleted={total_photo_files}")
        self.stdout.write(f"  PublicVideo: rows={total_video_rows}, thumb_files_deleted={total_video_thumbs}, video_files_deleted={total_video_files}, optimized_deleted={total_opt_files}")
        self.stdout.write(f"  GenerationJob: rows={total_job_rows}, result_images_deleted={total_job_imgfiles}, result_videos_deleted={total_job_videofiles}, retouch_refs_deleted={total_job_ref_files}, personal_images_deleted={total_personal_images}")
