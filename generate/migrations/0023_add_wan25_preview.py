from django.db import migrations


def add_wan25_preview(apps, schema_editor):
    VideoModel = apps.get_model("generate", "VideoModel")
    if not VideoModel.objects.filter(model_id="runware:201@1").exists():
        VideoModel.objects.create(
            name="Wan2.5-Preview",
            model_id="runware:201@1",
            category="i2v",
            description=(
                "Wan2.5-Preview — премиальная I2V модель для оживления фотографий: "
                "естественные моргания и дыхание, лёгкие движения головы и волос, "
                "реалистичные отражения света и мягкое боке."
            ),
            token_cost=18,
            max_duration=8,
            max_resolution="1920x1080",
            is_active=True,
            order=1,
        )


def remove_wan25_preview(apps, schema_editor):
    VideoModel = apps.get_model("generate", "VideoModel")
    VideoModel.objects.filter(model_id="runware:201@1").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("generate", "0022_add_mode_to_video_models"),
    ]

    operations = [
        migrations.RunPython(add_wan25_preview, remove_wan25_preview),
    ]
