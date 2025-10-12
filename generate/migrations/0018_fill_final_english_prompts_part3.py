# Generated migration for filling final professional English prompts - Part 3

from django.db import migrations


def fill_english_prompts_part3(apps, schema_editor):
    """Заполняет финальные поля prompt_en профессиональными английскими промптами"""
    CategoryPrompt = apps.get_model('generate', 'CategoryPrompt')
    
    # Словарь: русский текст -> профессиональный английский промпт
    prompts_mapping = {
        # Свет и тень
        "Солнечные лучи сквозь деревья, свет, тени": "Sunlight rays through trees, light beams, dramatic shadows, forest atmosphere, professional landscape photography, god rays, natural lighting, atmospheric beauty, golden hour, 8K ultra detailed",
        "Силуэт на закате, контраст, драматизм": "Silhouette at sunset, high contrast, dramatic composition, backlit figure, professional photography, golden hour, striking visual, powerful imagery, cinematic mood, artistic expression",
        "Свет и тень в архитектуре, геометрия": "Architectural light and shadow, geometric patterns, structural contrast, professional photography, modern design, dramatic angles, clean lines, contemporary aesthetic, visual rhythm",
        "Свеча в темноте, мягкий свет, уют": "Candle in darkness, soft warm glow, cozy atmosphere, intimate lighting, professional photography, gentle illumination, peaceful mood, romantic ambiance, flickering flame",
        "Неоновый свет, яркость, ночь, город": "Neon lights, vibrant glow, night city, urban atmosphere, professional photography, electric colors, modern signage, cyberpunk aesthetic, glowing brilliance, 8K detailed",
        "Лунный свет, ночь, романтика, тайна": "Moonlight, nocturnal romance, mysterious atmosphere, lunar glow, professional photography, silvery illumination, dreamy mood, peaceful night, ethereal beauty",
        "Студийное освещение, портрет, профессионализм": "Studio lighting setup, professional portrait, controlled illumination, key light and fill, photography excellence, perfect exposure, commercial quality, technical precision, flawless lighting",
        "Контровой свет, силуэт, драма": "Backlight silhouette, dramatic contrast, rim lighting, professional photography, striking composition, powerful visual, artistic expression, bold imagery, cinematic effect",
        "Рассеянный свет, мягкость, нежность": "Diffused soft light, gentle illumination, tender atmosphere, professional photography, even lighting, delicate mood, peaceful ambiance, natural softness, flattering glow",
        "Тени на стене, узоры, игра света": "Shadows on wall, pattern play, light interaction, professional photography, geometric shapes, artistic composition, natural design, visual rhythm, abstract beauty",
        "Золотой час, теплый свет, магия": "Golden hour lighting, warm glow, magical atmosphere, sunset/sunrise, professional photography, perfect illumination, romantic mood, natural beauty, photographer's dream, 8K detailed",
        "Синий час, сумерки, спокойствие": "Blue hour twilight, peaceful atmosphere, dusk lighting, professional photography, cool tones, serene mood, transitional time, atmospheric beauty, calm environment",
        "Световые блики, отражения, яркость": "Light flares, lens reflections, bright highlights, professional photography, sparkling effects, luminous beauty, glowing accents, radiant atmosphere, brilliant illumination",
        "Тень от жалюзи, полосы, графика": "Venetian blind shadows, striped pattern, graphic composition, professional photography, geometric lines, light and dark, modern aesthetic, architectural detail, visual rhythm",
        "Свет в тумане, мистика, атмосфера": "Light through fog, mystical atmosphere, ethereal glow, professional photography, atmospheric haze, mysterious mood, soft diffusion, dreamy environment, magical ambiance",
        
        # Спорт (продолжение)
        "Футболист забивает гол, динамика, стадион": "Soccer player scoring goal, dynamic action, stadium atmosphere, professional sports photography, athletic achievement, crowd excitement, decisive moment, competitive spirit, 8K ultra detailed",
        "Баскетболист в прыжке, данк, энергия": "Basketball player dunking, aerial jump, explosive energy, professional sports photography, athletic power, slam dunk, competitive moment, arena lighting, dynamic action",
        "Бегун на финише, скорость, усилие": "Runner crossing finish line, maximum speed, intense effort, professional sports photography, athletic determination, competitive race, victory moment, physical exertion, inspiring achievement",
        "Пловец под водой, техника, грация": "Swimmer underwater, perfect technique, graceful movement, professional sports photography, athletic form, pool competition, streamlined motion, aquatic grace, competitive swimming",
        "Теннисист подает мяч, концентрация": "Tennis player serving, focused concentration, powerful serve, professional sports photography, athletic precision, court action, competitive moment, technical excellence, dynamic motion",
        "Гимнастка на бревне, баланс, элегантность": "Gymnast on balance beam, perfect equilibrium, elegant performance, professional sports photography, athletic artistry, competitive routine, graceful poise, Olympic quality, precise control",
        "Боксер на ринге, удар, мощь": "Boxer in ring, powerful punch, intense combat, professional sports photography, athletic strength, competitive match, fighting spirit, dramatic lighting, action moment",
        "Велогонщик на трассе, скорость, драйв": "Cyclist racing, high speed, competitive drive, professional sports photography, athletic determination, road race, dynamic motion, team strategy, intense competition",
        "Серфер на волне, океан, адреналин": "Surfer riding wave, ocean power, adrenaline rush, professional action photography, athletic skill, perfect balance, coastal sport, dynamic moment, extreme conditions",
        "Скалолаз на вершине, достижение, высота": "Rock climber on summit, peak achievement, extreme height, professional action photography, athletic accomplishment, mountain conquest, triumphant moment, outdoor adventure, inspiring success",
        "Лыжник на склоне, снег, скорость": "Skier on slope, powder snow, high speed descent, professional sports photography, winter sport, athletic skill, mountain landscape, dynamic action, competitive racing",
        "Йога на рассвете, гармония, природа": "Sunrise yoga practice, natural harmony, peaceful pose, professional photography, spiritual wellness, outdoor meditation, golden hour light, mindful exercise, zen atmosphere",
        "Фигурное катание, прыжок, красота": "Figure skating jump, graceful beauty, ice performance, professional sports photography, athletic artistry, competitive routine, elegant movement, Olympic quality, perfect form",
        "Гольфист на поле, точность, концентрация": "Golfer on course, precise swing, focused concentration, professional sports photography, athletic precision, perfect form, competitive moment, strategic play, outdoor sport",
        "Марафонец, выносливость, целеустремленность": "Marathon runner, endurance athlete, determined spirit, professional sports photography, long distance, physical challenge, competitive race, inspiring perseverance, athletic dedication",
        
        # Текстуры
        "Дерево, текстура, годовые кольца, природа": "Wood texture, tree rings, natural grain, organic pattern, professional macro photography, aged surface, growth history, earthy tones, detailed close-up, rustic beauty",
        "Камень, шероховатость, прочность, древность": "Stone texture, rough surface, solid strength, ancient material, professional photography, weathered rock, geological beauty, natural durability, tactile quality, timeless substance",
        "Ткань, складки, мягкость, текстиль": "Fabric texture, soft folds, textile draping, material close-up, professional photography, woven pattern, gentle touch, flowing cloth, detailed surface, tactile beauty",
        "Металл, блеск, холод, прочность": "Metal texture, polished shine, cold surface, industrial strength, professional photography, reflective finish, modern material, sleek appearance, durable substance, contemporary aesthetic",
        "Стекло, прозрачность, отражения, хрупкость": "Glass texture, transparent clarity, surface reflections, delicate fragility, professional photography, smooth finish, light refraction, modern material, pristine surface, elegant simplicity",
        "Кожа, текстура, натуральность, качество": "Leather texture, natural grain, premium quality, organic material, professional photography, tactile surface, aged patina, luxury material, detailed close-up, authentic beauty",
        "Бумага, волокна, матовость, письмо": "Paper texture, fiber details, matte surface, writing material, professional macro photography, organic composition, subtle texture, natural finish, detailed close-up, tactile quality",
        "Песок, зернистость, пляж, пустыня": "Sand texture, granular surface, beach or desert, natural particles, professional macro photography, varied grains, earthy tones, detailed close-up, geological beauty, natural pattern",
        "Вода, капли, отражения, текучесть": "Water texture, liquid droplets, surface reflections, fluid nature, professional photography, transparent beauty, flowing movement, natural element, pristine clarity, dynamic surface",
        "Лед, кристаллы, холод, прозрачность": "Ice texture, crystal formation, frozen surface, transparent cold, professional photography, winter beauty, geometric patterns, natural structure, pristine clarity, delicate details",
        "Мрамор, прожилки, роскошь, камень": "Marble texture, natural veining, luxury stone, elegant surface, professional photography, premium material, sophisticated pattern, timeless beauty, polished finish, architectural quality",
        "Бетон, шероховатость, современность": "Concrete texture, rough surface, modern material, industrial aesthetic, professional photography, urban finish, contemporary design, raw beauty, architectural element, minimalist appeal",
        "Мех, мягкость, тепло, уют": "Fur texture, soft touch, warm comfort, cozy material, professional photography, luxurious feel, natural insulation, tactile pleasure, gentle surface, inviting warmth",
        "Керамика, глазурь, гладкость, искусство": "Ceramic texture, glazed finish, smooth surface, artistic pottery, professional photography, handcrafted quality, elegant sheen, traditional craft, refined beauty, cultural artistry",
        "Ржавчина, старение, время, металл": "Rust texture, oxidation pattern, aged metal, time's passage, professional photography, weathered surface, orange-brown tones, natural decay, industrial beauty, vintage character",
        
        # Технологии (продолжение)
        "Робот-гуманоид, искусственный интеллект, будущее": "Humanoid robot, artificial intelligence, futuristic android, sci-fi character, professional photography, advanced AI, metallic surfaces, glowing elements, photorealistic rendering, technological marvel",
        "Голограмма, 3D проекция, футуристика": "Holographic projection, 3D display, futuristic technology, floating image, professional photography, sci-fi interface, blue glow, advanced visualization, modern innovation, digital illusion",
        "Дрон в полете, аэросъемка, технологии": "Drone flying, aerial photography, modern technology, quadcopter in air, professional photography, remote control, innovative device, sky perspective, technical precision, contemporary gadget",
        "Умные часы, носимая электроника, дизайн": "Smartwatch, wearable technology, modern design, fitness tracker, professional product photography, sleek aesthetics, digital display, contemporary lifestyle, health monitoring, innovative device",
        "Виртуальная реальность, VR очки, погружение": "Virtual reality headset, VR immersion, digital world, gaming technology, professional product photography, futuristic device, immersive experience, modern entertainment, cutting-edge tech, 3D environment",
        "3D принтер в работе, создание объекта": "3D printer working, object creation, additive manufacturing, modern technology, professional photography, layer by layer, innovative production, digital fabrication, creative possibilities, future of making",
        "Квадрокоптер, съемка с воздуха, инновации": "Quadcopter drone, aerial filming, innovative technology, flying camera, professional photography, remote piloting, bird's eye view, modern device, technical precision, contemporary innovation",
        "Смартфон последнего поколения, экран, интерфейс": "Latest smartphone, touchscreen display, modern interface, cutting-edge device, professional product photography, sleek design, premium materials, contemporary technology, user experience, innovative features",
        "Беспроводные наушники, звук, технологии": "Wireless headphones, audio technology, modern sound, Bluetooth device, professional product photography, premium quality, sleek design, contemporary lifestyle, noise cancellation, innovative audio",
        "Электронная плата, микросхемы, детали": "Circuit board, microchips, electronic components, technical details, professional macro photography, green PCB, soldered connections, modern technology, intricate design, digital hardware",
        "Лазерная установка, свет, точность": "Laser equipment, light beam, precision technology, scientific instrument, professional photography, focused energy, modern innovation, technical accuracy, industrial application, cutting-edge device",
        "Солнечные панели, возобновляемая энергия": "Solar panels, renewable energy, sustainable technology, photovoltaic cells, professional photography, clean power, environmental innovation, modern infrastructure, green technology, future energy",
        "Биометрический сканер, безопасность": "Biometric scanner, security technology, fingerprint reader, modern authentication, professional photography, digital identity, access control, innovative protection, futuristic security, personal verification",
        "Нейроинтерфейс, связь мозг-компьютер": "Neural interface, brain-computer connection, futuristic technology, mind control, professional concept art, sci-fi innovation, cognitive link, advanced neuroscience, thought communication, revolutionary device",
        "Автономный автомобиль, самоуправление, датчики": "Autonomous vehicle, self-driving car, sensor array, futuristic transportation, professional photography, AI navigation, modern automotive, innovative technology, smart mobility, future of driving",
        
        # Транспорт
        "Спортивный автомобиль, красный цвет, скорость": "Sports car, red color, high speed, luxury automobile, professional automotive photography, sleek design, powerful engine, dynamic motion, premium vehicle, 8K ultra detailed, racing aesthetic",
        "Винтажный автомобиль, ретро стиль, классика": "Vintage classic car, retro styling, automotive heritage, pristine restoration, professional car photography, chrome details, nostalgic beauty, timeless design, collector's dream, golden era",
        "Мотоцикл на шоссе, закат, свобода": "Motorcycle on highway, sunset ride, freedom feeling, open road, professional photography, biker lifestyle, golden hour, wind in face, adventure spirit, scenic journey",
        "Частный самолет, роскошь, взлетная полоса": "Private jet, luxury aviation, runway ready, executive travel, professional photography, premium aircraft, sleek design, business class, modern convenience, elite transportation",
        "Яхта в море, белые паруса, голубая вода": "Sailing yacht, white sails, blue ocean, luxury vessel, professional photography, maritime elegance, coastal beauty, nautical lifestyle, peaceful sailing, pristine waters",
        "Поезд в горах, живописный маршрут": "Mountain train, scenic railway, picturesque route, alpine journey, professional photography, rail travel, dramatic landscape, engineering marvel, tourist attraction, beautiful vista",
        "Электромобиль, футуристичный дизайн, экология": "Electric vehicle, futuristic design, eco-friendly, sustainable transportation, professional photography, modern automotive, clean energy, innovative engineering, environmental consciousness, sleek aesthetics",
        "Вертолет над городом, высота, панорама": "Helicopter over city, aerial height, panoramic view, urban flight, professional photography, bird's eye perspective, modern aviation, cityscape below, dynamic angle, impressive vista",
        "Велосипед в парке, активный отдых, природа": "Bicycle in park, active recreation, nature setting, outdoor activity, professional photography, healthy lifestyle, peaceful environment, eco-friendly transport, leisure time, green space",
        "Грузовик на трассе, дальнобойщик, дорога": "Truck on highway, long-haul driver, open road, commercial transport, professional photography, freight delivery, working vehicle, journey ahead, industrial strength, modern logistics",
        "Трамвай в старом городе, европейская атмосфера": "Tram in old town, European atmosphere, vintage transport, historic streets, professional photography, urban charm, public transit, cultural heritage, nostalgic scene, city character",
        "Космический корабль, футуристика, звезды": "Spaceship, futuristic design, star field, sci-fi vessel, professional concept art, interstellar travel, advanced technology, cosmic journey, sleek spacecraft, space exploration",
        "Подводная лодка, глубина, исследование": "Submarine, ocean depths, underwater exploration, naval vessel, professional photography, deep sea, marine technology, submerged journey, pressure hull, aquatic adventure",
        "Дирижабль в небе, стимпанк, облака": "Airship in sky, steampunk aesthetic, cloud backdrop, vintage aviation, professional photography, retro-futuristic, floating vessel, Victorian technology, romantic flight, alternative history",
        "Гоночный болид, Формула-1, трек": "Formula 1 race car, high-speed track, racing circuit, professional motorsport photography, aerodynamic design, competitive racing, extreme performance, technical precision, championship vehicle",
        
        # Уют
        "Камин, огонь, тепло, уют, зима": "Fireplace, crackling fire, warm comfort, cozy winter, professional interior photography, glowing flames, peaceful atmosphere, home warmth, inviting ambiance, seasonal comfort",
        "Чашка кофе и книга, утро, спокойствие": "Coffee cup and book, peaceful morning, calm atmosphere, cozy reading, professional lifestyle photography, warm beverage, quiet moment, relaxing ritual, comfortable setting, gentle start",
        "Плед и подушки, диван, комфорт, отдых": "Blanket and pillows, cozy sofa, comfortable rest, relaxation space, professional interior photography, soft textiles, inviting comfort, peaceful atmosphere, home sanctuary, warm embrace",
        "Свечи в интерьере, мягкий свет, атмосфера": "Interior candles, soft glow, atmospheric lighting, cozy ambiance, professional photography, warm illumination, peaceful mood, romantic setting, gentle light, inviting space",
        "Кот на подоконнике, уют, дом, питомец": "Cat on windowsill, cozy home, domestic pet, peaceful scene, professional pet photography, comfortable perch, warm atmosphere, feline grace, lifestyle shot, charming companion",
        "Дождь за окном, уют внутри, чай": "Rain outside window, cozy interior, warm tea, comfortable indoors, professional photography, peaceful atmosphere, weather contrast, home comfort, relaxing moment, safe haven",
        "Вязаный свитер, тепло, комфорт, зима": "Knitted sweater, warm comfort, winter coziness, soft wool, professional photography, handmade quality, comfortable clothing, seasonal warmth, tactile pleasure, inviting texture",
        "Домашняя выпечка, аромат, уют, кухня": "Home baking, aromatic kitchen, cozy atmosphere, fresh pastries, professional photography, warm oven, inviting scent, domestic comfort, homemade quality, peaceful activity",
        "Гирлянды в комнате, мягкий свет, уют": "String lights in room, soft glow, cozy atmosphere, decorative lighting, professional interior photography, warm ambiance, peaceful mood, inviting space, gentle illumination, comfortable setting",
        "Теплые носки, камин, зима, комфорт": "Warm socks, fireplace, winter comfort, cozy feet, professional lifestyle photography, seasonal warmth, relaxing moment, home comfort, peaceful atmosphere, inviting scene",
        "Утро в постели, завтрак, уют, выходной": "Morning in bed, breakfast tray, cozy weekend, lazy day, professional lifestyle photography, comfortable setting, peaceful start, relaxing moment, home comfort, indulgent treat",
        "Растения в интерьере, зелень, уют, дом": "Indoor plants, green interior, cozy home, botanical decor, professional interior photography, natural elements, peaceful atmosphere, living space, biophilic design, fresh environment",
        "Мягкое кресло, чтение, спокойствие": "Comfortable armchair, reading nook, peaceful moment, cozy corner, professional interior photography, relaxing space, quiet time, home sanctuary, inviting seat, calm atmosphere",
        "Ароматические свечи, релакс, атмосфера": "Scented candles, relaxation atmosphere, aromatic ambiance, peaceful setting, professional photography, gentle glow, calming scents, spa-like mood, mindful moment, soothing environment",
        "Семейный вечер, тепло, любовь, дом": "Family evening, warm togetherness, loving home, domestic bliss, professional lifestyle photography, quality time, peaceful atmosphere, emotional connection, comfortable setting, heartwarming scene",
        
        # Фэнтези
        "Драконий замок на вершине горы, магическое сияние": "Dragon castle on mountain peak, magical glow, fantasy fortress, epic architecture, professional concept art, mystical atmosphere, towering structure, enchanted realm, dramatic sky, 8K ultra detailed",
        "Эльфийский лес, светящиеся растения, мистическая атмосфера": "Elven forest, bioluminescent plants, mystical atmosphere, magical woodland, professional fantasy art, glowing flora, enchanted realm, ethereal beauty, fantasy landscape, otherworldly scene",
        "Волшебник в башне, магические руны, книги заклинаний": "Wizard in tower, magical runes, spellbooks, sorcerer's sanctum, professional fantasy art, arcane knowledge, mystical atmosphere, ancient magic, glowing symbols, enchanted library",
        "Подводное королевство, русалки, коралловые дворцы": "Underwater kingdom, mermaids, coral palaces, aquatic realm, professional fantasy art, oceanic civilization, magical architecture, marine fantasy, bioluminescent beauty, mythical scene",
        "Летающий город в облаках, стимпанк элементы": "Flying city in clouds, steampunk elements, airborne metropolis, fantasy architecture, professional concept art, Victorian technology, floating islands, mechanical marvels, sky civilization, imaginative design",
        "Темный лес с мифическими существами, туман, загадочность": "Dark forest, mythical creatures, mysterious fog, enchanted woodland, professional fantasy art, magical beings, eerie atmosphere, fantasy realm, shadowy depths, mystical environment",
        "Кристаллическая пещера, светящиеся кристаллы, магия": "Crystal cavern, glowing crystals, magical cave, luminous minerals, professional fantasy art, underground wonder, ethereal glow, enchanted geology, mystical atmosphere, sparkling beauty",
        "Феникс возрождающийся из пепла, огненные крылья": "Phoenix rising from ashes, flaming wings, rebirth moment, mythical bird, professional fantasy art, fire and light, legendary creature, dramatic resurrection, magical transformation, epic scene",
        "Портал в другой мир, магический круг, энергия": "Portal to another world, magic circle, energy vortex, dimensional gateway, professional fantasy art, mystical passage, glowing runes, otherworldly connection, swirling power, epic transition",
        "Древний храм в джунглях, руины, мистика": "Ancient jungle temple, overgrown ruins, mystical atmosphere, lost civilization, professional fantasy art, archaeological wonder, magical remnants, tropical setting, mysterious past, epic discovery",
        "Ледяное королевство, снежная королева, северное сияние": "Ice kingdom, snow queen, aurora borealis, frozen realm, professional fantasy art, winter magic, crystalline palace, arctic beauty, regal presence, enchanted landscape",
        "Битва магов, заклинания, энергетические сферы": "Wizard battle, spell casting, energy spheres, magical combat, professional fantasy art, arcane warfare, glowing magic, dramatic confrontation, mystical powers, epic duel",
        "Мифический зверь-хранитель, величественная поза": "Mythical guardian beast, majestic pose, legendary creature, protective spirit, professional fantasy art, powerful presence, ancient protector, noble stance, magical being, epic scale",
        "Волшебный сад, говорящие цветы, феи": "Enchanted garden, talking flowers, fairy creatures, magical flora, professional fantasy art, whimsical atmosphere, mystical plants, tiny beings, colorful blooms, fantasy realm",
        "Астральный план, духи, эфирное свечение": "Astral plane, spirit beings, ethereal glow, otherworldly dimension, professional fantasy art, ghostly presence, mystical realm, translucent entities, magical atmosphere, spiritual world",
        
        # Экстрим (продолжение)
        "Сноубординг, горы, снег, скорость, адреналин": "Snowboarding action, mountain slopes, powder snow, high speed, professional action photography, extreme winter sport, adrenaline rush, athletic skill, dynamic moment, adventure lifestyle",
        "Серфинг, большая волна, океан, экстрим": "Big wave surfing, massive ocean swell, extreme sport, professional action photography, athletic courage, dangerous conditions, adrenaline rush, powerful water, epic scale, thrilling moment",
        "Скейтбординг, трюк, городская среда, драйв": "Skateboarding trick, urban environment, street action, professional action photography, athletic skill, city obstacles, dynamic movement, youth culture, extreme sport, creative expression",
    }
    
    # Обновляем промпты
    updated_count = 0
    for prompt in CategoryPrompt.objects.all():
        if prompt.prompt_text in prompts_mapping and not prompt.prompt_en:
            prompt.prompt_en = prompts_mapping[prompt.prompt_text]
            prompt.save(update_fields=['prompt_en'])
            updated_count += 1
    
    print(f"Часть 3 (финальная): Обновлено {updated_count} промптов")


def reverse_fill(apps, schema_editor):
    """Откат не требуется"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('generate', '0017_fill_remaining_english_prompts_part2'),
    ]

    operations = [
        migrations.RunPython(fill_english_prompts_part3, reverse_fill),
    ]
