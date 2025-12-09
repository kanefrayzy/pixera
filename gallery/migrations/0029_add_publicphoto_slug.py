from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gallery", "0028_backfill_publicvideo_slugs"),
    ]

    operations = [
        migrations.AddField(
            model_name="publicphoto",
            name="slug",
            field=models.SlugField(
                verbose_name="Слаг",
                max_length=180,
                unique=True,
                null=True,
                blank=True,
                db_index=True,
            ),
        ),
    ]
