from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gallery", "0026_jobhide"),
    ]

    operations = [
        migrations.AddField(
            model_name="publicvideo",
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
