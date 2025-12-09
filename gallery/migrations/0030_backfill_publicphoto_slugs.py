from django.db import migrations
from django.utils.text import slugify
from django.db.models import Q


def forwards(apps, schema_editor):
    PublicPhoto = apps.get_model("gallery", "PublicPhoto")

    # Select photos with missing/empty slug
    qs = PublicPhoto.objects.filter(Q(slug__isnull=True) | Q(slug__exact="")).only("id", "title", "slug")
    existing = set(
        PublicPhoto.objects.exclude(slug__isnull=True).exclude(slug__exact="").values_list("slug", flat=True)
    )

    to_update = []
    for p in qs.iterator():
        base = slugify(p.title or "")[:120] or f"photo-{p.id}"
        candidate = base
        # Ensure uniqueness; if collision, tie-break with id
        if candidate in existing:
            candidate = f"{base}-{p.id}"
            candidate = candidate[:180]
        existing.add(candidate)
        p.slug = candidate
        to_update.append(p)

    if to_update:
        PublicPhoto.objects.bulk_update(to_update, ["slug"])


def backwards(apps, schema_editor):
    # Keep generated slugs
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("gallery", "0029_add_publicphoto_slug"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
