# gallery/migrations/0002_category_photocomment_photolike_like_nullable_and_more.py
from django.conf import settings
from django.db import migrations, models, connection
import django.db.models.deletion
from django.db.models import Q


def drop_legacy_like_indexes(apps, schema_editor):
    """
    Удаляем старые индексы, если вдруг остались после предыдущих версий.

    PostgreSQL: DROP INDEX IF EXISTS <name>;
    MySQL:      DROP INDEX <name> ON <table>; (IF EXISTS не везде доступен, делаем через проверку SHOW INDEX)
    SQLite:     DROP INDEX IF EXISTS <name>; (ок, но оборачиваем в try на всякий случай)
    """
    vendor = connection.vendor
    table = "gallery_like"
    idx_names = ("uniq_like_user_job", "uix_like_user_job")

    with connection.cursor() as cursor:
        if vendor == "postgresql":
            for idx in idx_names:
                cursor.execute(f'DROP INDEX IF EXISTS "{idx}";')
        elif vendor == "mysql":
            for idx in idx_names:
                cursor.execute(f"SHOW INDEX FROM `{table}` WHERE Key_name = %s;", (idx,))
                if cursor.fetchone():
                    cursor.execute(f"DROP INDEX `{idx}` ON `{table}`;")
        else:
            # SQLite / другие — пробуем мягко
            for idx in idx_names:
                try:
                    cursor.execute(f"DROP INDEX IF EXISTS {idx};")
                except Exception:
                    pass


class Migration(migrations.Migration):

    dependencies = [
        ("gallery", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1) Защитно: удалить возможные старые индексы для Like(user, job)
        migrations.RunPython(drop_legacy_like_indexes, migrations.RunPython.noop),

        # 2) Категории
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=72, unique=True)),
            ],
            options={"ordering": ("name",), "verbose_name": "Категория", "verbose_name_plural": "Категории"},
        ),

        # 3) M2M: PublicPhoto.categories
        migrations.AddField(
            model_name="publicphoto",
            name="categories",
            field=models.ManyToManyField(blank=True, related_name="photos", to="gallery.category"),
        ),

        # 4) Лайки публичных фото
        migrations.CreateModel(
            name="PhotoLike",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("photo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to="gallery.publicphoto")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="photo_likes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Лайк фото", "verbose_name_plural": "Лайки фото"},
        ),
        migrations.AddConstraint(
            model_name="photolike",
            constraint=models.UniqueConstraint(
                fields=("user", "photo"),
                name="uix_photo_like_user_photo",
                condition=Q(("user__isnull", False)),
            ),
        ),

        # 5) Комментарии публичных фото
        migrations.CreateModel(
            name="PhotoComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField(max_length=2000)),
                ("is_visible", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("photo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="gallery.publicphoto")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="photo_comments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",), "verbose_name": "Комментарий к фото", "verbose_name_plural": "Комментарии к фото"},
        ),

        # 6) Like (к GenerationJob): делаем user nullable и вешаем новый условный unique
        migrations.AlterField(
            model_name="like",
            name="user",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="likes", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name="like",
            constraint=models.UniqueConstraint(
                fields=("user", "job"),
                name="uix_like_user_job",
                condition=Q(("job__isnull", False)) & Q(("user__isnull", False)),
            ),
        ),
    ]
