from django.db import migrations, models


def set_existing_jobs_persisted(apps, schema_editor):
    GenerationJob = apps.get_model('generate', 'GenerationJob')
    # Mark all existing jobs as persisted to preserve current behavior
    GenerationJob.objects.all().update(persisted=True)


class Migration(migrations.Migration):

    dependencies = [
        ('generate', '0026_videopromptsubcategory_videoprompt_subcategory_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='generationjob',
            name='persisted',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.RunPython(set_existing_jobs_persisted, migrations.RunPython.noop),
    ]
