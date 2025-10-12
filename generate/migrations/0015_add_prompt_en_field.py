from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('generate', '0014_seed_extended_prompt_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoryprompt',
            name='prompt_en',
            field=models.TextField(
                verbose_name='Английский промпт',
                help_text='Профессиональный английский промпт для генерации',
                blank=True,
                default=''
            ),
        ),
    ]
