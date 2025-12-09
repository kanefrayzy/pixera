"""
Fix image model fields to make them optional with defaults
"""

def create_migration():
    """Create migration to make fields optional"""

    migration_content = '''# Generated migration to make image model fields optional
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('generate', '0XXX_previous_migration'),  # Update this!
    ]

    operations = [
        # Make steps fields optional with defaults
        migrations.AlterField(
            model_name='imagemodelconfiguration',
            name='min_steps',
            field=models.PositiveIntegerField(
                verbose_name='Минимум шагов',
                default=1,
                blank=True
            ),
        ),
        migrations.AlterField(
            model_name='imagemodelconfiguration',
            name='max_steps',
            field=models.PositiveIntegerField(
                verbose_name='Максимум шагов',
                default=50,
                blank=True
            ),
        ),
        migrations.AlterField(
            model_name='imagemodelconfiguration',
            name='default_steps',
            field=models.PositiveIntegerField(
                verbose_name='Шагов по умолчанию',
                default=20,
                blank=True
            ),
        ),

        # Make CFG scale fields optional with defaults
        migrations.AlterField(
            model_name='imagemodelconfiguration',
            name='min_cfg_scale',
            field=models.DecimalField(
                verbose_name='Минимум CFG',
                max_digits=4,
                decimal_places=1,
                default=1.0,
                blank=True
            ),
        ),
        migrations.AlterField(
            model_name='imagemodelconfiguration',
            name='max_cfg_scale',
            field=models.DecimalField(
                verbose_name='Максимум CFG',
                max_digits=4,
                decimal_places=1,
                default=20.0,
                blank=True
            ),
        ),
        migrations.AlterField(
            model_name='imagemodelconfiguration',
            name='default_cfg_scale',
            field=models.DecimalField(
                verbose_name='CFG по умолчанию',
                max_digits=4,
                decimal_places=1,
                default=7.0,
                blank=True
            ),
        ),

        # Make reference images field optional
        migrations.AlterField(
            model_name='imagemodelconfiguration',
            name='max_reference_images',
            field=models.PositiveIntegerField(
                verbose_name='Максимум референсов',
                default=1,
                blank=True,
                help_text='Максимальное количество референсных изображений (1-2)'
            ),
        ),

        # Make number results field optional
        migrations.AlterField(
            model_name='imagemodelconfiguration',
            name='max_number_results',
            field=models.PositiveIntegerField(
                verbose_name='Максимум результатов',
                default=4,
                blank=True,
                help_text='Максимальное количество изображений за раз'
            ),
        ),
    ]
'''

    print("Migration content:")
    print("=" * 80)
    print(migration_content)
    print("=" * 80)
    print()
    print("To apply this migration:")
    print("1. Find the latest migration number in generate/migrations/")
    print("2. Create a new file: generate/migrations/0XXX_make_image_fields_optional.py")
    print("3. Copy the content above")
    print("4. Update the dependency to the previous migration")
    print("5. Run: python manage.py migrate")

    return migration_content


def update_model():
    """Update the model file directly"""

    model_path = 'generate/models_image.py'

    with open(model_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add blank=True to the fields
    replacements = [
        ('min_steps = models.PositiveIntegerField("Минимум шагов", default=1)',
         'min_steps = models.PositiveIntegerField("Минимум шагов", default=1, blank=True)'),

        ('max_steps = models.PositiveIntegerField("Максимум шагов", default=50)',
         'max_steps = models.PositiveIntegerField("Максимум шагов", default=50, blank=True)'),

        ('default_steps = models.PositiveIntegerField("Шагов по умолчанию", default=20)',
         'default_steps = models.PositiveIntegerField("Шагов по умолчанию", default=20, blank=True)'),

        ('min_cfg_scale = models.DecimalField(\n        "Минимум CFG",\n        max_digits=4,\n        decimal_places=1,\n        default=1.0\n    )',
         'min_cfg_scale = models.DecimalField(\n        "Минимум CFG",\n        max_digits=4,\n        decimal_places=1,\n        default=1.0,\n        blank=True\n    )'),

        ('max_cfg_scale = models.DecimalField(\n        "Максимум CFG",\n        max_digits=4,\n        decimal_places=1,\n        default=20.0\n    )',
         'max_cfg_scale = models.DecimalField(\n        "Максимум CFG",\n        max_digits=4,\n        decimal_places=1,\n        default=20.0,\n        blank=True\n    )'),

        ('default_cfg_scale = models.DecimalField(\n        "CFG по умолчанию",\n        max_digits=4,\n        decimal_places=1,\n        default=7.0\n    )',
         'default_cfg_scale = models.DecimalField(\n        "CFG по умолчанию",\n        max_digits=4,\n        decimal_places=1,\n        default=7.0,\n        blank=True\n    )'),

        ('max_reference_images = models.PositiveIntegerField(\n        "Максимум референсов",\n        default=1,\n        help_text="Максимальное количество референсных изображений (1-2)"\n    )',
         'max_reference_images = models.PositiveIntegerField(\n        "Максимум референсов",\n        default=1,\n        blank=True,\n        help_text="Максимальное количество референсных изображений (1-2)"\n    )'),

        ('max_number_results = models.PositiveIntegerField(\n        "Максимум результатов",\n        default=4,\n        help_text="Максимальное количество изображений за раз"\n    )',
         'max_number_results = models.PositiveIntegerField(\n        "Максимум результатов",\n        default=4,\n        blank=True,\n        help_text="Максимальное количество изображений за раз"\n    )'),
    ]

    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            print(f"✅ Updated field")
        else:
            print(f"⚠️  Field not found or already updated")

    # Write back
    with open(model_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print()
    print("✅ Model file updated!")
    print()
    print("Next steps:")
    print("1. Run: python manage.py makemigrations")
    print("2. Run: python manage.py migrate")


if __name__ == '__main__':
    print("Fixing image model optional fields...")
    print()

    print("Step 1: Updating model file...")
    update_model()

    print()
    print("Step 2: Migration template...")
    create_migration()
