from django.db import migrations

def seed_suggestions(apps, schema_editor):
    SuggestionCategory = apps.get_model("generate", "SuggestionCategory")
    Suggestion = apps.get_model("generate", "Suggestion")

    if SuggestionCategory.objects.exists():
        return  # уже наполнено

    data = [
        {
            "name": "Фотопортреты", "slug": "portraits", "order": 10, "is_active": True,
            "items": [
                ("Cinematic portrait", "cinematic portrait, soft studio light, 85mm lens, shallow DOF, rim light, RAW photo, Kodak Portra 400"),
                ("Beauty close-up", "beauty close-up, skin texture, softbox lighting, 100mm macro, high detail, glossy lips, editorial"),
                ("Moody noir", "black and white portrait, low key lighting, hard shadows, film grain, 50mm, dramatic look"),
            ],
        },
        {
            "name": "Пейзажи", "slug": "landscapes", "order": 20, "is_active": True,
            "items": [
                ("Golden hour", "epic landscape, golden hour, volumetric light, mist, ultrawide 16mm, high dynamic range"),
                ("Nordic fjord", "norwegian fjord, overcast sky, wet rocks, cold palette, long exposure water, 24mm"),
            ],
        },
        {
            "name": "Предметка", "slug": "product", "order": 30, "is_active": True,
            "items": [
                ("Studio packshot", "product shot on seamless backdrop, soft studio light, reflections control, 85mm, clean shadows"),
                ("Metal + glass", "premium gadget, brushed aluminum, glass reflections, specular highlights, dark background"),
            ],
        },
        {
            "name": "UI / Иконки", "slug": "ui", "order": 40, "is_active": True,
            "items": [
                ("Minimal app icon", "minimal app icon, flat, high contrast, simple shape, centered, 1024x1024"),
                ("Neumorphic card", "neumorphism ui card, soft inner shadows, subtle gradients, clean layout"),
            ],
        },
        {
            "name": "Абстракт", "slug": "abstract", "order": 50, "is_active": True,
            "items": [
                ("Liquid marble", "abstract fluid marble, high contrast veins, glossy finish, macro"),
                ("Neon waves", "synthwave abstract shapes, neon glow, dark background, depth of field"),
            ],
        },
    ]

    order_s = 1
    for cat in data:
        c = SuggestionCategory.objects.create(
            name=cat["name"], slug=cat["slug"], order=cat["order"], is_active=cat["is_active"]
        )
        for title, text in cat["items"]:
            Suggestion.objects.create(
                category=c, title=title, text=text, is_active=True, order=order_s
            )
            order_s += 1

def unseed(apps, schema_editor):
    SuggestionCategory = apps.get_model("generate", "SuggestionCategory")
    slugs = ["portraits", "landscapes", "product", "ui", "abstract"]
    SuggestionCategory.objects.filter(slug__in=slugs).delete()

class Migration(migrations.Migration):
    dependencies = [
        ("generate", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(seed_suggestions, unseed),
    ]
