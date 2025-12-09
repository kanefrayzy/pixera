from __future__ import annotations

from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Q

try:
    # Use python-slugify for robust ASCII transliteration
    from slugify import slugify as _slugify_ascii

    def make_slug(text: str) -> str:
        return _slugify_ascii(text or "", allow_unicode=False)
except Exception:
    # Fallback to Django's slugify (limited transliteration)
    from django.utils.text import slugify as _dj_slugify

    def make_slug(text: str) -> str:
        return _dj_slugify(text or "")


class Command(BaseCommand):
    help = (
        "Regenerate ASCII slugs for PublicPhoto from title (transliterated to English). "
        "Ensures uniqueness and can rewrite default-like slugs (photo-<id>)."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show changes without saving.",
        )
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="Process only records with missing/empty slugs.",
        )
        parser.add_argument(
            "--force-all",
            action="store_true",
            help="Rewrite all slugs to transliterated version based on current title.",
        )
        parser.add_argument(
            "--rewrite-defaults",
            action="store_true",
            default=True,
            help="Rewrite default-like slugs such as 'photo-<id>' to transliterated title (default: True).",
        )

    def handle(self, *args, **opts) -> None:
        from gallery.models import PublicPhoto

        dry = bool(opts.get("dry_run"))
        only_missing = bool(opts.get("only_missing"))
        force_all = bool(opts.get("force_all"))
        rewrite_defaults = bool(opts.get("rewrite_defaults", True))

        qs = PublicPhoto.objects.only("id", "title", "slug")
        if only_missing:
            qs = qs.filter(Q(slug__isnull=True) | Q(slug__exact=""))

        updated = 0
        skipped = 0

        for p in qs.iterator():
            base = make_slug(p.title)[:120] or f"photo-{p.id}"
            candidate = base

            # If not forcing all, decide whether to skip
            if not force_all:
                if not p.slug:
                    pass  # will generate
                else:
                    # Skip if already correct
                    if p.slug == candidate:
                        skipped += 1
                        continue
                    # Skip if not rewriting defaults and it's a custom non-default slug
                    is_default_like = p.slug.startswith("photo-") and p.slug == f"photo-{p.id}"
                    if not (is_default_like and rewrite_defaults):
                        # by default we only fix missing and obvious defaults
                        if only_missing:
                            skipped += 1
                            continue
                        if not is_default_like:
                            skipped += 1
                            continue

            # Ensure uniqueness with suffix -1, -2, etc.
            i = 1
            unique = candidate
            while PublicPhoto.objects.filter(slug=unique).exclude(pk=p.pk).exists():
                unique = f"{candidate}-{i}"[:180]
                i += 1

            if p.slug == unique:
                skipped += 1
                continue

            self.stdout.write(f"{p.id}: '{p.slug}' -> '{unique}'")
            if not dry:
                p.slug = unique
                p.save(update_fields=["slug"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Updated: {updated}, Skipped: {skipped}"))
