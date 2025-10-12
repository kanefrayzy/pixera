from django.db import migrations
from django.utils.text import slugify


def seed_big_suggestions(apps, schema_editor):
    SuggestionCategory = apps.get_model("generate", "SuggestionCategory")
    Suggestion = apps.get_model("generate", "Suggestion")

    # Avoid reseeding if we already have a lot of categories
    if SuggestionCategory.objects.count() >= 50:
        return

    # Helper to keep unique titles and incremental ordering
    order_cat = 1
    order_sg = 1

    def cat_slug(name: str) -> str:
        s = slugify(name or "")[:80]
        return s or slugify("cat")[:80]

    data = [
        # А
        {
            "name": "Аватары и профили",
            "desc": "Аватары для соцсетей и профилей.",
            "items": [
                ("Аватары и профили: Минималистичный аватар",
                 "Create a flat minimalist avatar icon with soft pastel colors, circular frame, simple facial features, vector style, high contrast, clean background, 1:1 aspect ratio, modern UI-friendly."),
                ("Аватары и профили: Реалистичный портрет",
                 "Photorealistic headshot portrait with soft natural lighting, shallow depth of field, neutral background, 85mm lens look, high detail skin texture, professional LinkedIn style, 1:1."),
                ("Аватары и профили: Аниме-аватар",
                 "Anime-style portrait, clean line art, vibrant colors, expressive eyes, subtle cel shading, studio-quality background blur, 1:1 avatar format."),
                ("Аватары и профили: Пиксель-арт",
                 "Pixel-art avatar with 32x32 retro style, crisp pixels, limited color palette, nostalgic game vibe, centered composition, 1:1."),
                ("Аватары и профили: Силуэтный",
                 "High-contrast silhouette avatar with gradient background, minimal details, smooth edges, 1:1 social media profile image."),
            ],
        },
        {
            "name": "Анимации и переходы (UI)",
            "desc": "Микроанимации интерфейсов и переходы.",
            "items": [
                ("Анимации и переходы: Лоадер-спиннер",
                 "Looping animation of a clean circular loader spinner, smooth easing, minimal, white on dark background."),
                ("Анимации и переходы: Параллакс-слои",
                 "Animated parallax layers for a landing page, subtle depth, performance-friendly, SVG/PNG layers."),
                ("Анимации и переходы: Микроанимации кнопок",
                 "Button micro-interactions set, hover, press, success state, smooth cubic-bezier easing, minimal style."),
                ("Анимации и переходы: Skeleton-загрузки",
                 "Skeleton loading placeholders set for cards, text lines, avatar, soft shimmer animation."),
                ("Анимации и переходы: Переходы страниц",
                 "Page transition animations: fade-through, slide, scale, coherent with Material motion guidelines."),
            ],
        },
        {
            "name": "Арт-коллажи и постеры",
            "desc": "Постеры и художественные коллажи.",
            "items": [
                ("Арт-коллажи: Ретро 80-х",
                 "80s retro poster, neon grid, chrome text, synthwave sunset, grainy texture, bold typography, A2 ratio."),
                ("Арт-коллажи: Сюрреализм",
                 "Surreal collage mixing nature and urban elements, dreamy color grading, paper cut-out effect."),
                ("Арт-коллажи: Минимал-геометрия",
                 "Minimal geometric poster, primary colors, strong shapes, Bauhaus inspired, clean layout."),
                ("Арт-коллажи: Гранж-постер",
                 "Grunge poster with distressed textures, torn paper edges, bold contrast, layered typography."),
                ("Арт-коллажи: Абстракт для выставки",
                 "Abstract art poster, fluid shapes, gradient meshes, modern type, gallery announcement layout."),
            ],
        },
        {
            "name": "Астрономия и космос",
            "desc": "Космос, планеты и туманности.",
            "items": [
                ("Космос: Туманность Hubble",
                 "Deep-space nebula with vivid gaseous swirls, star clusters, volumetric clouds, high dynamic range, astrophotography style."),
                ("Космос: Марс крупным планом",
                 "Macro view of Mars surface with red dust, rocky terrain, soft shadows, cinematic lighting, realistic space photography."),
                ("Космос: Корабль у кольцевой",
                 "Sleek sci-fi spaceship near a ringed planet, detailed rings, subsurface scattering, cinematic wide shot, volumetric light."),
                ("Космос: Коллаж галактик",
                 "Collage of spiral galaxies on black background, balanced composition, high contrast, cosmic dust textures."),
                ("Космос: Орбитальная станция",
                 "Isometric illustration of a futuristic orbital station, clean vector style, labeled modules, subtle gradients."),
            ],
        },
        {
            "name": "Архитектура и интерьеры",
            "desc": "Экстерьеры и интерьеры.",
            "items": [
                ("Интерьеры: Современный лофт",
                 "Industrial loft interior with exposed brick, large windows, raw concrete, warm ambient light, photorealistic render."),
                ("Интерьеры: Сканди-минимализм",
                 "Scandinavian minimal interior, white walls, light wood, plants, cozy textiles, soft daylight, wide-angle shot."),
                ("Архитектура: Футуристический небоскреб",
                 "Futuristic skyscraper with organic curves, glass facade, reflections, sunset glow, architectural visualization."),
                ("Интерьеры: Ретро-кафе",
                 "Retro cafe interior, neon accents, checkerboard floor, warm tungsten lights, nostalgic mood."),
                ("Планировка: Квартира",
                 "Clean floor plan, 2D top-down, labeled rooms, neutral palette, architectural drawing, vector lines."),
            ],
        },

        # Б
        {
            "name": "Блоги и контент-маркетинг",
            "desc": "Визуалы для статей и контента.",
            "items": [
                ("Блог: Обложка статьи",
                 "Article cover illustration, relevant metaphor, flat style, vibrant palette, room for title text, 1200x630."),
                ("Блог: Превью соцсетей",
                 "Social media preview image with headline area, brand colors, clean layout, 1200x628."),
                ("Блог: Иллюстрации разделов",
                 "Section header illustrations, iconographic style, cohesive color system, SVG-friendly."),
                ("Блог: Обложка подкаста",
                 "Podcast cover art, bold typography, simple icon, consistent brand palette, 3000x3000."),
                ("Блог: Воронка контента",
                 "Funnel diagram, clean vector arrows, stages labeled, corporate color theme, presentation-ready."),
            ],
        },
        {
            "name": "Брендинг и логотипы",
            "desc": "Знаки, маскоты, монограммы.",
            "items": [
                ("Лого: Монограмма",
                 "Monogram logo with intertwined initials, vector, minimal lines, versatile for dark/light, responsive versions."),
                ("Лого: Геометрический символ",
                 "Abstract geometric symbol logo, scalable, flat colors, brandable, balanced negative space."),
                ("Лого: Маскот",
                 "Mascot logo, friendly character, bold outline, limited color palette, sticker-friendly."),
                ("Лого: Для приложения",
                 "App icon logo, rounded square, simple symbol, high legibility, platform guidelines compliant."),
                ("Лого: Леттеринг",
                 "Custom lettering logo, smooth curves, modern calligraphy, single color, vector."),
            ],
        },

        # В
        {
            "name": "Веб-баннеры и обложки",
            "desc": "Обложки соцсетей, баннеры, hero.",
            "items": [
                ("Баннер: 970x250",
                 "Web banner 970x250, product spotlight, CTA area, high contrast, optimized composition."),
                ("Обложка: YouTube канала",
                 "YouTube channel art, safe area respected, brand pattern background, readable title, 2560x1440."),
                ("Обложка: Twitter/X",
                 "Twitter header, clean gradient, subtle pattern, brand colors, 1500x500."),
                ("Плитка: Карточка товара",
                 "Product tile image, isolated on white, soft shadow, centered composition, e-commerce style."),
                ("Hero: Лендинг",
                 "Hero banner illustration, abstract shapes, brand palette, negative space for headline, 1600x900."),
            ],
        },

        # Г
        {
            "name": "Гейминговые ассеты",
            "desc": "Спрайты, тайлы, UI компонентов игр.",
            "items": [
                ("Игры: Плитка тайлсета",
                 "Seamless game tileset, 32x32 pixel-art, terrain, water, details, retro palette."),
                ("Игры: Спрайт-лист персонажа",
                 "Character sprite sheet with idle/run/jump, clean silhouette, consistent frame size, pixel-art."),
                ("Игры: UI-панели",
                 "Game UI panels, health bars, inventory slots, crisp icons, fantasy theme, vector."),
                ("Игры: Иконки лута",
                 "Loot icons set, weapons, potions, gems, readable at small sizes, outlined style."),
                ("Игры: Фон уровня",
                 "Parallax background for platformer, 3-4 layers, forest theme, soft colors."),
            ],
        },
        {
            "name": "Генерация товаров и мокапов",
            "desc": "Мокапы футболок, упаковок, визиток.",
            "items": [
                ("Мокап: Футболка",
                 "T-shirt mockup, front view, neutral model, soft studio light, high-res fabric texture."),
                ("Мокап: Упаковка",
                 "Packaging box mockup, three-quarter view, subtle shadow, photorealistic, place logo area."),
                ("Мокап: Кружка",
                 "Coffee mug mockup, white ceramic, clean background, natural reflection, logo placement."),
                ("Мокап: Визитка",
                 "Business card mockup, top-down, soft shadows, front and back, premium paper stock."),
                ("Мокап: Постер на стене",
                 "Poster mockup framed on wall, minimal interior, soft daylight, glare controlled."),
            ],
        },
        {
            "name": "Графики и диаграммы (для разработчиков)",
            "desc": "Наборы графиков для дашбордов и презентаций.",
            "items": [
                ("Графики: Линейный с аннотациями",
                 "Clean line chart, labeled axes, annotations for peaks, pastel color scheme, retina-friendly."),
                ("Графики: Столбчатый",
                 "Bar chart, grouped and stacked variants, accessible colors, minimal grid, legend included."),
                ("Графики: Круговая диаграмма",
                 "Pie and donut charts, percentages, subtle gradients, clear labels, presentation-ready."),
                ("Графики: Тепловая карта",
                 "Heatmap with square cells, diverging color scale, tooltip-ready regions."),
                ("Графики: Sankey",
                 "Sankey diagram showing flows between categories, smooth links, balanced spacing."),
            ],
        },

        # Д
        {
            "name": "Дата-арт и инфографика",
            "desc": "Инфографика, карты, схемы.",
            "items": [
                ("Инфографика: Карта мира",
                 "Vector world map with choropleth shading, clean legend, neutral background."),
                ("Инфографика: Временная шкала",
                 "Timeline infographic, milestones nodes, icons per event, horizontal layout, readable labels."),
                ("Инфографика: Пирамида популяции",
                 "Population pyramid chart, male/female bars, central axis, accessible palette."),
                ("Инфографика: Процесс-диаграмма",
                 "Process flow infographic, 5–7 steps, icons, arrows, consistent style."),
                ("Инфографика: Постер статистики",
                 "Statistics poster, large numerals, iconography, modular sections, editorial design."),
            ],
        },
        {
            "name": "Детская иллюстрация",
            "desc": "Детские темы, сказки, азбука.",
            "items": [
                ("Дети: Сказочный лес",
                 "Whimsical children’s illustration of a forest, friendly animals, soft textures, pastel colors."),
                ("Дети: Азбука с картинками",
                 "Alphabet illustration set for kids, each letter with a themed object, flat vector, bright colors."),
                ("Дети: Транспорт",
                 "Cute vehicles set, smiling faces, rounded shapes, toy-like style."),
                ("Дети: Правила безопасности",
                 "Kids safety rules poster, clear icons, simple language areas, positive tone."),
                ("Дети: Иллюстрация для книги",
                 "Full-page children’s book illustration, warm palette, gentle shading, storybook style."),
            ],
        },
        {
            "name": "Для разработчиков: фоны и паттерны",
            "desc": "Градиенты, паттерны, текстуры для UI.",
            "items": [
                ("Фоны: Абстрактный градиент",
                 "Smooth gradient background with subtle noise, modern hues, high-resolution, seamless."),
                ("Фоны: Геометрический SVG",
                 "Seamless geometric SVG pattern, low contrast, UI backdrop, responsive tiling."),
                ("Фоны: Линейные волны",
                 "Flowing line waves pattern, soft curves, calming palette, wallpaper-quality."),
                ("Фоны: Технопаттерн",
                 "Tech pattern with circuits motif, low-opacity lines, dark theme friendly."),
                ("Фоны: Бумажная текстура",
                 "Paper texture background, subtle fiber details, light off-white, scan-like realism."),
            ],
        },
        {
            "name": "Документы и обложки",
            "desc": "Обложки отчётов, сертификаты, брошюры.",
            "items": [
                ("Документы: Обложка отчета",
                 "Corporate report cover, abstract shapes, brand colors, clean typography, A4."),
                ("Документы: Обложка презентации",
                 "Presentation title slide background, gradient mesh, minimal layout, logo area."),
                ("Документы: Титульный лист резюме",
                 "Resume cover page, modern clean layout, name prominent, monochrome accent."),
                ("Документы: Сертификат",
                 "Certificate template, elegant border, serif typography, gold foil effect illusion."),
                ("Документы: Брошюра A5",
                 "A5 brochure cover, photo overlay, geometric mask, grid-based composition."),
            ],
        },

        # Е
        {
            "name": "Еда и напитки",
            "desc": "Предметная съёмка еды, рецепты, этикетки.",
            "items": [
                ("Еда: Бургер-меню",
                 "Gourmet burger photo, soft diffused light, shallow depth, studio black background."),
                ("Еда: Коктейль со льдом",
                 "Cocktail glass with ice and citrus, condensation details, moody bar lighting."),
                ("Еда: Флетлей сервировки",
                 "Flat lay of a brunch table, top-down, rustic props, natural daylight."),
                ("Еда: Иллюстрация рецепта",
                 "Recipe illustration with step icons, ingredients doodles, hand-drawn style."),
                ("Еда: Этикетка продукта",
                 "Product label design mockup, minimal layout, color band system, clean typography."),
            ],
        },
        {
            "name": "Електронная почта и CRM",
            "desc": "Email-баннеры, онбординг и схема автоматизаций.",
            "items": [
                ("Email/CRM: Шаблон рассылки",
                 "Newsletter hero image, modular blocks, brand palette."),
                ("Email/CRM: Баннер акции",
                 "Promo email banner, bold CTA, product highlight."),
                ("Email/CRM: Иллюстрации онбординга",
                 "Onboarding email illustrations, friendly, simple."),
                ("Email/CRM: Карточки сегментов",
                 "CRM segment visuals, color-coded tags, icons."),
                ("Email/CRM: Схема автоматизаций",
                 "Email automation flowchart, triggers and actions, clear."),
            ],
        },

        # Ж
        {
            "name": "Животные и питомцы",
            "desc": "Питомцы, птицы, акварель и пиксель-арт.",
            "items": [
                ("Животные: Реалистичный портрет",
                 "Pet portrait, photorealistic fur, catchlights in eyes, studio light."),
                ("Животные: Акварельные",
                 "Watercolor animal portraits, soft edges, textured paper effect, pastel palette."),
                ("Животные: Пиксель-арт",
                 "Pixel-art animals, 48x48, cute proportions, small color palette."),
                ("Животные: Силуэты птиц",
                 "Bird silhouettes set, various poses, vector, clean edges."),
                ("Животные: Маскот-кошка",
                 "Cat mascot character, chibi style, bold outline, sticker-ready."),
            ],
        },

        # З
        {
            "name": "Заголовки и типографика",
            "desc": "Типографика для постеров и хиро-секций.",
            "items": [
                ("Типографика: Hero-заголовок",
                 "Hero headline typography layout, bold sans, ample whitespace, attention-grabbing."),
                ("Типографика: Кинетическая",
                 "Kinetic typography animation, smooth transitions, readable at speed, high contrast."),
                ("Типографика: Ретро-надпись",
                 "Retro lettering with halftone shading, warm colors, 70s vibe."),
                ("Типографика: Неоновые буквы",
                 "Neon text effect on dark brick wall, glow, realistic reflections."),
                ("Типографика: Гротескный постер",
                 "Grotesk type poster, grid alignment, asymmetric composition, editorial style."),
            ],
        },
        {
            "name": "Здоровье и фитнес",
            "desc": "Плакаты тренировок, трекеры, рецепты ПП.",
            "items": [
                ("Фитнес: Постер тренировок",
                 "Workout routine poster, pictograms for exercises, clean layout, motivating color."),
                ("Фитнес: Прогресс-график",
                 "Fitness progress chart, weight trend line, weekly ticks, celebratory markers."),
                ("Фитнес: ПП-рецепты",
                 "Healthy meal plan grid, macro icons, fresh colors, appetizing photos."),
                ("Фитнес: Трекер сна",
                 "Sleep tracker dashboard card, moon iconography, calm dark palette."),
                ("Фитнес: Иконки упражнений",
                 "Exercise icons set, minimal lines, consistent stroke, vector."),
            ],
        },

        # И
        {
            "name": "Игровые постеры и ключ-арт",
            "desc": "Постеры игр: фэнтези, киберпанк, мобайл.",
            "items": [
                ("Игры: Фэнтези ключ-арт",
                 "Fantasy key art with hero silhouette, epic landscape, dramatic lighting."),
                ("Игры: Киберпанк-постер",
                 "Cyberpunk poster, neon city, rain reflections, chromatic aberration."),
                ("Игры: Ретро-консольное",
                 "Retro console game cover, pixel background, bold title, nostalgic layout."),
                ("Игры: Casual мобайл",
                 "Casual mobile game poster, bright colors, cute characters, simple shapes."),
                ("Игры: Store превью",
                 "Promo image set for app store, feature highlights, clean device frames."),
            ],
        },
        {
            "name": "Иллюстрации для соцсетей",
            "desc": "Карусели, цитаты, мемы и Q&A карточки.",
            "items": [
                ("Соцсети: Карусель карточек",
                 "Carousel post cards, numbered steps, brand colors, uniform grid."),
                ("Соцсети: Цитатная карточка",
                 "Quote cards with large text, subtle background pattern, logo footer."),
                ("Соцсети: Мем-формат",
                 "Meme template, top/bottom text areas, neutral image, bold impact font."),
                ("Соцсети: Вопрос-ответ",
                 "Q&A card style, two-tone layout, high contrast for text."),
                ("Соцсети: Визуал квиза",
                 "Quiz post visuals, multiple choice buttons style, playful."),
            ],
        },
        {
            "name": "Искусство моды",
            "desc": "Лукбуки, скетчи, ткани и плакаты моды.",
            "items": [
                ("Мода: Лукбук кадр",
                 "Lookbook fashion photo, soft studio light, minimal backdrop, editorial."),
                ("Мода: Скетчи одежды",
                 "Fashion sketches, ink line, colored accents, fabric swatches."),
                ("Мода: Паттерн ткани",
                 "Seamless textile pattern, floral/abstract, balanced repeats."),
                ("Мода: Плакат показа",
                 "Fashion show poster, elegant serif, monochrome photo overlay."),
                ("Мода: Аксессуары flat lay",
                 "Accessories flat lay, top-down, crisp shadows, luxury vibe."),
            ],
        },
        {
            "name": "История и ретро",
            "desc": "Винтаж, ретро-техника, старые карты.",
            "items": [
                ("Ретро: Винтажная открытка",
                 "Vintage postcard design, aged paper, stamps, sepia tone."),
                ("Ретро: Конструктивизм",
                 "Constructivist poster, diagonals, bold red/black, geometric shapes."),
                ("Ретро: Техника",
                 "Retro electronics illustration, exploded view, labeled parts."),
                ("Ретро: Старые карты",
                 "Antique map style, parchment texture, ink lines, compass rose."),
                ("Ретро: Плакат пропаганды",
                 "Propaganda poster parody, strong pose, limited palette, grain."),
            ],
        },

        # К
        {
            "name": "Карты и навигация",
            "desc": "Иконки карты, схемы метро, маршруты.",
            "items": [
                ("Карты: Иконки POI",
                 "Map pins and POI icons set, consistent style, vector, legible small."),
                ("Карты: Схема метро",
                 "Subway map diagram, colored lines, stations, high legibility."),
                ("Карты: Туристическая карта",
                 "Tourist map with landmarks illustrations, friendly colors, simplified roads."),
                ("Карты: Навигация маршрута",
                 "Route map with turn-by-turn arrows, clean legend, minimal clutter."),
                ("Карты: 3D местность",
                 "Isometric terrain map, hills and rivers, low-poly style."),
            ],
        },
        {
            "name": "Кинематограф и постеры фильмов",
            "desc": "Постеры жанров: триллер, sci‑fi, ромком.",
            "items": [
                ("Кино: Триллер",
                 "Movie thriller poster, dark mood, dramatic lighting, bold title."),
                ("Кино: Научная фантастика",
                 "Sci-fi poster, cosmic elements, sleek typography, cyan-magenta palette."),
                ("Кино: Романтическая комедия",
                 "Rom-com poster, warm tones, playful composition, smiling leads."),
                ("Кино: Документальный",
                 "Documentary poster, clean layout, striking photo, minimal text."),
                ("Кино: Фестивальный постер",
                 "Film festival poster, abstract shapes, grid layout, multi-logo area."),
            ],
        },
        {
            "name": "Комиксы и манга",
            "desc": "Панели манги, западные комиксы, обложки.",
            "items": [
                ("Комиксы: Панель манги",
                 "Manga panel with dynamic speed lines, screentone shading, expressive faces."),
                ("Комиксы: Западный стиль",
                 "Western comic panel, bold ink, halftone dots, bright colors."),
                ("Комиксы: Обложка выпуска",
                 "Comic issue cover, dramatic pose, logo area, narrative hints."),
                ("Комиксы: Супергеройская сцена",
                 "Superhero action scene, motion blur, glossy highlights."),
                ("Комиксы: Чиби-комикс",
                 "Chibi comic strip, cute proportions, simple backgrounds."),
            ],
        },

        # Л
        {
            "name": "Ландшафты и природа",
            "desc": "Горы, озёра, пустыни, водопады и сияние.",
            "items": [
                ("Пейзажи: Горы на рассвете",
                 "Mountain sunrise, misty valleys, soft orange light, wide panoramic view."),
                ("Пейзажи: Озеро и отражение",
                 "Calm lake reflection, symmetrical composition, cool colors."),
                ("Пейзажи: Пустынные дюны",
                 "Desert dunes, rippled sand, golden hour, minimalistic."),
                ("Пейзажи: Тропический водопад",
                 "Tropical waterfall, lush greenery, high humidity haze."),
                ("Пейзажи: Северное сияние",
                 "Aurora borealis over snowy landscape, starry sky, long exposure look."),
            ],
        },
        {
            "name": "Логотипы: генерация идей (для разработчиков)",
            "desc": "Подбор направлений: техно, эко, финтех, спорт.",
            "items": [
                ("Идеи логотипов: Tech",
                 "Abstract tech logo marks, geometric, negative space, versatile monochrome variants."),
                ("Идеи логотипов: Эко",
                 "Eco brand symbol exploration, leaf motifs, circles, soft greens."),
                ("Идеи логотипов: Финтех",
                 "Fintech logo concepts, trustful blues, shield/graph motifs, clean lines."),
                ("Идеи логотипов: Образование",
                 "Education logo, book/lightbulb metaphors, friendly shapes."),
                ("Идеи логотипов: Спорт",
                 "Sports team logos, dynamic lines, bold outlines, mascot and letterforms."),
            ],
        },

        # М
        {
            "name": "Маркетплейс и карточки товара",
            "desc": "Товарные карты, лайфстайл-фото и бейджи.",
            "items": [
                ("Маркетплейс: Фото на белом",
                 "Product on white background, even lighting, soft shadow, high clarity."),
                ("Маркетплейс: Лайфстайл сцена",
                 "Lifestyle product shot, natural setting, warm tones, aspirational."),
                ("Маркетплейс: Галерея вариаций",
                 "Product variations grid, consistent angles, colorways."),
                ("Маркетплейс: Инфографика фич",
                 "Product features infographic, icons, brief bullets, brand color."),
                ("Маркетплейс: Бейджи скидок",
                 "Sale badges set, vibrant colors, legible at small size."),
            ],
        },
        {
            "name": "Медицина и фарма",
            "desc": "Иконки, инфографика симптомов, аптечные визуалы.",
            "items": [
                ("Медицина: Иконки",
                 "Medical icons set, line style, clear metaphors, vector."),
                ("Медицина: Симптомы",
                 "Symptoms infographic, human silhouette, labeled areas."),
                ("Медицина: Продукт фарма",
                 "Pharma product visual, clean sterile background, trustworthy."),
                ("Медицина: Гигиена",
                 "Hygiene poster, steps with pictograms, blue-white scheme."),
                ("Медицина: Карточка пациента",
                 "Patient card UI mock, clear hierarchy, accessible contrast."),
            ],
        },
        {
            "name": "Мобайл UI",
            "desc": "Компоненты мобильных интерфейсов.",
            "items": [
                ("Мобайл UI: Карточки",
                 "Mobile UI card components set, iOS/Android friendly, spacing system."),
                ("Мобайл UI: Навбар и таббар",
                 "Navigation bar and tab bar variations, icons and labels, safe areas."),
                ("Мобайл UI: Онбординг",
                 "Onboarding screens with illustrations, bold headlines, CTA."),
                ("Мобайл UI: Экран профиля",
                 "Profile screen layout, avatar, stats, actions, clean hierarchy."),
                ("Мобайл UI: Платежи",
                 "Payment screen mock, card form, secure indicators, minimal."),
            ],
        },
        {
            "name": "Музыка и обложки альбомов",
            "desc": "Обложки альбомов разных жанров, лирик-фоны.",
            "items": [
                ("Музыка: EDM обложка",
                 "EDM album cover, neon gradient, abstract shapes, high energy."),
                ("Музыка: Джазовый винил",
                 "Jazz vinyl cover, vintage typography, sepia photo, grain."),
                ("Музыка: Метал-арт",
                 "Metal album art, dark textures, gothic type, high contrast."),
                ("Музыка: Инди-поп",
                 "Indie pop cover, pastel collage, hand-cut feel, playful."),
                ("Музыка: Лирик-видео фон",
                 "Lyric video background loops, soft motion graphics, readable space."),
            ],
        },

        # Н
        {
            "name": "Научная визуализация",
            "desc": "Молекулы, клетки, уравнения и схемы.",
            "items": [
                ("Наука: Молекулярная схема",
                 "Molecular diagram, ball-and-stick, labels, clean vector."),
                ("Наука: Клеточная структура",
                 "Cell illustration, cutaway view, organelles labeled."),
                ("Наука: Солнечная система",
                 "Solar system diagram, orbits, scale indication, vector."),
                ("Наука: Физические графики",
                 "Physics graphs, equations placeholders, axis clarity."),
                ("Наука: Химические уравнения",
                 "Chemical reaction infographic, arrows, conditions noted."),
            ],
        },

        # О
        {
            "name": "Образование и курсы",
            "desc": "Обложки модулей, сертификаты, глоссарии.",
            "items": [
                ("Образование: Плитки модулей",
                 "Course module cover tiles, consistent layout, icon per topic."),
                ("Образование: Сертификат",
                 "Completion certificate template, elegant, logo area."),
                ("Образование: Глоссарий",
                 "Glossary cards, term + short definition, clean design."),
                ("Образование: Дорожная карта",
                 "Learning roadmap infographic, levels, milestones."),
                ("Образование: Мини-иллюстрации",
                 "Section illustrations, simple vectors, school theme."),
            ],
        },
        {
            "name": "Окружение и экология",
            "desc": "Постеры переработки, биоразнообразие, энергия.",
            "items": [
                ("Экология: Переработка",
                 "Recycling poster, green palette, clear steps, iconography."),
                ("Экология: Биоразнообразие",
                 "Biodiversity illustration, layered silhouettes, earthy tones."),
                ("Экология: Чистый воздух",
                 "Air quality infographic, city skyline, pollution index."),
                ("Экология: Вода",
                 "Clean water poster, waves motif, blue gradients, hopeful tone."),
                ("Экология: Возобновляемая энергия",
                 "Renewable energy poster, wind/solar icons, modern."),
            ],
        },

        # П
        {
            "name": "Плакаты мероприятий",
            "desc": "Конференции, концерты, хакатоны, театр.",
            "items": [
                ("События: Конференция IT",
                 "Conference poster, speaker lineup area, QR code placeholder."),
                ("События: Концерт",
                 "Concert poster, bold artist name, dynamic composition."),
                ("События: Хакатон",
                 "Hackathon poster, glitch lines, neon accents, schedule grid."),
                ("События: Ярмарка",
                 "Fair poster, friendly illustrations, family vibe."),
                ("События: Театр",
                 "Theater play poster, dramatic photo, serif type."),
            ],
        },
        {
            "name": "Погода и сезоны",
            "desc": "Иконки погоды, сезонные открытки, климат.",
            "items": [
                ("Погода: Иконки",
                 "Weather icons set, line + filled variants, consistent grid."),
                ("Погода: Сезонные открытки",
                 "Seasonal cards, spring/summer/autumn/winter themes."),
                ("Погода: Пейзаж четырёх сезонов",
                 "Same landscape through four seasons, panel layout."),
                ("Погода: Климат инфографика",
                 "Climate infographic, temp anomalies, trend line."),
                ("Погода: Праздничные заставки",
                 "Holiday greeting banners, tasteful, brand-friendly."),
            ],
        },
        {
            "name": "Портреты и люди",
            "desc": "Портретные стили: студия, стрит, high‑key.",
            "items": [
                ("Портреты: Рембрандт",
                 "Rembrandt lighting portrait, chiaroscuro, warm tones."),
                ("Портреты: Стрит-фото",
                 "Street photography portrait, candid, natural light, grain."),
                ("Портреты: Студийный high-key",
                 "High-key studio portrait, white background, soft light."),
                ("Портреты: Иллюстративный",
                 "Illustrated portrait, vector, flat shading, bold shapes."),
                ("Портреты: Деловой",
                 "Corporate headshot, neutral backdrop, crisp attire."),
            ],
        },
        {
            "name": "Презентации и слайды",
            "desc": "Обложки, разделители, KPI и кейсы.",
            "items": [
                ("Слайды: Обложка",
                 "Keynote slide cover, big title, abstract background, minimal."),
                ("Слайды: Разделитель",
                 "Section divider slide, large numeral, subtle pattern."),
                ("Слайды: Диаграммы",
                 "Slide with charts, clean legend, readable labels."),
                ("Слайды: Кейс",
                 "Case study slide, problem/solution layout, icons."),
                ("Слайды: CTA",
                 "Call-to-action slide, contrasting button, contact area."),
            ],
        },
        {
            "name": "Промо и рекламные креативы",
            "desc": "Перформанс, нативные, ремаркетинг, УТП.",
            "items": [
                ("Реклама: Перформанс баннеры",
                 "Performance ad banners set, strong CTA, product focus."),
                ("Реклама: Нативный креатив",
                 "Native ad creative, editorial style, soft branding."),
                ("Реклама: Ремаркетинг",
                 "Remarketing tiles, personalized product, subtle."),
                ("Реклама: УТП постер",
                 "USP poster, single bold message, minimal."),
                ("Реклама: Отзывы коллаж",
                 "Testimonial collage, portraits + quotes, trust signals."),
            ],
        },
        {
            "name": "Путешествия и туризм",
            "desc": "Постеры направлений, карты туров, билборды.",
            "items": [
                ("Туризм: Плакат направления",
                 "Travel destination poster, landmark illustration, vibrant palette."),
                ("Туризм: Карта экскурсии",
                 "Tour route map, points of interest icons, clean."),
                ("Туризм: Билборд тура",
                 "Tour billboard visual, large photo, clean type."),
                ("Туризм: Обложка гида",
                 "Guidebook cover, collage style, typography overlay."),
                ("Туризм: Карточки отелей",
                 "Hotel listing image set, cozy room, daylight, inviting."),
            ],
        },

        # Р
        {
            "name": "Работа и HR",
            "desc": "Вакансии, культура, офферы и карьерные пути.",
            "items": [
                ("HR: Объявление вакансии",
                 "Job vacancy card, role title big, benefits icons."),
                ("HR: Культура компании",
                 "Company culture visuals, team photos stylized, friendly."),
                ("HR: Презентация оффера",
                 "Offer slide, compensation highlights, clean layout."),
                ("HR: Диаграмма карьеры",
                 "Career path diagram, ladder metaphor, modern."),
                ("HR: Мотивирующие постеры",
                 "Motivational office posters, minimal, typographic."),
            ],
        },
        {
            "name": "Разработка: UI-компоненты",
            "desc": "Карточки, формы, таблицы, модали и меню.",
            "items": [
                ("UI-компоненты: Карточки/листы",
                 "UI cards and list components, light/dark variants, consistent spacing system."),
                ("UI-компоненты: Формы и валидации",
                 "Form UI with inputs, dropdowns, error states, accessibility focus."),
                ("UI-компоненты: Таблицы данных",
                 "Data table components, zebra rows, filters, pagination."),
                ("UI-компоненты: Модали и тосты",
                 "Modal dialogs and toast notifications, overlay styles, motion."),
                ("UI-компоненты: Навигация",
                 "Nav components, sidebars, breadcrumbs, tabs, responsive."),
            ],
        },
        {
            "name": "Разработка: иллюстрации для 404/500",
            "desc": "Иллюстрации ошибок, пустых состояний и заглушек.",
            "items": [
                ("Иллюстрации: 404 с персонажем",
                 "Cute 404 error illustration, lost character, soft colors, friendly."),
                ("Иллюстрации: 500 технический",
                 "500 error tech illustration, broken robot, subtle humor."),
                ("Иллюстрации: 403 доступ",
                 "403 access denied, shield/lock metaphor, minimal."),
                ("Иллюстрации: Пустые состояния",
                 "Empty state illustrations, clean vectors, positive tone."),
                ("Иллюстрации: Заглушки",
                 "Placeholder illustrations for coming soon, under construction."),
            ],
        },

        # С
        {
            "name": "Свадьбы и праздники",
            "desc": "Приглашения, рассадки, открытки, юбилеи.",
            "items": [
                ("Праздники: Свадебное приглашение",
                 "Wedding invite card, floral border, elegant script type."),
                ("Праздники: План рассадки",
                 "Seating plan board, neat layout, name cards style."),
                ("Праздники: Открытки",
                 "Holiday greeting cards set, tasteful, classic motifs."),
                ("Праздники: Детский день рождения",
                 "Birthday party poster for kids, balloons, bright."),
                ("Праздники: Юбилей",
                 "Anniversary poster, gold accents, refined typography."),
            ],
        },
        {
            "name": "Спорт и активити",
            "desc": "Афиши, правила, планы тренировок, экипировка.",
            "items": [
                ("Спорт: Афиша соревнований",
                 "Sports tournament poster, dynamic composition, team logos."),
                ("Спорт: Правила инфографика",
                 "Rules infographic, icons for fouls/scoring, clear."),
                ("Спорт: План тренировок",
                 "Training schedule board, week grid, icons."),
                ("Спорт: Плакат болельщика",
                 "Fan poster, bold colors, mascot, chant area."),
                ("Спорт: Экипировка обзор",
                 "Gear display graphic, labeled parts, clean."),
            ],
        },

        # Т
        {
            "name": "Технологии и стартапы",
            "desc": "Питч-обложки, архитектуры, флоучарты, лендинги.",
            "items": [
                ("Стартап: Питч-обложка",
                 "Pitch deck cover, gradient mesh, sleek branding."),
                ("Стартап: Архитектура системы",
                 "System architecture diagram, microservices boxes, arrows."),
                ("Стартап: Флоучарт процессов",
                 "Flowchart diagram, swimlanes, clean connectors."),
                ("Стартап: Лэндинг",
                 "Startup landing hero, product mock, value props."),
                ("Стартап: Анонс релиза",
                 "Release announcement card, version badge, highlights."),
            ],
        },

        # У
        {
            "name": "Упаковка и этикетки",
            "desc": "Напитки, косметика, наклейки, бирки, эко-упаковка.",
            "items": [
                ("Упаковка: Этикетка напитка",
                 "Beverage label design, curved, bold brand mark."),
                ("Упаковка: Коробка косметики",
                 "Cosmetics box, foil accents, minimal type."),
                ("Упаковка: Наклейки",
                 "Sticker sheet, die-cut outlines, playful icons."),
                ("Упаковка: Бирка одежды",
                 "Clothing hang tag, textured paper, simple logo."),
                ("Упаковка: Эко-концепт",
                 "Eco packaging concept, kraft paper, green accents."),
            ],
        },

        # Ф
        {
            "name": "Фоновые изображения для сайтов",
            "desc": "Градиенты, блобы, mesh, low‑poly, lifestyle.",
            "items": [
                ("Фоны сайта: Мягкий градиент",
                 "Soft gradient wallpaper, low-noise texture, large resolution."),
                ("Фоны сайта: Абстрактные пятна",
                 "Abstract blobs background, pastel colors, smooth edges."),
                ("Фоны сайта: Сетчатые градиенты",
                 "Mesh gradient background, organic transitions, subtle."),
                ("Фоны сайта: Низкополи фон",
                 "Low-poly abstract background, geometric facets."),
                ("Фоны сайта: Фотофон лайфстайл",
                 "Lifestyle photo background, blurred, warm tones, content-safe."),
            ],
        },
        {
            "name": "Фото: предметная съемка",
            "desc": "Изолят, акрил, softbox, макро и ракурсы.",
            "items": [
                ("Предметка: Изолят на белом",
                 "Product isolated on pure white, shadow, crisp edges."),
                ("Предметка: Черный акрил",
                 "Product on glossy black acrylic, reflection, moody."),
                ("Предметка: Softbox-съемка",
                 "Softbox lighting setup look, diffused highlights, no harsh shadows."),
                ("Предметка: Макро-текстуры",
                 "Macro texture shots, fabric/wood/stone, sharp details."),
                ("Предметка: Набор ракурсов",
                 "Multi-angle product set, consistent lighting and distance."),
            ],
        },
        {
            "name": "Фото: портрет и мода",
            "desc": "Стрит, beauty студия, каталог, ЧБ, движение.",
            "items": [
                ("Фото-портрет: Стрит-лук",
                 "Street fashion portrait, candid pose, urban background."),
                ("Фото-портрет: Beauty студия",
                 "Beauty studio portrait, high-end retouch, glossy skin."),
                ("Фото-портрет: Каталог одежды",
                 "Lookbook catalog shot, neutral backdrop, full body."),
                ("Фото-портрет: Черно-белый",
                 "Black and white portrait, strong contrast, film grain."),
                ("Фото-портрет: Динамика движения",
                 "Motion blur fashion shot, flowing fabric, dramatic light."),
            ],
        },

        # Х
        {
            "name": "Хозяйство и интерьер-декор",
            "desc": "Мудборды, постеры, картины, календари, этикетки.",
            "items": [
                ("Дом: Moodboard комнаты",
                 "Room moodboard, color swatches, materials, furniture icons."),
                ("Дом: Постер правил дома",
                 "Home rules poster, friendly icons, playful type."),
                ("Дом: Картина для гостиной",
                 "Living room wall art, abstract, calming palette."),
                ("Дом: Календарь-планер",
                 "Wall calendar planner, monthly grid, notes area."),
                ("Дом: Этикетки для хранения",
                 "Storage labels, clean typography, icon system."),
            ],
        },

        # Ц
        {
            "name": "Цифровое искусство и концепт-арт",
            "desc": "Концепты персонажей и окружения, матпейнтинг.",
            "items": [
                ("Концепт-арт: Персонаж",
                 "Character concept sheet, front/side, costume details."),
                ("Концепт-арт: Окружение",
                 "Environment concept, key lighting, mood boards."),
                ("Концепт-арт: Матпейнтинг",
                 "Matte painting landscape, epic scale, realistic."),
                ("Концепт-арт: Обложка игры",
                 "Game cover concept, hero focus, cinematic."),
                ("Концепт-арт: Brushpack превью",
                 "Brush pack preview graphics, strokes display, clear labels."),
            ],
        },
        {
            "name": "Чарт-дизайн для дашбордов",
            "desc": "KPI карточки, составные графики, гео-аналитика.",
            "items": [
                ("Дашборд: KPI карточки",
                 "Dashboard KPI cards, concise numbers, trend arrows."),
                ("Дашборд: Композитные графики",
                 "Composite charts, dual-axis, clean legend, balanced."),
                ("Дашборд: Гео-аналитика",
                 "Geo analytics map choropleth, tooltips, neutral palette."),
                ("Дашборд: Таблица показателей",
                 "Metrics table, sticky headers, zebra rows, icons."),
                ("Дашборд: Сигнальные индикаторы",
                 "Status indicators set: success/warn/error/info, subtle."),
            ],
        },

        # Э
        {
            "name": "Электроника и устройства",
            "desc": "3D-рендеры устройств, аксессуары, линейки.",
            "items": [
                ("Гаджеты: Рендер смартфона",
                 "Smartphone 3D render, floating, soft shadow, glossy."),
                ("Гаджеты: Лаптоп на столе",
                 "Laptop on desk, natural light, productivity vibe."),
                ("Гаджеты: Гарнитура",
                 "Headphones product shot, matte black, minimal scene."),
                ("Гаджеты: Умные часы",
                 "Smartwatch render, app screen visible, reflections."),
                ("Гаджеты: Сет устройств",
                 "Device set lineup, consistent perspective, labels."),
            ],
        },

        # Ю
        {
            "name": "Юмор и мемы",
            "desc": "Мем-шаблоны, реакционные стикеры, панчи.",
            "items": [
                ("Юмор: Шаблоны мемов",
                 "Meme templates, safe layout, bold top/bottom text areas."),
                ("Юмор: Реакции-стикеры",
                 "Reaction stickers set, expressive characters, outline."),
                ("Юмор: Ироничные постеры",
                 "Ironic posters, typographic jokes, minimal composition."),
                ("Юмор: Гифки-лупы",
                 "Looping GIF motifs, playful motion, simple shapes."),
                ("Юмор: Комикс-панчи",
                 "One-panel comic jokes, high-contrast, bold captions."),
            ],
        },

        # Я
        {
            "name": "3D и изометрия",
            "desc": "Изометрические иконки, low‑poly, 3D-логотипы.",
            "items": [
                ("3D/Изометрия: Иконки",
                 "Isometric icon set, soft shadows, pastel palette."),
                ("3D/Изометрия: Лоу-поли сцена",
                 "Low-poly scene, clean lighting, geometric."),
                ("3D/Изометрия: 3D логотип",
                 "3D logo extrude, metallic material, studio light."),
                ("3D/Изометрия: Изометрический офис",
                 "Isometric office environment, desks, plants, devices."),
                ("3D/Изометрия: 3D график",
                 "3D bar and pie chart renders, glossy, presentation."),
            ],
        },
        {
            "name": "UI/UX исследования",
            "desc": "Персоны, CJM, карты сайта, юзабилити-отчёты, вайрфреймы.",
            "items": [
                ("UX: Персонажи (Personas)",
                 "User persona cards, photo placeholders, goals/pain points."),
                ("UX: CJM карта",
                 "Customer journey map, stages columns, touchpoints."),
                ("UX: Карта сайта",
                 "Sitemap diagram, hierarchy tree, clean connectors."),
                ("UX: Юзабилити находки",
                 "Usability findings report visuals, severity tags."),
                ("UX: Вайрфреймы",
                 "Wireframe screens, grayscale blocks, annotations."),
            ],
        },
        {
            "name": "Интернет-магазин (витрина)",
            "desc": "Hero офферы, категории, преимущества, отзывы и бренды.",
            "items": [
                ("E‑commerce: Hero офферы",
                 "E-commerce hero banner, seasonal offers, product collage."),
                ("E‑commerce: Сетки категорий",
                 "Category tiles grid, icons/photos, clean labels."),
                ("E‑commerce: Плашки преимуществ",
                 "Benefit badges: free shipping, returns, support."),
                ("E‑commerce: Карточки отзывов",
                 "Review cards, stars, portrait, highlighted quotes."),
                ("E‑commerce: Секция брендов",
                 "Brand logos strip, monochrome, balanced spacing."),
            ],
        },
        {
            "name": "Видео и motion дизайн",
            "desc": "Фоны для интро, lower-thirds, титры, лупы.",
            "items": [
                ("Motion: Интро-фон",
                 "Abstract motion background loop, subtle particles, depth, low-contrast palette."),
                ("Motion: Lower-thirds",
                 "Lower-third graphics set, clean bars, safe margins, broadcast-ready."),
                ("Motion: Титры",
                 "End credits template visuals, scrolling layout, legible typography."),
                ("Motion: Трансitions",
                 "Pack of transitions frames, wipes and morphs, smooth easing."),
                ("Motion: Луп паттерны",
                 "Loopable pattern animations, seamless, minimal shapes."),
            ],
        },
    ]

    # Insert categories and suggestions
    for block in data:
        name = block["name"].strip()
        slug = cat_slug(name)
        desc = block.get("desc", "")[:200]
        # 1) Try to find by name (unique in model)
        cat = SuggestionCategory.objects.filter(name=name).first()

        # 2) If not found by name — try find by computed slug (to reuse existing)
        if not cat:
            cat = SuggestionCategory.objects.filter(slug=slug).first()

        # 3) If still not found — ensure unique slug, then create
        if not cat:
            base_slug = slug or slugify("cat")
            s = base_slug
            i = 2
            while SuggestionCategory.objects.filter(slug=s).exists():
                s = f"{base_slug}-{i}"
                i += 1
            cat = SuggestionCategory.objects.create(
                name=name,
                slug=s,
                description=desc,
                order=order_cat,
                is_active=True,
            )
        else:
            # Update minimal fields on existing without breaking unique constraints
            updated = False
            if desc and getattr(cat, "description", "") != desc:
                cat.description = desc
                updated = True
            if getattr(cat, "order", 0) == 0:
                cat.order = order_cat
                updated = True
            if not cat.is_active:
                cat.is_active = True
                updated = True
            if updated:
                cat.save()

        order_cat += 1

        for title, text in block.get("items", []):
            title_ru = title.strip()
            # Safety: max length 80 for title
            if len(title_ru) > 80:
                title_ru = title_ru[:77] + "…"
            s, _ = Suggestion.objects.get_or_create(
                title=title_ru,
                defaults={
                    "category_id": cat.id,
                    "text": text.strip(),
                    "order": order_sg,
                    "is_active": True,
                },
            )
            # If existed, ensure category and text updated
            updated = False
            if s.category_id != cat.id:
                s.category_id = cat.id
                updated = True
            if text.strip() and s.text != text.strip():
                s.text = text.strip()
                updated = True
            if s.order == 0:
                s.order = order_sg
                updated = True
            if not s.is_active:
                s.is_active = True
                updated = True
            if updated:
                s.save()
            order_sg += 1


def unseed_big_suggestions(apps, schema_editor):
    SuggestionCategory = apps.get_model("generate", "SuggestionCategory")
    # Only remove categories created by this seeder by matching known prefixes in names
    prefixes = [
        "Аватары и профили", "Анимации и переходы (UI)", "Арт-коллажи и постеры", "Астрономия и космос",
        "Архитектура и интерьеры", "Блоги и контент-маркетинг", "Брендинг и логотипы",
        "Веб-баннеры и обложки", "Гейминговые ассеты", "Генерация товаров и мокапов",
        "Графики и диаграммы (для разработчиков)", "Дата-арт и инфографика", "Детская иллюстрация",
        "Для разработчиков: фоны и паттерны", "Документы и обложки", "Еда и напитки",
        "Електронная почта и CRM", "Животные и питомцы", "Заголовки и типографика",
        "Здоровье и фитнес", "Игровые постеры и ключ-арт", "Иллюстрации для соцсетей",
        "Искусство моды", "История и ретро", "Карты и навигация",
        "Кинематограф и постеры фильмов", "Комиксы и манга", "Ландшафты и природа",
        "Логотипы: генерация идей (для разработчиков)", "Маркетплейс и карточки товара",
        "Медицина и фарма", "Мобайл UI", "Музыка и обложки альбомов", "Научная визуализация",
        "Образование и курсы", "Окружение и экология", "Плакаты мероприятий", "Погода и сезоны",
        "Портреты и люди", "Презентации и слайды", "Промо и рекламные креативы", "Путешествия и туризм",
        "Работа и HR", "Разработка: UI-компоненты", "Разработка: иллюстрации для 404/500",
        "Свадьбы и праздники", "Спорт и активити", "Технологии и стартапы", "Упаковка и этикетки",
        "Фоновые изображения для сайтов", "Фото: предметная съемка", "Фото: портрет и мода",
        "Хозяйство и интерьер-декор", "Цифровое искусство и концепт-арт", "Чарт-дизайн для дашбордов",
        "Электроника и устройства", "Юмор и мемы", "3D и изометрия", "UI/UX исследования",
        "Интернет-магазин (витрина)", "Видео и motion дизайн",
    ]
    SuggestionCategory.objects.filter(name__in=prefixes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("generate", "0013_showcaseadditionalimage"),
    ]

    operations = [
        migrations.RunPython(seed_big_suggestions, unseed_big_suggestions),
    ]
