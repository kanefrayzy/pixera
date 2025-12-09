# Generated manually: Add JobSave model (bookmarks for GenerationJob)
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("gallery", "0022_photosave_videosave"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("generate", "0023_add_wan25_preview"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobSave",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saves", to="generate.generationjob", db_index=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="job_saves", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Сохранение задачи",
                "verbose_name_plural": "Сохранения задач",
            },
        ),
        migrations.AddConstraint(
            model_name="jobsave",
            constraint=models.UniqueConstraint(fields=("user", "job"), name="uq_job_save_user"),
        ),
    ]
