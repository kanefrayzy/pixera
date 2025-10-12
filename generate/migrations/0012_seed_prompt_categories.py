from django.db import migrations


def seed_categories(apps, schema_editor):
    PromptCategory = apps.get_model('generate', 'PromptCategory')
    CategoryPrompt = apps.get_model('generate', 'CategoryPrompt')
    
    # Данные категорий (без изображений - их нужно будет добавить через админку)
    categories_data = [
        {
            'name': 'Портрет',
            'slug': 'portrait',
            'description': 'Портретная фотография и изображения людей',
            'order': 1,
            'prompts': [
                ('Классический портрет', 'professional portrait, studio lighting, 85mm lens, shallow depth of field, neutral background, natural skin tones, sharp focus on eyes'),
                ('Драматический портрет', 'dramatic portrait, low key lighting, strong shadows, intense gaze, cinematic mood, dark background, high contrast'),
                ('Естественный свет', 'natural light portrait, golden hour, soft shadows, outdoor setting, warm tones, candid expression, bokeh background'),
                ('Деловой портрет', 'corporate headshot, professional attire, clean background, confident expression, studio lighting, sharp details'),
                ('Художественный портрет', 'artistic portrait, creative lighting, unique composition, expressive pose, vibrant colors, editorial style'),
                ('Черно-белый портрет', 'black and white portrait, high contrast, dramatic lighting, timeless aesthetic, fine art photography'),
                ('Уличный портрет', 'street portrait, urban background, natural light, candid moment, authentic expression, environmental context'),
                ('Модный портрет', 'fashion portrait, stylish outfit, professional makeup, dynamic pose, editorial lighting, trendy aesthetic'),
                ('Детский портрет', 'child portrait, playful expression, soft lighting, warm tones, natural setting, joyful mood'),
                ('Семейный портрет', 'family portrait, group composition, natural interaction, warm lighting, outdoor setting, genuine smiles'),
                ('Винтажный портрет', 'vintage portrait, retro styling, film grain, muted colors, classic pose, nostalgic mood'),
                ('Креативный портрет', 'creative portrait, experimental lighting, unusual angle, artistic composition, bold colors, conceptual approach'),
                ('Минималистичный портрет', 'minimalist portrait, clean background, simple composition, soft lighting, neutral tones, elegant simplicity'),
                ('Эмоциональный портрет', 'emotional portrait, expressive face, dramatic lighting, intense mood, storytelling composition'),
                ('Силуэт портрет', 'silhouette portrait, backlit subject, dramatic contrast, sunset background, mysterious mood, artistic composition'),
            ]
        },
        {
            'name': 'Пейзаж',
            'slug': 'landscape',
            'description': 'Природные и городские пейзажи',
            'order': 2,
            'prompts': [
                ('Горный пейзаж', 'mountain landscape, dramatic peaks, golden hour light, misty valleys, epic vista, wide angle, HDR'),
                ('Морской пейзаж', 'seascape, ocean waves, sunset sky, rocky shore, long exposure, vibrant colors, peaceful atmosphere'),
                ('Лесной пейзаж', 'forest landscape, tall trees, dappled sunlight, misty morning, lush greenery, nature photography'),
                ('Городской пейзаж', 'urban landscape, city skyline, blue hour, modern architecture, light trails, metropolitan view'),
                ('Пустынный пейзаж', 'desert landscape, sand dunes, dramatic sky, warm tones, vast expanse, golden hour'),
                ('Зимний пейзаж', 'winter landscape, snow covered, frozen lake, bare trees, cold atmosphere, soft light'),
                ('Осенний пейзаж', 'autumn landscape, colorful foliage, golden leaves, warm tones, misty morning, scenic view'),
                ('Весенний пейзаж', 'spring landscape, blooming flowers, fresh greenery, soft light, vibrant colors, renewal theme'),
                ('Ночной пейзаж', 'night landscape, starry sky, milky way, long exposure, dark silhouettes, cosmic atmosphere'),
                ('Водопад', 'waterfall landscape, flowing water, lush vegetation, long exposure, misty spray, natural beauty'),
                ('Сельский пейзаж', 'rural landscape, rolling hills, farmland, pastoral scene, golden fields, peaceful countryside'),
                ('Тропический пейзаж', 'tropical landscape, palm trees, turquoise water, white sand beach, paradise setting, vibrant colors'),
                ('Арктический пейзаж', 'arctic landscape, ice formations, northern lights, cold atmosphere, pristine wilderness, dramatic sky'),
                ('Каньон', 'canyon landscape, layered rock formations, dramatic depth, warm earth tones, epic scale, geological wonder'),
                ('Озеро', 'lake landscape, mirror reflection, mountain backdrop, calm water, serene atmosphere, natural beauty'),
            ]
        },
        {
            'name': 'Для разработки',
            'slug': 'development',
            'description': 'Изображения для веб-разработки и дизайна',
            'order': 3,
            'prompts': [
                ('Иконка приложения', 'app icon, modern design, clean lines, vibrant colors, minimalist style, professional look, 1024x1024'),
                ('Фон для сайта', 'website background, abstract pattern, subtle texture, modern aesthetic, professional design, seamless tile'),
                ('Баннер героя', 'hero banner, dynamic composition, bold typography, call to action, modern design, web optimized'),
                ('Иллюстрация для блога', 'blog illustration, editorial style, conceptual design, clean lines, modern aesthetic, engaging visual'),
                ('Инфографика', 'infographic design, data visualization, clean layout, professional colors, easy to understand, modern style'),
                ('UI элементы', 'UI elements, modern interface, clean design, consistent style, user friendly, professional look'),
                ('Логотип', 'logo design, minimalist style, memorable symbol, professional look, versatile usage, clean lines'),
                ('Иконки набор', 'icon set, consistent style, clean lines, modern design, various sizes, professional quality'),
                ('Презентация слайд', 'presentation slide, clean layout, professional design, data visualization, modern aesthetic, corporate style'),
                ('Email шаблон', 'email template, responsive design, clean layout, professional look, brand consistent, engaging visual'),
                ('Социальные медиа пост', 'social media post, eye catching design, bold typography, vibrant colors, engaging composition, shareable content'),
                ('Обложка для видео', 'video thumbnail, attention grabbing, bold text, vibrant colors, clear message, clickable design'),
                ('Мобильное приложение UI', 'mobile app UI, clean interface, intuitive design, modern aesthetic, user friendly, professional quality'),
                ('Дашборд дизайн', 'dashboard design, data visualization, clean layout, professional look, easy to read, modern interface'),
                ('Лендинг страница', 'landing page design, conversion focused, clean layout, compelling visuals, professional aesthetic, modern style'),
            ]
        },
        {
            'name': 'Эстетика',
            'slug': 'aesthetic',
            'description': 'Эстетичные и стильные изображения',
            'order': 4,
            'prompts': [
                ('Пастельная эстетика', 'pastel aesthetic, soft colors, dreamy atmosphere, gentle lighting, minimalist composition, Instagram worthy'),
                ('Темная эстетика', 'dark aesthetic, moody atmosphere, deep shadows, muted colors, mysterious vibe, artistic composition'),
                ('Неоновая эстетика', 'neon aesthetic, vibrant lights, cyberpunk vibes, glowing colors, urban night, futuristic mood'),
                ('Винтажная эстетика', 'vintage aesthetic, retro vibes, film grain, muted tones, nostalgic mood, classic composition'),
                ('Минималистичная эстетика', 'minimalist aesthetic, clean lines, negative space, simple composition, elegant design, modern style'),
                ('Гранж эстетика', 'grunge aesthetic, rough textures, distressed look, urban decay, raw atmosphere, edgy style'),
                ('Романтическая эстетика', 'romantic aesthetic, soft lighting, warm tones, dreamy atmosphere, delicate details, ethereal mood'),
                ('Индустриальная эстетика', 'industrial aesthetic, raw materials, exposed structures, urban setting, gritty atmosphere, modern edge'),
                ('Богемная эстетика', 'bohemian aesthetic, eclectic mix, natural elements, warm colors, artistic vibe, free spirited mood'),
                ('Скандинавская эстетика', 'scandinavian aesthetic, clean design, natural light, neutral tones, minimalist style, cozy atmosphere'),
                ('Тропическая эстетика', 'tropical aesthetic, vibrant colors, lush plants, summer vibes, bright lighting, paradise mood'),
                ('Космическая эстетика', 'space aesthetic, cosmic colors, starry background, nebula effects, ethereal atmosphere, dreamy composition'),
                ('Ретро-футуризм', 'retro futurism aesthetic, vintage sci-fi, bold colors, geometric shapes, nostalgic future, unique style'),
                ('Коттеджкор эстетика', 'cottagecore aesthetic, rural charm, natural elements, warm lighting, cozy atmosphere, pastoral scene'),
                ('Вапорвейв эстетика', 'vaporwave aesthetic, retro computer graphics, pink and cyan, glitch effects, 80s nostalgia, surreal composition'),
            ]
        },
        {
            'name': 'Фэнтези',
            'slug': 'fantasy',
            'description': 'Фантастические и магические миры',
            'order': 5,
            'prompts': [
                ('Магический лес', 'magical forest, glowing mushrooms, fairy lights, mystical atmosphere, enchanted trees, fantasy landscape'),
                ('Драконы', 'majestic dragon, detailed scales, powerful wings, fantasy creature, epic scene, dramatic lighting'),
                ('Замок фэнтези', 'fantasy castle, towering spires, magical aura, dramatic sky, medieval architecture, epic scale'),
                ('Эльфийский город', 'elven city, elegant architecture, natural integration, magical lights, fantasy setting, ethereal beauty'),
                ('Волшебник', 'powerful wizard, flowing robes, magical staff, mystical energy, fantasy character, dramatic pose'),
                ('Мифические существа', 'mythical creature, unique design, fantasy anatomy, magical powers, epic composition, detailed rendering'),
                ('Подземелье', 'fantasy dungeon, torch lighting, ancient ruins, mysterious atmosphere, adventure setting, detailed environment'),
                ('Магический портал', 'magic portal, swirling energy, mystical gateway, glowing runes, fantasy scene, dramatic effect'),
                ('Феи', 'fairy character, delicate wings, magical glow, enchanted forest, whimsical design, fantasy illustration'),
                ('Рыцарь', 'fantasy knight, ornate armor, heroic pose, epic battlefield, dramatic lighting, detailed metalwork'),
                ('Магическое оружие', 'enchanted weapon, glowing runes, mystical energy, detailed craftsmanship, fantasy design, powerful aura'),
                ('Небесный город', 'floating city, clouds below, magical architecture, fantasy setting, epic vista, ethereal atmosphere'),
                ('Темный лорд', 'dark lord, menacing presence, powerful aura, fantasy villain, dramatic composition, ominous atmosphere'),
                ('Магический кристалл', 'magic crystal, glowing energy, mystical properties, fantasy object, detailed rendering, ethereal light'),
                ('Фэнтези битва', 'fantasy battle, epic scale, magical effects, heroic warriors, dramatic action, cinematic composition'),
            ]
        },
    ]
    
    # Создаём категории и промпты
    for cat_data in categories_data:
        prompts_data = cat_data.pop('prompts')
        category = PromptCategory.objects.create(**cat_data)
        
        for order, (title, prompt_text) in enumerate(prompts_data, start=1):
            CategoryPrompt.objects.create(
                category=category,
                title=title,
                prompt_text=prompt_text,
                order=order,
                is_active=True
            )


def reverse_seed(apps, schema_editor):
    PromptCategory = apps.get_model('generate', 'PromptCategory')
    PromptCategory.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('generate', '0011_prompt_categories_with_images'),
    ]

    operations = [
        migrations.RunPython(seed_categories, reverse_seed),
    ]
