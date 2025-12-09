from django.db import migrations


def set_wan25_duration_to_10(apps, schema_editor):
    VideoModel = apps.get_model('generate', 'VideoModel')
    VideoModel.objects.filter(model_id='runware:201@1').update(max_duration=10)


def revert_wan25_duration(apps, schema_editor):
    # Safe fallback: if previously was 8, revert to 8 (common default)
    VideoModel = apps.get_model('generate', 'VideoModel')
    # Only revert if currently 10 to avoid overwriting manual edits
    VideoModel.objects.filter(model_id='runware:201@1', max_duration=10).update(max_duration=8)


class Migration(migrations.Migration):

    dependencies = [
        ('generate', '0024_device_tracking_security'),
    ]

    operations = [
        migrations.RunPython(set_wan25_duration_to_10, revert_wan25_duration),
    ]
