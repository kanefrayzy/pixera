# gallery/migrations/0003_safe_drop_old_like_indexes.py
from django.db import migrations, connection

def drop_old_like_indexes(apps, schema_editor):
    """
    Кросс-СУБД удаление «старых» индексов/констрейнтов, если остались.
    Поддерживаемые имена: uniq_like_user_job, uniq_like_user_public.
    """
    vendor = connection.vendor
    table = "gallery_like"
    names = ("uniq_like_user_job", "uniq_like_user_public")

    with connection.cursor() as c:
        if vendor == "postgresql":
            # В Postgres пробуем и constraint, и index.
            for name in names:
                c.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{name}";')
                c.execute(f'DROP INDEX IF EXISTS "{name}";')
        elif vendor == "mysql":
            # В MySQL условные UNIQUE-констрейнты не используются — удаляем индекс, если он есть.
            for name in names:
                c.execute(f"SHOW INDEX FROM `{table}` WHERE Key_name = %s;", (name,))
                if c.fetchone():
                    c.execute(f"DROP INDEX `{name}` ON `{table}`;")
        else:
            # SQLite / прочие: мягко пробуем снести индекс.
            for name in names:
                try:
                    c.execute(f"DROP INDEX IF EXISTS {name};")
                except Exception:
                    pass


class Migration(migrations.Migration):

    dependencies = [
        ("gallery", "0002_category_photocomment_photolike_alter_like_options_and_more"),
    ]

    operations = [
        migrations.RunPython(drop_old_like_indexes, migrations.RunPython.noop),
        # Если в исходной 0003 были другие операции (AlterModelOptions и т.п.) — добавь их ниже.
    ]
