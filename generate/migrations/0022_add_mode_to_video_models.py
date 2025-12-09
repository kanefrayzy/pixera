# Generated migration for adding mode field to video models

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('generate', '0021_add_video_prompt_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='videopromptcategory',
            name='mode',
            field=models.CharField(
                choices=[('i2v', 'Image-to-Video'), ('t2v', 'Text-to-Video')],
                db_index=True,
                default='t2v',
                max_length=10,
                verbose_name='Режим'
            ),
        ),
        migrations.AddField(
            model_name='showcasevideo',
            name='mode',
            field=models.CharField(
                choices=[('i2v', 'Image-to-Video'), ('t2v', 'Text-to-Video')],
                db_index=True,
                default='t2v',
                max_length=10,
                verbose_name='Режим'
            ),
        ),
        migrations.AlterIndexTogether(
            name='videopromptcategory',
            index_together={('is_active', 'mode', 'order')},
        ),
        migrations.AlterIndexTogether(
            name='showcasevideo',
            index_together={('is_active', 'mode', 'order')},
        ),
    ]
