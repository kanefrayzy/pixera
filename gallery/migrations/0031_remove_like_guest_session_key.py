# Generated migration to remove guest_session_key from gallery_like table
from django.db import migrations


def drop_guest_session_key_column(apps, schema_editor):
    """
    Actually drop the guest_session_key column from gallery_like table if it exists.
    The column was only removed from Django state in migration 0004, but not from database.
    """
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'gallery_like' AND column_name = 'guest_session_key'
        """)
        if cursor.fetchone():
            # Drop related constraints first
            cursor.execute("""
                DO $$
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (
                        SELECT constraint_name
                        FROM information_schema.constraint_column_usage
                        WHERE table_name = 'gallery_like' AND column_name = 'guest_session_key'
                    ) LOOP
                        EXECUTE 'ALTER TABLE gallery_like DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name) || ' CASCADE';
                    END LOOP;
                END $$;
            """)
            # Drop related indexes
            cursor.execute("""
                DO $$
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (
                        SELECT indexname
                        FROM pg_indexes
                        WHERE tablename = 'gallery_like' AND indexdef LIKE '%guest_session_key%'
                    ) LOOP
                        EXECUTE 'DROP INDEX IF EXISTS ' || quote_ident(r.indexname);
                    END LOOP;
                END $$;
            """)
            # Now drop the column
            cursor.execute("ALTER TABLE gallery_like DROP COLUMN IF EXISTS guest_session_key CASCADE")


class Migration(migrations.Migration):

    dependencies = [
        ("gallery", "0030_backfill_publicphoto_slugs"),
    ]

    operations = [
        migrations.RunPython(drop_guest_session_key_column, reverse_code=migrations.RunPython.noop),
    ]
