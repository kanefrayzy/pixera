"""
Clear emoji icons from AspectRatioPreset in production database
Run via Docker: docker-compose exec web python clear_preset_icons_production.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pixera.settings')
django.setup()

from generate.models_aspect_ratio import AspectRatioPreset


def clear_icons():
    """Clear all icon values from presets"""
    print("🧹 Clearing emoji icons from AspectRatioPreset...")

    updated = AspectRatioPreset.objects.all().update(icon='')

    print(f"✅ Cleared icons from {updated} presets")

    # Verify
    with_icons = AspectRatioPreset.objects.exclude(icon='').count()
    print(f"📊 Presets with icons remaining: {with_icons}")


if __name__ == '__main__':
    clear_icons()
