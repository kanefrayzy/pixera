# Generated migration for filling professional English prompts

from django.db import migrations


def fill_english_prompts(apps, schema_editor):
    """Заполняет поле prompt_en профессиональными английскими промптами"""
    CategoryPrompt = apps.get_model('generate', 'CategoryPrompt')
    
    # Словарь: русский текст -> профессиональный английский промпт
    prompts_mapping = {
        # Абстракция
        "Абстрактные формы, яркие цвета, динамика": "Abstract geometric shapes, vibrant color palette, dynamic composition, fluid motion, contemporary art style, high contrast, bold brushstrokes, energetic movement, 8K resolution",
        "Геометрическая абстракция, четкие линии, минимализм": "Geometric abstract art, crisp clean lines, minimalist composition, precise angles, modern design, balanced symmetry, monochromatic palette with accent colors, professional vector style, ultra sharp details",
        "Жидкая абстракция, текучие формы, переливы": "Liquid abstract art, flowing organic forms, iridescent color transitions, smooth gradients, fluid dynamics, glossy finish, ethereal atmosphere, macro photography style, 8K ultra detailed",
        "Фрактальный узор, математическая красота": "Intricate fractal patterns, mathematical precision, infinite recursion, sacred geometry, vibrant neon colors, digital art, complex algorithmic design, mesmerizing symmetry, 4K ultra HD",
        "Цветовые пятна, экспрессионизм, эмоции": "Expressive color splashes, emotional abstract expressionism, bold impasto technique, raw artistic energy, dramatic contrasts, spontaneous brushwork, intense color saturation, gallery-quality canvas",
        "Абстрактный портрет, кубизм, грани": "Cubist abstract portrait, fragmented geometric faces, multiple perspectives, angular planes, Picasso-inspired style, bold color blocks, deconstructed features, modern art masterpiece",
        "Световая абстракция, неон, свечение": "Luminous abstract art, neon light trails, glowing particles, bioluminescent effects, dark background, vibrant electric colors, long exposure photography style, ethereal glow, 8K HDR",
        "Текстурная абстракция, рельеф, материалы": "Textured abstract composition, tactile relief surfaces, mixed media materials, impasto technique, layered depth, organic textures, earthy color palette, professional fine art photography",
        "Абстрактный пейзаж, импрессионизм, мазки": "Impressionist abstract landscape, visible brushstrokes, soft color blending, atmospheric perspective, dreamy ambiance, Monet-inspired palette, plein air painting style, natural light",
        "Цифровая абстракция, пиксели, глитч-арт": "Digital glitch art, pixelated distortion, data moshing effects, cyberpunk aesthetic, RGB color separation, corrupted data visualization, modern digital art, 4K resolution",
        "Органическая абстракция, природные формы": "Organic abstract forms, biomorphic shapes, natural flowing lines, earth-toned palette, botanical inspiration, smooth curves, harmonious composition, zen aesthetic",
        "Абстрактная композиция, баланс, гармония": "Balanced abstract composition, harmonious color theory, golden ratio proportions, visual equilibrium, sophisticated palette, professional gallery art, museum quality, perfect symmetry",
        "Монохромная абстракция, оттенки серого": "Monochromatic abstract art, grayscale gradient, tonal variations, minimalist black and white, subtle texture, dramatic shadows, high contrast, fine art photography style",
        "Абстрактное движение, энергия, вихрь": "Dynamic abstract motion, swirling vortex energy, kinetic movement, spiral composition, vibrant color flow, speed blur effect, powerful visual impact, 8K ultra sharp",
        "Минималистичная абстракция, простота, пространство": "Minimalist abstract art, negative space emphasis, simple geometric forms, clean composition, limited color palette, zen simplicity, modern gallery piece, ultra clean aesthetic",
        
        # Архитектура
        "Современный небоскреб, стеклянный фасад, отражения": "Modern glass skyscraper, reflective curtain wall facade, contemporary architecture, urban cityscape, blue hour lighting, mirror-like reflections, architectural photography, tilt-shift lens, 8K ultra detailed",
        "Готический собор, витражи, высокие своды": "Gothic cathedral interior, stunning stained glass windows, soaring vaulted ceilings, dramatic light rays, medieval architecture, ornate stone carvings, sacred atmosphere, wide-angle architectural shot",
        "Японский храм, традиционная архитектура, сад камней": "Traditional Japanese temple, authentic wooden architecture, zen rock garden, peaceful atmosphere, cherry blossoms, minimalist design, natural materials, golden hour lighting, cultural heritage",
        "Футуристическое здание, необычная форма, инновационный дизайн": "Futuristic architecture, innovative organic form, parametric design, cutting-edge engineering, sustainable materials, dramatic curves, Zaha Hadid style, architectural visualization, 8K photorealistic",
        "Античные руины, колонны, историческая атмосфера": "Ancient ruins, classical Greek columns, weathered marble, historical atmosphere, archaeological site, golden sunset light, dramatic sky, cultural heritage photography, cinematic composition",
        "Мост через реку, архитектурное чудо, закат": "Iconic bridge architecture, spanning river, engineering marvel, golden sunset reflection, dramatic sky, long exposure water, urban landscape, professional architectural photography, HDR",
        "Минималистичный дом, чистые линии, большие окна": "Minimalist modern house, clean architectural lines, floor-to-ceiling windows, open space design, natural light flooding, contemporary interior, Scandinavian aesthetic, architectural digest quality",
        "Барокко дворец, золотые украшения, роскошь": "Baroque palace interior, ornate gold decorations, luxurious chandeliers, frescoed ceilings, marble columns, opulent grandeur, Versailles style, royal magnificence, ultra detailed",
        "Промышленная архитектура, кирпич, лофт стиль": "Industrial loft architecture, exposed brick walls, steel beams, urban warehouse conversion, high ceilings, large windows, modern industrial design, raw materials, contemporary living",
        "Деревянный дом в скандинавском стиле, природа вокруг": "Scandinavian wooden cabin, natural timber construction, forest surroundings, minimalist Nordic design, large windows, cozy interior, sustainable architecture, nature integration, peaceful atmosphere",
        "Мечеть с куполами, исламская архитектура, орнаменты": "Grand mosque architecture, ornate domes, Islamic geometric patterns, intricate tile work, arabesque decorations, minarets, sacred Islamic art, golden hour lighting, cultural masterpiece",
        "Небоскребы Дубая, современная архитектура, ночная подсветка": "Dubai skyscrapers, futuristic architecture, illuminated night scene, Burj Khalifa, modern cityscape, LED lighting, luxury urban development, aerial photography, 8K ultra HD",
        "Старинная библиотека, деревянные полки, высокие потолки": "Historic library interior, wooden bookshelves, soaring ceilings, ornate architecture, warm ambient lighting, leather-bound books, scholarly atmosphere, Renaissance style, cinematic composition",
        "Оперный театр, классическая архитектура, величие": "Grand opera house, classical architecture, ornate interior, red velvet seats, golden balconies, crystal chandeliers, baroque details, cultural landmark, majestic atmosphere",
        "Экологичный дом, зеленая крыша, солнечные панели": "Eco-friendly house, green roof garden, solar panels, sustainable architecture, modern environmental design, energy efficient, natural materials, LEED certified, architectural innovation",
        
        # Будущее
        "Город будущего, небоскребы, летающие машины": "Futuristic cityscape, towering skyscrapers, flying vehicles, advanced technology, neon lights, cyberpunk atmosphere, sci-fi metropolis, holographic displays, 8K cinematic, Blade Runner aesthetic",
        "Киборг, человек и машина, технологии": "Cybernetic humanoid, human-machine fusion, advanced prosthetics, glowing circuitry, metallic components, sci-fi character design, detailed mechanical parts, futuristic technology, photorealistic rendering",
        "Космическая колония, другая планета, будущее": "Space colony settlement, alien planet landscape, futuristic domes, advanced architecture, distant stars, sci-fi environment, terraformed world, space exploration, cinematic sci-fi art",
        "Голографический интерфейс, технологии, взаимодействие": "Holographic user interface, floating digital displays, interactive technology, blue glowing projections, futuristic UI/UX, gesture control, sci-fi workspace, advanced computing, neon aesthetics",
        "Роботы в городе, автоматизация, будущее": "Humanoid robots, automated city, advanced AI, mechanical beings, futuristic urban environment, technological integration, sci-fi society, chrome finish, detailed robotics, 8K photorealistic",
        "Левитирующий транспорт, антигравитация, инновации": "Levitating vehicles, anti-gravity technology, floating transportation, magnetic suspension, futuristic design, sleek aerodynamics, sci-fi innovation, energy trails, advanced engineering",
        "Биотехнологии, генная инженерия, наука": "Biotechnology laboratory, genetic engineering, DNA visualization, scientific equipment, futuristic medical technology, glowing samples, advanced research facility, microscopic details, sci-fi science",
        "Виртуальный мир, цифровая реальность": "Virtual reality world, digital landscape, cyberspace environment, matrix-like grid, neon data streams, immersive VR experience, futuristic digital realm, glowing particles, 8K ultra detailed",
        "Энергетический щит, защита, технологии": "Energy shield barrier, force field protection, glowing hexagonal pattern, sci-fi defense system, translucent blue energy, advanced technology, protective dome, futuristic security",
        "Нанотехнологии, микромир, будущее": "Nanotechnology visualization, microscopic world, molecular structures, atomic scale, scientific illustration, glowing particles, futuristic science, detailed nano-robots, 8K macro photography",
        "Телепортация, перемещение, фантастика": "Teleportation portal, energy vortex, particle disintegration effect, sci-fi transportation, glowing gateway, dimensional travel, futuristic technology, light trails, cinematic VFX",
        
        # Винтаж
        "Ретро автомобиль, 50-е годы, классика": "Vintage 1950s automobile, classic car design, chrome details, pastel colors, retro styling, American classic, pristine condition, nostalgic atmosphere, professional car photography, golden hour",
        "Старинная пишущая машинка, винтажный стол": "Antique typewriter, vintage wooden desk, aged paper, nostalgic workspace, warm sepia tones, retro office, classic literature atmosphere, soft natural light, detailed textures",
        "Винтажная камера, пленочная фотография": "Vintage film camera, classic photography equipment, leather case, mechanical precision, retro technology, nostalgic aesthetic, warm tones, detailed close-up, professional product shot",
        "Ретро кафе, 60-е годы, уютная атмосфера": "Retro 1960s diner, vintage interior design, checkered floor, neon signs, classic booths, nostalgic ambiance, warm lighting, Americana aesthetic, cinematic composition",
        "Старинный граммофон, виниловые пластинки": "Antique gramophone, vinyl records collection, vintage music player, brass horn, wooden cabinet, nostalgic music atmosphere, warm ambient light, detailed craftsmanship",
        "Винтажная мода, 20-е годы, элегантность": "1920s vintage fashion, Art Deco elegance, flapper dress, pearl accessories, Great Gatsby style, sepia photography, classic glamour, sophisticated portrait, period costume",
        "Ретро телевизор, черно-белое изображение": "Vintage television set, black and white screen, retro electronics, mid-century modern, nostalgic technology, warm wood cabinet, classic design, period interior",
        "Старинная библиотека, кожаные переплеты": "Antique library, leather-bound books, vintage bookshelves, aged paper, scholarly atmosphere, warm candlelight, classic literature, ornate details, nostalgic ambiance",
        "Винтажный велосипед, ретро дизайн": "Vintage bicycle, classic retro design, chrome details, leather saddle, nostalgic transportation, urban street scene, warm afternoon light, lifestyle photography",
        "Ретро радио, ламповый приемник": "Vintage tube radio, retro receiver, warm glowing tubes, wooden cabinet, classic electronics, nostalgic technology, detailed craftsmanship, soft ambient lighting",
        "Старинные часы, механизм, детали": "Antique pocket watch, intricate mechanical movement, exposed gears, brass components, vintage timepiece, detailed macro photography, steampunk aesthetic, precision craftsmanship",
        "Винтажный постер, ретро реклама": "Vintage advertising poster, retro graphic design, classic typography, aged paper texture, nostalgic commercial art, bold colors, Art Deco style, collectible print",
        "Ретро телефон, дисковый набор": "Vintage rotary telephone, classic dial phone, retro communication, nostalgic technology, warm colors, detailed product shot, mid-century design, period piece",
        "Старинная швейная машинка, антиквариат": "Antique sewing machine, vintage Singer, ornate cast iron, mechanical precision, nostalgic craftsmanship, detailed metalwork, warm sepia tones, classic design",
        "Винтажная посуда, ретро кухня": "Vintage kitchenware, retro dishes, classic patterns, nostalgic tableware, pastel colors, 1950s kitchen aesthetic, detailed ceramics, warm domestic scene",
        
        # Города
        "Ночной Токио, неоновые огни, улицы": "Tokyo night scene, vibrant neon lights, bustling streets, cyberpunk atmosphere, Japanese signage, urban energy, rain-wet pavement, cinematic cityscape, 8K ultra detailed, Blade Runner aesthetic",
        "Парижские улочки, кафе, романтика": "Charming Parisian streets, sidewalk café, romantic atmosphere, Eiffel Tower view, cobblestone paths, French architecture, golden hour lighting, European elegance, cinematic composition",
        "Нью-Йорк, Таймс-сквер, толпы людей": "Times Square New York, massive LED billboards, crowded streets, urban energy, yellow cabs, iconic landmarks, night photography, vibrant city life, dynamic composition, HDR",
        "Венеция, каналы, гондолы": "Venice canals, traditional gondolas, historic architecture, romantic waterways, Italian Renaissance buildings, golden sunset reflection, European charm, travel photography, picturesque scene",
        "Дубай, небоскребы, роскошь": "Dubai skyline, luxury skyscrapers, Burj Khalifa, modern architecture, golden hour, opulent cityscape, futuristic development, aerial photography, 8K ultra HD, architectural marvel",
        "Лондон, Биг-Бен, туман": "London cityscape, Big Ben clock tower, atmospheric fog, Thames River, Gothic architecture, moody weather, British landmark, cinematic lighting, dramatic sky, professional photography",
        "Амстердам, каналы, велосипеды": "Amsterdam canals, Dutch architecture, bicycles parked, colorful buildings, European charm, canal houses, peaceful waterways, golden hour, travel photography, picturesque scene",
        "Барселона, Гауди, архитектура": "Barcelona architecture, Gaudi masterpieces, Sagrada Familia, modernist design, colorful mosaics, Spanish culture, artistic buildings, architectural photography, vibrant details",
        "Прага, старый город, готика": "Prague Old Town, Gothic architecture, medieval buildings, Charles Bridge, historic center, European heritage, atmospheric lighting, cobblestone streets, cultural landmark",
        "Сингапур, футуристический город": "Singapore futuristic cityscape, Marina Bay Sands, modern architecture, Gardens by the Bay, Supertrees, night illumination, urban innovation, architectural photography, 8K HDR",
        "Рим, Колизей, история": "Rome Colosseum, ancient Roman architecture, historical landmark, archaeological wonder, dramatic sky, golden hour lighting, cultural heritage, professional travel photography, epic composition",
        "Стамбул, мечети, восток": "Istanbul cityscape, Ottoman mosques, Blue Mosque, Hagia Sophia, Bosphorus view, Eastern architecture, cultural fusion, sunset lighting, Turkish heritage, cinematic composition",
        "Сидней, оперный театр, гавань": "Sydney Opera House, harbor view, iconic architecture, waterfront cityscape, Australian landmark, blue sky, sailboats, modern design, professional photography, HDR",
        "Гонконг, небоскребы, гавань": "Hong Kong skyline, dense skyscrapers, Victoria Harbor, neon lights, urban density, night cityscape, dramatic architecture, aerial photography, 8K ultra detailed, cyberpunk aesthetic",
        "Сан-Франциско, мост Золотые Ворота": "San Francisco Golden Gate Bridge, iconic landmark, fog rolling in, Pacific Ocean, suspension bridge, dramatic sky, California coastline, professional landscape photography, cinematic composition",
        
        # Дети
        "Ребенок с воздушными шарами, радость": "Happy child holding colorful balloons, joyful expression, bright sunny day, outdoor park setting, natural light, candid moment, vibrant colors, professional portrait photography, heartwarming scene",
        "Дети играют в парке, веселье": "Children playing in park, joyful activities, playground equipment, sunny day, natural outdoor setting, candid photography, happy childhood moments, vibrant colors, lifestyle photography",
        "Малыш с игрушкой, милота": "Adorable toddler with favorite toy, cute expression, soft natural light, cozy home setting, tender moment, pastel colors, professional baby photography, heartwarming portrait",
        "Дети рисуют, творчество": "Children creating art, colorful paintings, creative activity, messy hands, concentrated expressions, art supplies, natural light, candid moment, educational scene, vibrant colors",
        "Ребенок читает книгу, уют": "Child reading book, cozy atmosphere, warm lighting, comfortable setting, focused expression, educational moment, soft colors, peaceful scene, lifestyle photography",
        "Дети на пляже, лето, радость": "Children playing on beach, summer vacation, sandy shore, ocean waves, joyful expressions, bright sunshine, candid moments, vibrant colors, family photography, carefree childhood",
        "Малыш спит, нежность": "Sleeping baby, peaceful expression, soft blankets, gentle lighting, tender moment, pastel colors, newborn photography, serene atmosphere, professional portrait, heartwarming scene",
        "Дети празднуют день рождения": "Children's birthday party, colorful decorations, birthday cake, happy celebration, balloons, festive atmosphere, joyful expressions, candid moments, vibrant colors, party photography",
        "Ребенок с домашним животным": "Child with pet, loving interaction, cute moment, natural bond, outdoor setting, warm lighting, heartwarming scene, candid photography, emotional connection, lifestyle portrait",
        "Дети в школе, обучение": "Children in classroom, learning environment, educational setting, focused students, school supplies, natural light, candid moment, academic atmosphere, documentary photography",
        "Малыш делает первые шаги": "Toddler taking first steps, milestone moment, proud expression, supportive parents, home setting, natural light, candid photography, emotional scene, developmental achievement",
        "Дети в костюмах, праздник": "Children in costumes, festive celebration, colorful outfits, joyful expressions, party atmosphere, creative dress-up, candid moments, vibrant colors, holiday photography",
        "Ребенок смеется, эмоции": "Child laughing heartily, genuine joy, expressive face, natural moment, bright eyes, candid photography, emotional portrait, warm lighting, professional child photography",
        "Дети строят замок из песка": "Children building sandcastle, beach activity, creative play, summer fun, concentrated expressions, sandy hands, ocean background, candid moment, childhood memories",
        "Малыш с мыльными пузырями": "Toddler playing with soap bubbles, magical moment, wonder expression, outdoor setting, soft natural light, floating bubbles, joyful scene, candid photography, dreamy atmosphere",
        
        # Еда
        "Изысканный десерт, ресторанная подача": "Gourmet dessert plating, fine dining presentation, elegant garnish, professional food styling, soft studio lighting, shallow depth of field, culinary artistry, 8K macro photography, Michelin star quality",
        "Свежие фрукты, яркие цвета": "Fresh fruit arrangement, vibrant colors, water droplets, natural lighting, healthy food photography, colorful composition, organic produce, professional food styling, ultra detailed, appetizing presentation",
        "Пицца, аппетитная подача": "Artisan pizza, melted cheese, fresh ingredients, rustic wooden board, steam rising, professional food photography, appetizing close-up, Italian cuisine, warm lighting, mouth-watering presentation",
        "Суши, японская кухня, минимализм": "Authentic sushi platter, Japanese cuisine, minimalist presentation, fresh fish, elegant plating, traditional serving, professional food photography, clean composition, cultural authenticity",
        "Бургер, сочный, крупный план": "Gourmet burger close-up, juicy patty, fresh ingredients, melted cheese, sesame bun, professional food photography, appetizing details, restaurant quality, dramatic lighting, ultra sharp",
        "Паста, итальянская кухня": "Fresh pasta dish, Italian cuisine, al dente perfection, rich sauce, parmesan cheese, rustic presentation, professional food photography, warm lighting, culinary excellence, appetizing composition",
        "Салат, здоровое питание, свежесть": "Fresh salad bowl, healthy eating, vibrant vegetables, colorful ingredients, natural lighting, clean presentation, organic food, professional photography, nutritious meal, appetizing arrangement",
        "Стейк, мясо, гриль": "Perfectly grilled steak, juicy meat, grill marks, professional plating, restaurant quality, dramatic lighting, culinary perfection, food photography, appetizing presentation, Michelin star level",
        "Морепродукты, деликатесы": "Seafood platter, fresh shellfish, gourmet presentation, ocean delicacies, elegant plating, professional food photography, luxury dining, ice bed presentation, culinary artistry",
        "Выпечка, хлеб, аромат": "Artisan bread, fresh bakery, golden crust, rustic presentation, warm lighting, professional food photography, appetizing texture, homemade quality, steam rising, inviting aroma",
        "Коктейль, напиток, лед": "Craft cocktail, professional mixology, ice cubes, garnish details, elegant glassware, bar photography, vibrant colors, condensation droplets, studio lighting, premium beverage",
        "Кофе, латте-арт, уют": "Latte art coffee, barista craftsmanship, foam design, cozy café atmosphere, warm lighting, professional beverage photography, ceramic cup, aromatic steam, artisan coffee",
        "Шоколад, десерт, роскошь": "Luxury chocolate dessert, rich cocoa, elegant presentation, gourmet confection, professional food styling, dramatic lighting, indulgent treat, culinary artistry, premium quality",
        "Завтрак, утро, свежесть": "Fresh breakfast spread, morning meal, natural lighting, healthy start, colorful presentation, professional food photography, appetizing arrangement, nutritious options, inviting composition",
        "Барбекю, гриль, лето": "BBQ grill scene, summer cooking, smoky atmosphere, grilled meats, outdoor dining, professional food photography, appetizing presentation, charcoal grill, rustic setting",
        
        # Животные
        "Величественный лев, грива, саванна": "Majestic lion portrait, flowing mane, African savanna, golden hour lighting, wildlife photography, powerful gaze, natural habitat, professional nature shot, 8K ultra detailed, National Geographic style",
        "Милый котенок, игривость": "Adorable kitten, playful expression, soft fur, bright eyes, natural light, cute pet photography, heartwarming moment, professional portrait, shallow depth of field, charming details",
        "Дельфин в океане, прыжок": "Dolphin jumping, ocean spray, dynamic motion, marine wildlife, blue water, professional wildlife photography, graceful movement, natural behavior, cinematic action shot, crystal clear",
        "Панда ест бамбук, милота": "Giant panda eating bamboo, adorable expression, black and white fur, natural habitat, wildlife conservation, professional nature photography, peaceful moment, detailed close-up",
        "Орел в полете, свобода": "Eagle soaring, wings spread, mountain backdrop, freedom symbol, wildlife photography, dramatic sky, powerful flight, professional nature shot, majestic bird, 8K ultra sharp",
        "Слон с детенышем, семья": "Elephant with calf, family bond, African wildlife, maternal care, natural habitat, professional wildlife photography, emotional moment, savanna landscape, heartwarming scene",
        "Бабочка на цветке, макро": "Butterfly on flower, macro photography, vibrant colors, delicate wings, natural beauty, shallow depth of field, professional nature shot, detailed close-up, soft natural light",
        "Волк в лесу, дикая природа": "Wolf in forest, wild nature, piercing eyes, natural habitat, professional wildlife photography, atmospheric lighting, powerful predator, cinematic composition, untamed beauty",
        "Пингвины в Антарктиде": "Emperor penguins, Antarctic landscape, ice and snow, colony gathering, wildlife photography, harsh environment, natural behavior, professional nature shot, cold climate adaptation",
        "Колибри у цветка, скорость": "Hummingbird at flower, hovering motion, iridescent feathers, nectar feeding, high-speed photography, vibrant colors, professional wildlife shot, frozen motion, detailed wings",
        "Медведь ловит рыбу": "Bear catching salmon, river fishing, wildlife action, natural hunting, professional nature photography, dynamic moment, powerful predator, Alaska wilderness, dramatic composition",
        "Жираф в саванне, высота": "Giraffe in savanna, tall stature, African landscape, acacia trees, wildlife photography, golden hour, natural habitat, professional nature shot, graceful animal, scenic background",
        "Тигр в джунглях, хищник": "Tiger in jungle, powerful predator, striped pattern, dense vegetation, wildlife photography, intense gaze, natural habitat, professional nature shot, majestic big cat",
        "Коала на дереве, Австралия": "Koala on eucalyptus tree, Australian wildlife, cute marsupial, natural habitat, professional nature photography, peaceful moment, soft fur, adorable expression",
        "Морская черепаха, подводный мир": "Sea turtle swimming, underwater photography, coral reef, marine life, ocean conservation, professional wildlife shot, graceful movement, crystal clear water, natural behavior",
        
        # Интерьер
        "Современная гостиная, минимализм": "Modern minimalist living room, clean lines, neutral palette, contemporary furniture, natural light, open space, Scandinavian design, professional interior photography, 8K ultra detailed, architectural digest quality",
        "Уютная спальня, теплые тона": "Cozy bedroom interior, warm color palette, soft textiles, comfortable bedding, ambient lighting, inviting atmosphere, professional interior design, peaceful sanctuary, lifestyle photography",
        "Кухня в скандинавском стиле": "Scandinavian kitchen design, white cabinets, wooden accents, minimalist aesthetic, natural light, functional layout, modern appliances, clean lines, professional interior photography",
        "Домашний офис, рабочее пространство": "Home office workspace, ergonomic setup, natural lighting, organized desk, modern furniture, productive environment, professional interior design, minimalist aesthetic, inspiring workspace",
        "Ванная комната, спа-атмосфера": "Luxury spa bathroom, marble surfaces, freestanding tub, ambient lighting, hotel-quality design, professional interior photography, relaxing atmosphere, modern fixtures, elegant details",
        "Детская комната, яркие цвета": "Colorful children's room, playful design, bright colors, organized storage, creative space, fun atmosphere, professional interior photography, kid-friendly furniture, cheerful environment",
        "Столовая, семейные ужины": "Elegant dining room, family gathering space, modern table, comfortable seating, ambient lighting, professional interior design, inviting atmosphere, contemporary style",
        "Библиотека, книжные полки": "Home library, floor-to-ceiling bookshelves, reading nook, warm lighting, cozy atmosphere, professional interior photography, literary sanctuary, comfortable seating, intellectual space",
        "Лофт, индустриальный стиль": "Industrial loft interior, exposed brick, high ceilings, open floor plan, modern furniture, urban aesthetic, professional interior photography, contemporary design, raw materials",
        "Прихожая, первое впечатление": "Welcoming entryway, organized storage, mirror accent, natural light, functional design, professional interior photography, first impression space, clean aesthetic, practical layout",
        "Балкон, зона отдыха": "Cozy balcony retreat, outdoor furniture, plants, city view, relaxation space, professional interior photography, urban oasis, comfortable seating, peaceful atmosphere",
        "Гардеробная, организация": "Walk-in closet, organized storage, luxury wardrobe, professional interior design, efficient layout, ambient lighting, fashion sanctuary, modern fixtures, elegant organization",
        "Камин, уют, тепло": "Cozy fireplace setting, warm ambiance, comfortable seating, crackling fire, professional interior photography, inviting atmosphere, winter comfort, elegant design, peaceful scene",
        "Зимний сад, растения": "Indoor winter garden, lush plants, natural light, botanical sanctuary, professional interior photography, green oasis, peaceful atmosphere, nature integration, glass walls",
        "Подвал, развлекательная зона": "Basement entertainment room, home theater, game area, modern design, ambient lighting, professional interior photography, recreational space, comfortable seating, fun atmosphere",
        
        # Космос
        "Галактика, звезды, бесконечность": "Spiral galaxy, countless stars, cosmic infinity, deep space photography, nebula clouds, astronomical wonder, Hubble telescope quality, 8K ultra detailed, celestial beauty, vast universe",
        "Планета Земля из космоса": "Earth from space, blue marble, cloud formations, continents visible, orbital photography, stunning planet view, NASA quality, atmospheric glow, cosmic perspective, 8K resolution",
        "Луна, кратеры, поверхность": "Moon surface close-up, detailed craters, lunar landscape, astronomical photography, grey terrain, space exploration, high resolution, scientific accuracy, celestial body",
        "Марс, красная планета": "Mars landscape, red planet surface, rocky terrain, Martian atmosphere, space exploration, NASA rover perspective, alien world, scientific photography, planetary details",
        "Черная дыра, гравитация": "Black hole visualization, gravitational lensing, event horizon, accretion disk, cosmic phenomenon, scientific illustration, space-time distortion, astronomical art, theoretical physics",
        "Космонавт в открытом космосе": "Astronaut spacewalk, Earth backdrop, orbital EVA, space suit details, professional space photography, zero gravity, cosmic adventure, NASA mission, heroic moment",
        "Туманность, космические облака": "Colorful nebula, cosmic gas clouds, star formation region, deep space photography, vibrant colors, astronomical wonder, Hubble quality, celestial nursery, 8K ultra detailed",
        "Солнечная система, планеты": "Solar system visualization, planetary alignment, orbital paths, astronomical scale, scientific accuracy, educational illustration, cosmic family, space art, detailed planets",
        "Комета, хвост, космос": "Comet in space, glowing tail, ice and dust, celestial visitor, astronomical photography, cosmic traveler, dramatic trajectory, space phenomenon, detailed nucleus",
        "Млечный путь, ночное небо": "Milky Way galaxy, night sky photography, star trail, cosmic river, long exposure, astronomical beauty, dark sky location, professional astrophotography, celestial wonder",
        "Спутник Земли, орбита": "Earth satellite, orbital view, space technology, communication device, planet backdrop, professional space photography, technological achievement, cosmic perspective",
        "Звездное скопление, яркость": "Star cluster, brilliant stars, dense formation, astronomical photography, cosmic jewels, deep space view, celestial gathering, Hubble quality, vibrant colors",
        "Солнечное затмение, корона": "Solar eclipse, sun's corona, moon silhouette, astronomical event, professional photography, celestial alignment, dramatic moment, rare phenomenon, scientific wonder",
        "Космическая станция, технологии": "International Space Station, orbital laboratory, space technology, Earth backdrop, professional photography, human achievement, scientific research, cosmic outpost",
        "Метеоритный дождь, падающие звезды": "Meteor shower, shooting stars, night sky, celestial event, long exposure photography, cosmic display, astronomical phenomenon, starry background, magical moment",
        
        # Мода
        "Высокая мода, подиум, элегантность": "High fashion runway, elegant model, designer couture, professional fashion photography, dramatic lighting, luxury garments, catwalk moment, Vogue quality, 8K ultra detailed, sophisticated style",
        "Уличная мода, стиль, город": "Street style fashion, urban setting, trendy outfit, candid photography, city backdrop, contemporary fashion, lifestyle shot, editorial quality, modern aesthetic, fashion blogger",
        "Винтажный стиль, ретро одежда": "Vintage fashion, retro clothing, classic style, period costume, nostalgic aesthetic, professional fashion photography, timeless elegance, authentic details, styled photoshoot",
        "Спортивная одежда, активный образ жизни": "Athletic wear, active lifestyle, sportswear fashion, dynamic pose, fitness aesthetic, professional photography, modern activewear, performance clothing, energetic composition",
        "Вечернее платье, роскошь": "Luxury evening gown, elegant dress, formal fashion, red carpet style, professional photography, glamorous look, sophisticated design, high-end couture, dramatic lighting",
        "Деловой костюм, профессионализм": "Business suit, professional attire, corporate fashion, confident pose, office style, editorial photography, tailored fit, executive look, modern professional",
        "Бохо стиль, свобода, природа": "Boho fashion style, free-spirited outfit, natural setting, flowing fabrics, earthy tones, lifestyle photography, bohemian aesthetic, relaxed vibe, outdoor photoshoot",
        "Минималистичная мода, простота": "Minimalist fashion, clean lines, neutral colors, simple elegance, contemporary style, professional photography, understated chic, modern aesthetic, refined look",
        "Авангардная мода, эксперимент": "Avant-garde fashion, experimental design, artistic clothing, bold statement, editorial photography, unconventional style, creative expression, fashion art, innovative concept",
        "Летняя мода, легкость, яркость": "Summer fashion, light fabrics, bright colors, beach style, sunny day photography, casual elegance, vacation vibes, fresh look, outdoor setting",
        "Зимняя мода, тепло, уют": "Winter fashion, cozy outerwear, warm layers, cold weather style, professional photography, seasonal clothing, elegant warmth, urban winter scene, stylish comfort",
        "Аксессуары, детали, стиль": "Fashion accessories, detailed close-up, luxury items, professional product photography, elegant styling, designer pieces, refined details, high-end quality, sophisticated presentation",
        "Обувь, модная коллекция": "Designer footwear, fashion shoe collection, professional product photography, luxury shoes, detailed craftsmanship, elegant presentation, high-end quality, stylish design",
        "Ювелирные украшения, блеск": "Luxury jewelry, sparkling gems, precious metals, professional product photography, elegant presentation, high-end accessories, detailed craftsmanship, glamorous shine",
        "Сумки, модные аксессуары": "Designer handbags, luxury accessories, professional product photography, elegant styling, high-end fashion, detailed craftsmanship, sophisticated presentation, premium quality",
        
        # Музыка
        "Концерт, сцена, энергия": "Live concert performance, stage lighting, energetic atmosphere, crowd excitement, professional music photography, dynamic moment, rock show, dramatic lights, 8K ultra detailed, festival vibes",
        "Гитарист, рок, страсть": "Rock guitarist, passionate performance, electric guitar, stage presence, professional music photography, dramatic lighting, intense moment, musical expression, concert energy",
        "Диджей, клуб, танцы": "DJ performance, nightclub atmosphere, mixing console, crowd dancing, professional club photography, neon lights, electronic music, party energy, dynamic composition",
        "Оркестр, классическая музыка": "Symphony orchestra, classical performance, concert hall, professional musicians, elegant atmosphere, cultural event, musical excellence, formal setting, acoustic perfection",
        "Джаз-бар, саксофон, атмосфера": "Jazz club atmosphere, saxophone player, intimate venue, moody lighting, professional music photography, soulful performance, vintage aesthetic, musical artistry",
        "Барабанщик, ритм, динамика": "Drummer performance, rhythmic energy, drum kit, dynamic motion, professional music photography, concert lighting, powerful beats, musical intensity, action shot",
        "Пианист, рояль, элегантность": "Pianist at grand piano, elegant performance, classical music, professional photography, concert hall, musical artistry, refined atmosphere, cultural sophistication",
        "Рок-группа, выступление": "Rock band performance, group energy, stage show, professional concert photography, dramatic lighting, musical collaboration, live music, energetic atmosphere",
        "Электронная музыка, синтезаторы": "Electronic music setup, synthesizers, modern equipment, studio atmosphere, professional music photography, technological artistry, creative workspace, innovative sound",
        "Уличный музыкант, город": "Street musician, urban performance, acoustic guitar, city backdrop, candid photography, artistic expression, public space, cultural scene, authentic moment",
        "Студия звукозаписи, микрофон": "Recording studio, professional microphone, sound equipment, music production, technical setup, creative workspace, professional photography, acoustic treatment, artistic environment",
        "Виниловые пластинки, коллекция": "Vinyl record collection, music nostalgia, album covers, professional photography, retro aesthetic, music lover's treasure, detailed close-up, vintage quality",
        "Музыкальный фестиваль, толпа": "Music festival, massive crowd, outdoor concert, festival atmosphere, professional event photography, summer vibes, cultural gathering, energetic scene, aerial view",
        "Хор, пение, гармония": "Choir performance, vocal harmony, group singing, professional music photography, concert hall, cultural event, musical unity, elegant presentation, acoustic excellence",
        "Наушники, музыка, погружение": "Premium headphones, music immersion, professional product photography, audio equipment, detailed close-up, modern technology, sound quality, lifestyle shot",
        
        # Наука
        "Лаборатория, эксперимент, исследование": "Scientific laboratory, research experiment, modern equipment, professional scientist, clean environment, technical precision, educational setting, innovation workspace, 8K detailed, scientific discovery",
        "Микроскоп, клетки, биология": "Microscope view, cellular biology, scientific research, detailed microorganisms, laboratory equipment, professional photography, medical science, biological discovery, ultra magnification",
        "Химические реакции, колбы": "Chemical reaction, laboratory glassware, colorful solutions, scientific experiment, professional photography, bubbling liquids, research environment, precise measurement, educational science",
        "ДНК, генетика, наука": "DNA double helix, genetic research, molecular biology, scientific visualization, professional illustration, biotechnology, medical science, detailed structure, 3D rendering",
        "Телескоп, астрономия": "Astronomical telescope, stargazing equipment, observatory setting, professional photography, scientific instrument, night sky research, celestial observation, technical precision",
        "Робототехника, инженерия": "Robotics engineering, mechanical design, advanced technology, professional photography, innovative machinery, technical precision, futuristic development, scientific progress",
        "Физика, формулы, доска": "Physics equations, blackboard formulas, scientific notation, educational setting, mathematical concepts, professional photography, academic environment, theoretical science",
        "Медицинское оборудование, технологии": "Medical equipment, healthcare technology, hospital setting, professional photography, modern devices, clinical precision, patient care, scientific advancement",
        "Экология, природа, исследование": "Ecological research, nature study, environmental science, field work, professional photography, conservation effort, biological diversity, scientific observation",
        "Археология, раскопки, история": "Archaeological excavation, historical discovery, ancient artifacts, scientific research, professional photography, cultural heritage, careful documentation, historical preservation",
        "Космические технологии, ракеты": "Space technology, rocket engineering, aerospace development, professional photography, scientific innovation, launch preparation, technical precision, space exploration",
        "Нейронауки, мозг, исследование": "Neuroscience research, brain imaging, medical technology, scientific visualization, professional photography, cognitive science, neural networks, medical breakthrough",
        "Квантовая физика, частицы": "Quantum physics, particle visualization, scientific illustration, theoretical physics, professional rendering, subatomic world, scientific discovery, complex mathematics",
        "Геология, минералы, кристаллы": "Geological specimens, mineral crystals, natural formations, scientific photography, detailed close-up, earth science, colorful minerals, crystalline structure",
        "Ботаника, растения, исследование": "Botanical research, plant specimens, scientific study, professional photography, biological diversity, detailed observation, natural science, educational documentation",
        
        # Природа
        "Горный пейзаж, вершины, величие": "Majestic mountain landscape, snow-capped peaks, dramatic sky, alpine scenery, professional landscape photography, golden hour lighting, vast wilderness, 8K ultra detailed, National Geographic quality, breathtaking vista",
        "Лесной водопад, мох, свежесть": "Forest waterfall, moss-covered rocks, fresh mountain stream, lush vegetation, professional nature photography, long exposure water, peaceful atmosphere, natural beauty, pristine wilderness",
        "Закат на море, волны, спокойствие": "Ocean sunset, rolling waves, peaceful seascape, golden hour colors, professional landscape photography, serene atmosphere, coastal beauty, dramatic sky, tranquil waters",
        "Северное сияние, ночь, магия": "Aurora borealis, northern lights, night sky, magical atmosphere, professional astrophotography, vibrant colors, Arctic landscape, natural phenomenon, celestial display",
        "Пустыня, дюны, бескрайность": "Desert landscape, sand dunes, endless horizon, golden sand, professional landscape photography, dramatic shadows, arid beauty, vast wilderness, warm tones",
        "Тропический лес, джунгли, зелень": "Tropical rainforest, dense jungle, lush vegetation, vibrant green, professional nature photography, biodiversity, humid atmosphere, natural canopy, exotic plants",
        "Ледник, лед, холод": "Glacier landscape, ice formations, frozen wilderness, Arctic environment, professional nature photography, blue ice, pristine beauty, climate documentation, dramatic scenery",
        "Цветочное поле, весна, краски": "Flower field, spring blooms, vibrant colors, natural meadow, professional landscape photography, pastoral beauty, seasonal display, colorful carpet, peaceful scene",
        "Осенний лес, листва, золото": "Autumn forest, golden foliage, fall colors, seasonal beauty, professional landscape photography, warm tones, natural transformation, peaceful woodland, vibrant leaves",
        "Горное озеро, отражение, чистота": "Mountain lake, mirror reflection, crystal clear water, alpine scenery, professional landscape photography, peaceful atmosphere, pristine nature, dramatic backdrop",
        "Каньон, скалы, масштаб": "Grand canyon, rock formations, vast scale, geological wonder, professional landscape photography, dramatic cliffs, natural erosion, epic scenery, layered strata",
        "Вулкан, лава, мощь": "Active volcano, flowing lava, powerful eruption, geological phenomenon, professional nature photography, dramatic scene, natural force, molten rock, intense heat",
        "Коралловый риф, подводный мир": "Coral reef, underwater ecosystem, marine biodiversity, tropical fish, professional underwater photography, vibrant colors, ocean life, natural wonder, crystal clear water",
        "Радуга после дождя": "Rainbow after rain, colorful arc, dramatic sky, natural phenomenon, professional landscape photography, weather beauty, atmospheric optics, hopeful scene, vibrant spectrum",
        "Звездное небо, млечный путь": "Starry night sky, Milky Way galaxy, celestial view, professional astrophotography, cosmic beauty, dark sky location, astronomical wonder, long exposure, infinite universe",
        
        # Портрет
        "Профессиональный портрет молодой женщины, студийное освещение, 4K": "Professional portrait of young woman, studio lighting setup, soft key light, rim light accent, shallow depth of field, 85mm lens, natural skin tones, elegant pose, high-end retouching, 8K ultra detailed, fashion photography quality",
        "Портрет пожилого мужчины с седой бородой, мудрый взгляд, детализация морщин": "Character portrait of elderly man, distinguished grey beard, wise expression, detailed wrinkles, life experience, natural lighting, authentic emotion, professional headshot, storytelling photography, dignified presence",
        "Деловой портрет, офисный фон, профессионализм": "Corporate business portrait, office background, professional attire, confident expression, executive presence, clean lighting, modern setting, LinkedIn quality, corporate photography, polished appearance",
        "Художественный портрет, драматическое освещение, черно-белое": "Fine art portrait, dramatic chiaroscuro lighting, black and white photography, emotional depth, artistic expression, professional studio work, timeless aesthetic, gallery quality, moody atmosphere",
        "Портрет ребенка с голубыми глазами, естественный свет, мягкий фокус": "Child portrait, bright blue eyes, natural window light, soft focus, innocent expression, candid moment, professional children's photography, heartwarming scene, gentle atmosphere, pure emotion",
        "Модельный портрет, высокая мода, макияж": "Fashion model portrait, high fashion styling, professional makeup, editorial quality, dramatic pose, studio lighting, Vogue aesthetic, beauty photography, sophisticated look, glamorous presentation",
        "Портрет в золотой час, теплый свет, природа": "Golden hour portrait, warm natural light, outdoor setting, sunset glow, professional photography, soft shadows, romantic atmosphere, environmental portrait, beautiful bokeh",
        "Портрет музыканта с инструментом": "Musician portrait, instrument in frame, artistic expression, professional photography, creative composition, cultural documentation, passionate performer, authentic moment, storytelling image",
        "Семейный портрет, счастье, единство": "Family portrait, joyful expressions, togetherness, professional group photography, natural interaction, warm atmosphere, lifestyle shot, emotional connection, generational bond",
        "Портрет спортсмена, сила, решимость": "Athlete portrait, powerful physique, determined expression, professional sports photography, dramatic lighting, strength showcase, motivational image, peak performance, intense focus",
        "Автопортрет, творчество, самовыражение": "Creative self-portrait, artistic expression, personal vision, innovative composition, professional photography, introspective mood, unique perspective, conceptual art",
        "Портрет в стиле ренессанс, классика": "Renaissance-style portrait, classical painting aesthetic, dramatic lighting, rich colors, timeless elegance, fine art photography, historical inspiration, sophisticated composition",
        "Портрет танцора, движение, грация": "Dancer portrait, graceful movement, artistic pose, professional dance photography, elegant lines, dynamic composition, expressive body language, performance art",
        "Портрет в дожде, эмоции, атмосфера": "Rain portrait, emotional atmosphere, water droplets, moody lighting, professional photography, dramatic weather, cinematic feel, storytelling image, atmospheric conditions",
        "Портрет с животным, связь, нежность": "Portrait with pet, emotional bond, tender moment, professional photography, natural interaction, heartwarming scene, lifestyle shot, genuine connection, loving relationship",
        
        # Спорт
        "Футбол, гол, эмоции": "Soccer goal celebration, intense emotions, stadium atmosphere, professional sports photography, dynamic action, crowd excitement, athletic achievement, dramatic moment, 8K ultra detailed, sports journalism quality",
        "Баскетбол, данк, прыжок": "Basketball slam dunk, aerial action, powerful jump, professional sports photography, arena lighting, athletic prowess, dynamic moment, competitive spirit, freeze frame",
        "Теннис, удар, концентрация": "Tennis serve, focused concentration, powerful stroke, professional sports photography, court action, athletic precision, competitive moment, dynamic composition, peak performance",
        "Плавание, бассейн, скорость": "Swimming competition, pool action, speed and power, professional sports photography, underwater perspective, athletic determination, competitive race, dynamic motion, splash effects",
        "Бег, марафон, выносливость": "Marathon running, endurance athlete, determined expression, professional sports photography, road race, physical challenge, competitive spirit, motion blur, inspiring moment",
        "Велоспорт, гонка, скорость": "Cycling race, high speed action, professional sports photography, competitive peloton, athletic determination, dynamic motion, road cycling, team strategy, intense competition",
        "Гимнастика, грация, сила": "Gymnastics performance, graceful strength, athletic artistry, professional sports photography, perfect form, competitive routine, physical excellence, dynamic pose, Olympic quality",
        "Бокс, ринг, поединок": "Boxing match, ring combat, intense competition, professional sports photography, athletic power, dramatic lighting, competitive spirit, action moment, fighting determination",
        "Серфинг, волна, баланс": "Surfing action, riding wave, perfect balance, professional sports photography, ocean power, athletic skill, dynamic moment, coastal sport, extreme conditions",
        "Скейтбординг, трюк, улица": "Skateboarding trick, street action, urban sport, professional action photography, athletic skill, dynamic movement, youth culture, extreme sport, creative expression",
        "Хоккей, лед, скорость": "Ice hockey action, fast-paced game, professional sports photography, arena atmosphere, athletic intensity, competitive spirit, dynamic motion, team sport, winter athletics",
        "Волейбол, прыжок, команда": "Volleyball spike, jumping action, team coordination, professional sports photography, court dynamics, athletic power, competitive moment, synchronized movement, beach or indoor",
        "Гольф, удар, концентрация": "Golf swing, focused concentration, professional sports photography, course landscape, athletic precision, competitive moment, perfect form, outdoor sport, strategic play",
        "Лыжи, горы, скорость": "Alpine skiing, mountain descent, high speed action, professional sports photography, winter sport, athletic skill, snowy landscape, competitive racing, extreme conditions",
        "Единоборства, боевые искусства": "Martial arts combat, fighting technique, professional sports photography, athletic discipline, competitive match, dynamic action, traditional sport, physical mastery, intense focus",
        
        # Технологии
        "Современный смартфон, дизайн, инновации": "Modern smartphone design, sleek aesthetics, innovative technology, professional product photography, minimalist style, premium materials, cutting-edge features, studio lighting, 8K ultra detailed, tech showcase",
        "Ноутбук, рабочее место, продуктивность": "Laptop workspace, productive environment, modern technology, professional photography, clean desk setup, minimalist aesthetic, business tools, contemporary office, efficient workflow",
        "Виртуальная реальность, VR-очки": "Virtual reality headset, VR technology, immersive experience, professional product photography, futuristic design, gaming innovation, modern tech, digital world, cutting-edge device",
        "Дрон, аэросъемка, технологии": "Drone technology, aerial photography equipment, modern innovation, professional product shot, flying camera, technical precision, outdoor adventure, remote control, advanced features",
        "Умный дом, автоматизация": "Smart home technology, home automation, modern living, professional photography, IoT devices, connected lifestyle, innovative solutions, contemporary interior, digital integration",
        "Электромобиль, будущее транспорта": "Electric vehicle, sustainable transportation, modern automotive design, professional photography, eco-friendly technology, innovative engineering, sleek aesthetics, future mobility, clean energy",
        "3D-принтер, производство": "3D printer, additive manufacturing, modern technology, professional photography, innovative production, technical precision, creative possibilities, industrial design, future of making",
        "Искусственный интеллект, нейросети": "AI visualization, neural networks, machine learning, professional illustration, technological innovation, digital intelligence, futuristic concept, data processing, algorithmic art",
        "Криптовалюта, блокчейн": "Cryptocurrency visualization, blockchain technology, digital finance, professional illustration, modern economics, decentralized system, innovative concept, financial future, tech revolution",
        "Квантовый компьютер, вычисления": "Quantum computer, advanced computing, cutting-edge technology, professional photography, scientific innovation, complex calculations, futuristic hardware, technological breakthrough",
        "Солнечные панели, энергия": "Solar panels, renewable energy, sustainable technology, professional photography, clean power, environmental innovation, modern infrastructure, green technology, future energy",
        "Биометрия, безопасность": "Biometric security, fingerprint scanner, modern authentication, professional photography, technological safety, digital identity, innovative protection, futuristic access control",
        "Беспроводная зарядка, удобство": "Wireless charging, modern convenience, innovative technology, professional product photography, sleek design, cable-free solution, contemporary lifestyle, efficient power",
        "Голосовой ассистент, AI": "Voice assistant device, AI technology, smart speaker, professional product photography, modern home tech, hands-free control, innovative interface, connected living",
        "Носимые технологии, фитнес": "Wearable technology, fitness tracker, health monitoring, professional product photography, modern lifestyle, smart device, athletic innovation, wellness tech, connected fitness",
        
        # Фантастика
        "Космический корабль, звезды, путешествие": "Spaceship in deep space, star field background, interstellar journey, sci-fi concept art, futuristic vessel, cosmic adventure, professional digital art, cinematic composition, 8K ultra detailed, epic scale",
        "Инопланетная планета, чужой мир": "Alien planet landscape, exotic world, otherworldly environment, sci-fi concept art, strange vegetation, multiple moons, atmospheric effects, professional digital painting, imaginative scenery",
        "Робот-гуманоид, искусственный интеллект": "Humanoid robot, advanced AI, futuristic android, sci-fi character design, metallic surfaces, glowing elements, professional 3D rendering, detailed mechanics, photorealistic quality",
        "Портал в другое измерение": "Dimensional portal, energy vortex, sci-fi gateway, swirling colors, professional digital art, mystical atmosphere, otherworldly passage, glowing effects, cinematic lighting",
        "Летающий город, футуризм": "Flying city, futuristic architecture, floating metropolis, sci-fi concept art, advanced civilization, sky-high buildings, professional digital painting, imaginative design, epic scale",
        "Киберпанк улица, неон": "Cyberpunk street scene, neon lights, dystopian city, futuristic urban environment, rain-wet pavement, holographic ads, professional digital art, Blade Runner aesthetic, atmospheric mood",
        "Временной парадокс, петля времени": "Time paradox visualization, temporal loop, sci-fi concept, abstract representation, professional digital art, mind-bending imagery, chronological distortion, conceptual illustration",
        "Телепатия, связь разумов": "Telepathic connection, mind link visualization, sci-fi concept art, energy streams, mental communication, professional digital illustration, abstract representation, glowing effects",
        "Мутант, эволюция, изменения": "Mutant character, evolutionary changes, sci-fi creature design, biological transformation, professional concept art, detailed anatomy, imaginative features, dramatic presentation",
        "Подводный город, океан": "Underwater city, ocean depths, futuristic architecture, sci-fi concept art, marine environment, bioluminescent lighting, professional digital painting, aquatic civilization, glass domes",
        "Постапокалипсис, руины, выживание": "Post-apocalyptic landscape, urban ruins, survival setting, dystopian environment, professional concept art, desolate atmosphere, abandoned civilization, dramatic sky, weathered structures",
        "Генетический эксперимент, лаборатория": "Genetic experiment, sci-fi laboratory, futuristic science, professional concept art, glowing specimens, advanced equipment, mysterious atmosphere, biotechnology, ethical questions",
        "Параллельная вселенная, альтернатива": "Parallel universe, alternate reality, sci-fi concept, dimensional rift, professional digital art, reality distortion, multiple worlds, mind-bending visualization, cosmic scale",
        "Нанороботы, микромир": "Nanobots visualization, microscopic world, futuristic technology, sci-fi illustration, molecular scale, professional digital art, scientific accuracy, glowing particles, detailed mechanics",
        "Искусственная гравитация, космос": "Artificial gravity, space station interior, sci-fi environment, rotating habitat, professional concept art, futuristic living, zero-g adaptation, advanced engineering, realistic physics",
        
        # Экстрим
        "Серфинг на больших волнах, адреналин": "Big wave surfing, extreme action, adrenaline rush, professional sports photography, massive ocean swell, athletic courage, dynamic moment, dangerous conditions, 8K ultra detailed, epic scale",
        "Скалолазание без страховки, высота": "Free solo climbing, extreme height, no safety rope, professional action photography, sheer cliff face, athletic skill, dangerous sport, mental focus, breathtaking perspective",
        "Прыжок с парашютом, свободное падение": "Skydiving freefall, extreme sport, aerial perspective, professional action photography, adrenaline moment, cloud backdrop, athletic courage, dynamic composition, thrilling experience",
        "Сноубординг, трюк, горы": "Snowboarding trick, mountain backdrop, extreme winter sport, professional action photography, aerial maneuver, athletic skill, powder snow, dynamic moment, adventure lifestyle",
        "Банджи-джампинг, прыжок, высота, страх": "Bungee jumping, extreme height, leap of faith, professional action photography, adrenaline rush, elastic cord, fearless moment, dramatic perspective, thrilling experience",
        "Паркур, город, прыжки, акробатика": "Parkour action, urban environment, acrobatic jumps, professional action photography, athletic skill, city obstacles, dynamic movement, extreme sport, creative navigation",
        "Мотокросс, грязь, скорость, мотоцикл": "Motocross racing, muddy terrain, high speed action, professional sports photography, dirt bike, athletic skill, extreme conditions, dynamic motion, competitive spirit",
        "Скалолазание, высота, сила, концентрация": "Rock climbing, extreme height, physical strength, professional action photography, mental focus, challenging route, athletic determination, outdoor adventure, vertical world",
        "Кайтсерфинг, ветер, вода, свобода": "Kitesurfing action, wind power, water sport, professional action photography, aerial tricks, athletic skill, ocean waves, extreme conditions, freedom feeling",
        "BMX трюки, велосипед, экстрим, мастерство": "BMX tricks, bicycle stunts, extreme sport, professional action photography, aerial maneuvers, athletic skill, urban setting, dynamic action, youth culture",
        "Вингсьют, полет, небо, адреналин": "Wingsuit flying, human flight, sky diving, professional action photography, extreme sport, aerial perspective, adrenaline rush, mountain backdrop, thrilling experience",
        "Дайвинг с акулами, опасность, смелость": "Shark diving, dangerous encounter, underwater photography, extreme adventure, marine predators, athletic courage, ocean depths, thrilling experience, wildlife interaction",
        "Сноукайтинг, снег, ветер, скорость": "Snow kiting, winter extreme sport, wind power, professional action photography, snowy landscape, high speed, athletic skill, mountain setting, dynamic movement",
        "Фрирайд, горы, снег, свобода": "Freeride skiing, mountain terrain, powder snow, professional action photography, extreme winter sport, athletic skill, backcountry adventure, freedom feeling, natural landscape",
        "Слэклайн, баланс, высота, концентрация": "Slacklining, extreme balance, high altitude, professional action photography, mental focus, athletic skill, mountain backdrop, dangerous height, zen concentration",
        "Дрифт, автомобиль, дым, контроль": "Drift racing, car control, tire smoke, professional action photography, motorsport skill, dynamic motion, extreme driving, competitive spirit, adrenaline rush",
        
        # Эмоции
        "Радость, смех, счастье, позитив, улыбка": "Pure joy expression, genuine laughter, happiness radiating, positive energy, bright smile, professional portrait photography, emotional authenticity, heartwarming moment, natural light, candid emotion",
        "Грусть, слезы, меланхолия, печаль": "Sadness expression, emotional tears, melancholic mood, sorrowful moment, professional portrait photography, authentic emotion, dramatic lighting, vulnerable state, touching scene",
        "Удивление, широко открытые глаза, шок": "Surprise expression, wide-eyed shock, astonished reaction, professional portrait photography, genuine emotion, dramatic moment, spontaneous response, expressive face",
        "Гнев, ярость, напряжение, эмоция": "Anger expression, intense rage, emotional tension, professional portrait photography, powerful emotion, dramatic lighting, fierce look, raw feeling, intense moment",
        "Страх, испуг, тревога, беспокойство": "Fear expression, frightened look, anxiety visible, professional portrait photography, vulnerable emotion, tense atmosphere, worried state, authentic feeling",
        "Любовь, нежность, объятия, тепло": "Love expression, tender embrace, warm affection, professional portrait photography, emotional connection, gentle moment, heartfelt feeling, intimate scene",
        "Восторг, восхищение, вдохновение": "Delight expression, admiration visible, inspired moment, professional portrait photography, joyful emotion, enthusiastic reaction, uplifting feeling, positive energy",
        "Спокойствие, умиротворение, медитация": "Peaceful expression, serene meditation, tranquil state, professional portrait photography, calm emotion, zen atmosphere, relaxed moment, inner peace",
        "Задумчивость, размышление, концентрация": "Thoughtful expression, deep contemplation, focused concentration, professional portrait photography, introspective mood, intellectual moment, pensive state",
        "Веселье, смех, радость, праздник": "Cheerful expression, joyful laughter, celebration mood, professional portrait photography, festive emotion, happy moment, party atmosphere, positive vibes",
        "Ностальгия, воспоминания, прошлое": "Nostalgic expression, reminiscing moment, memories surfacing, professional portrait photography, wistful emotion, sentimental mood, reflective state, touching scene",
        "Надежда, оптимизм, вера, будущее": "Hopeful expression, optimistic outlook, faithful belief, professional portrait photography, positive emotion, forward-looking, inspiring moment, bright future",
        "Усталость, истощение, отдых": "Tired expression, exhausted state, need for rest, professional portrait photography, weary emotion, drained feeling, recovery moment, human vulnerability",
        "Вдохновение, креативность, идея": "Inspired expression, creative spark, idea moment, professional portrait photography, artistic emotion, innovative thinking, eureka feeling, imaginative state",
        "Благодарность, признательность, тепло": "Grateful expression, thankful emotion, warm appreciation, professional portrait photography, heartfelt feeling, sincere gratitude, touching moment, emotional warmth",
        
        # Эстетика
        "Минималистичная композиция, пастельные тона, мягкий свет": "Minimalist composition, pastel color palette, soft diffused lighting, clean aesthetic, professional photography, simple elegance, gentle atmosphere, contemporary style, 8K ultra detailed, refined beauty",
        "Винтажная эстетика, ретро цвета, пленочная фотография": "Vintage aesthetic, retro color grading, film photography style, nostalgic atmosphere, professional photography, aged look, classic vibe, warm tones, analog feel",
        "Бохо стиль, натуральные материалы, уютная атмосфера": "Boho aesthetic, natural materials, cozy atmosphere, earthy tones, professional photography, free-spirited style, organic textures, relaxed vibe, comfortable setting",
        "Скандинавский минимализм, белые тона, чистые линии": "Scandinavian minimalism, white color scheme, clean lines, Nordic aesthetic, professional photography, simple elegance, functional beauty, bright atmosphere, contemporary design",
        "Японская эстетика ваби-саби, простота, несовершенство": "Wabi-sabi aesthetic, embracing imperfection, simple beauty, Japanese philosophy, professional photography, natural materials, rustic charm, authentic character, zen atmosphere",
        "Парижский шик, элегантность, черно-белая гамма": "Parisian chic, elegant style, black and white palette, sophisticated aesthetic, professional photography, timeless beauty, French elegance, classic composition, refined taste",
        "Тропическая эстетика, пальмы, яркие цвета": "Tropical aesthetic, palm trees, vibrant colors, exotic atmosphere, professional photography, summer vibes, lush vegetation, paradise feeling, warm climate",
        "Готическая эстетика, темные тона, драматизм": "Gothic aesthetic, dark tones, dramatic atmosphere, mysterious mood, professional photography, Victorian influence, ornate details, moody lighting, romantic darkness",
        "Cottagecore эстетика, деревенский уют, цветы": "Cottagecore aesthetic, rural charm, wildflowers, pastoral beauty, professional photography, countryside living, natural simplicity, cozy atmosphere, romantic nostalgia",
        "Vaporwave эстетика, неоновые цвета, ретро-футуризм": "Vaporwave aesthetic, neon colors, retro-futurism, digital art style, professional photography, 80s nostalgia, surreal atmosphere, glitch effects, cyberpunk vibes",
        "Академическая эстетика, книги, винтажная мебель": "Academic aesthetic, vintage books, antique furniture, scholarly atmosphere, professional photography, intellectual vibe, classic library, warm lighting, timeless elegance",
        "Морская эстетика, синие тона, ракушки, волны": "Nautical aesthetic, blue color palette, seashells, ocean waves, professional photography, coastal living, maritime charm, beach vibes, aquatic beauty",
        "Осенняя эстетика, теплые тона, уют, свечи": "Autumn aesthetic, warm color tones, cozy atmosphere, candlelight, professional photography, fall season, comfortable setting, hygge feeling, seasonal beauty",
        "Космическая эстетика, звезды, галактики, фиолетовые тона": "Cosmic aesthetic, starry sky, galaxies, purple color palette, professional photography, celestial beauty, space theme, dreamy atmosphere, astronomical wonder",
        "Артхаус эстетика, необычные ракурсы, глубокие цвета": "Arthouse aesthetic, unusual angles, deep rich colors, artistic photography, experimental composition, cinematic mood, creative vision, sophisticated style, gallery quality",
    }
    
    # Обновляем все промпты
    updated_count = 0
    for prompt in CategoryPrompt.objects.all():
        if prompt.prompt_text in prompts_mapping:
            prompt.prompt_en = prompts_mapping[prompt.prompt_text]
            prompt.save(update_fields=['prompt_en'])
            updated_count += 1
    
    print(f"Обновлено {updated_count} промптов из {CategoryPrompt.objects.count()}")


def reverse_fill(apps, schema_editor):
    """Откат: очищаем поле prompt_en"""
    CategoryPrompt = apps.get_model('generate', 'CategoryPrompt')
    CategoryPrompt.objects.all().update(prompt_en='')


class Migration(migrations.Migration):

    dependencies = [
        ('generate', '0015_add_prompt_en_field'),
    ]

    operations = [
        migrations.RunPython(fill_english_prompts, reverse_fill),
    ]
