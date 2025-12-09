from django.db import migrations
from django.utils.text import slugify
from django.db.models import Q


def forwards(apps, schema_editor):
    PublicVideo = apps.get_model("gallery", "PublicVideo")

    # Select videos with missing/empty slug
    qs = PublicVideo.objects.filter(Q(slug__isnull=True) | Q(slug__exact="")).only("id", "title", "slug")
    existing = set(
        PublicVideo.objects.exclude(slug__isnull=True).exclude(slug__exact="").values_list("slug", flat=True)
    )

    to_update = []
    for v in qs.iterator():
        base = slugify(v.title or "")[:120] or f"video-{v.id}"
        candidate = base
        # Ensure uniqueness; tie-breakers with pk to avoid long loops
        if candidate in existing:
            candidate = f"{base}-{v.id}"
            # Trim to max length 180 (matches field definition)
            candidate = candidate[:180]
        existing.add(candidate)
        v.slug = candidate
        to_update.append(v)

    if to_update:
        PublicVideo.objects.bulk_update(to_update, ["slug"])


def backwards(apps, schema_editor):
    # No-op: keep generated slugs
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("gallery", "0027_add_publicvideo_slug"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
