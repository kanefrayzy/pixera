# 🎬 VIDEO GENERATION - ПОЛНАЯ ДОКУМЕНТАЦИЯ

## ✅ ВСЁ РАБОТАЕТ И СОХРАНЕНО!

**Git Commit:** `c59f0a6` - VIDEO: I2V uploadImage API + T2V models
**Дата:** 13.10.2025, 00:22

---

## 📋 ЧТО РАБОТАЕТ

### 🎥 Text-to-Video (T2V)
✅ **Google Veo 3.0 PRO**
- Duration: 8 секунд (автоматически)
- Resolution: 1280x720
- Параметры: enhance_prompt, generate_audio
- Стоимость: ~50 TOK

✅ **Google Veo 2.0**
- Duration: 2-10 секунд
- Resolution: 1280x720
- Параметры: enhance_prompt
- Стоимость: ~40 TOK

### 🖼️ Image-to-Video (I2V)
✅ **Vidu Q1** (vidu:1@1)
- Resolution: 1920x1080 (зафиксировано)
- Duration: 5 секунд (зафиксировано)
- **Работает в localhost через uploadImage API!**

✅ **Vidu 2.0** (vidu:2@0)
- Resolution: 1920x1080
- Duration: настраиваемо
- **Работает в localhost через uploadImage API!**

---

## 🔧 ТЕХНИЧЕСКОЕ РЕШЕНИЕ I2V

### Проблема:
Runware API не принимает:
- ❌ localhost URL
- ❌ data URI для frameImages
- ❌ base64 напрямую

### Решение (2-шаговое):

**Шаг 1: uploadImage API**
```python
def _upload_image_to_runware(image_bytes: bytes) -> str:
    payload = [{
        "taskType": "uploadImage",
        "taskUUID": str(uuid.uuid4()),
        "inputImage": f"data:{mime_type};base64,{b64}",
    }]
    # Возвращает imageUUID
```

**Шаг 2: videoInference с UUID**
```python
def generate_video_from_image(...):
    image_uuid = _upload_image_to_runware(image_bytes)

    payload = [{
        "taskType": "videoInference",
        "frameImages": [image_uuid],  # UUID работает!
        "model": "vidu:1@1",
        "deliveryMethod": "sync"
    }]
```

---

## 📁 КЛЮЧЕВЫЕ ФАЙЛЫ

### Backend:
1. **ai_gallery/services/runware_client.py**
   - `_upload_image_to_runware()` - загрузка изображения → UUID
   - `generate_video_via_rest()` - Text-to-Video
   - `generate_video_from_image()` - Image-to-Video
   - `_build_provider_settings()` - автонастройка параметров

2. **generate/views_video_api.py**
   - `video_submit()` - приём запросов на генерацию
   - `video_status()` - проверка статуса
   - Автоматическое списание токенов
   - Сохранение в галерею

3. **generate/models.py**
   - `VideoModel` - модели видео
   - `GenerationJob` - задачи генерации
   - Dynamic fields для каждого провайдера

### Frontend:
4. **static/js/video-generation.js**
   - Динамические поля провайдера
   - Автообновление интерфейса
   - Sync режим обработки

5. **templates/generate/index.html**
   - T2V и I2V вкладки
   - Загрузка изображений
   - Выбор моделей

---

## 🎯 КАК ИСПОЛЬЗОВАТЬ

### Text-to-Video:
```python
# 1. Выберите модель
model = VideoModel.objects.get(model_id='google:3@0')

# 2. Генерация
video_url = generate_video_via_rest(
    prompt="Beautiful sunset over ocean",
    model_id="google:3@0",
    duration=8,  # автоматически для Veo 3.0
    enhance_prompt=True,
    generate_audio=True
)

# 3. Видео готово моментально!
```

### Image-to-Video:
```python
# 1. Загрузите изображение
with open('image.jpg', 'rb') as f:
    image_bytes = f.read()

# 2. Генерация
video_url = generate_video_from_image(
    prompt="Camera slowly pans right",
    model_id="vidu:1@1",
    image_bytes=image_bytes,
    duration=5,  # зафиксировано для Vidu Q1
)

# 3. Видео готово!
```

---

## 🚀 АВТОМАТИЧЕСКИЕ НАСТРОЙКИ

### Google Veo 3.0:
- Duration: **всегда 8 секунд**
- Resolution: **1280x720**
- Параметры: enhance_prompt, generate_audio

### Google Veo 2.0:
- Duration: **2-10 секунд**
- Resolution: **1280x720**
- Параметры: enhance_prompt

### Vidu Q1:
- Duration: **всегда 5 секунд**
- Resolution: **всегда 1920x1080**
- I2V через uploadImage API

### Vidu 1.5:
- Duration: **всегда 4 секунды**
- BGM: только если duration = 4 сек
- Параметры: movement_amplitude, style

---

## 🔐 БЕЗОПАСНОСТЬ

### Localhost поддержка:
✅ I2V работает через uploadImage API
✅ Не требуется публичный URL
✅ Не требуется CDN
✅ Изображения загружаются во временное хранилище Runware

### Валидация:
- Размер изображения: до 10MB
- Форматы: JPG, PNG, WEBP
- Автоматическая оптимизация
- Проверка токенов перед генерацией

---

## 💾 БАЗА ДАННЫХ

### Миграции выполнены:
- ✅ 0020_add_video_generation_models.py
- ✅ 0021_add_video_prompt_categories.py
- ✅ VideoModel таблица создана
- ✅ GenerationJob расширена для видео
- ✅ Все индексы настроены

### Модели в БД:
```sql
-- Google Veo
INSERT INTO generate_videomodel (model_id, name, category, token_cost)
VALUES ('google:3@0', 'Google Veo 3.0 PRO', 't2v', 50);

-- Vidu
INSERT INTO generate_videomodel (model_id, name, category, token_cost)
VALUES ('vidu:1@1', 'Vidu Q1', 'i2v', 40);
```

---

## 📊 API ENDPOINTS

### POST /api/video/submit/
Создание задачи генерации видео

**Параметры T2V:**
```json
{
  "prompt": "Beautiful sunset",
  "video_model_id": 1,
  "generation_mode": "t2v",
  "duration": 8,
  "provider_fields": {
    "enhance_prompt": true,
    "generate_audio": true
  }
}
```

**Параметры I2V:**
```json
{
  "prompt": "Camera pan right",
  "video_model_id": 2,
  "generation_mode": "i2v",
  "source_image": "<file>",
  "duration": 5,
  "provider_fields": {
    "movement_amplitude": "auto"
  }
}
```

**Response (Sync):**
```json
{
  "success": true,
  "job_id": 123,
  "status": "done",
  "video_url": "https://...",
  "gallery_id": 456,
  "instant": true
}
```

### GET /api/video/status/{job_id}/
Проверка статуса задачи

---

## 🎨 FRONTEND ИНТЕРФЕЙС

### Вкладки:
1. **Text-to-Video** - генерация из текста
2. **Image-to-Video** - генерация из изображения

### Динамические поля:
- Показываются только для поддерживающих моделей
- Автообновление при смене модели
- Tooltips с описанием параметров

### Sync режим:
- Видео готово моментально
- Прогресс бар (если async)
- Автоматическое сохранение в галерею

---

## 🐛 РЕШЕННЫЕ ПРОБЛЕМЫ

### ❌ Проблема 1: BGM для Vidu 1.5
**Ошибка:** Background music can only be used with videos of exactly 4 seconds
**Решение:** Автоматическая проверка duration перед отправкой

### ❌ Проблема 2: I2V frameImages
**Ошибка:** Invalid value for 'frameImages' parameter
**Решение:** 2-шаговая загрузка через uploadImage API

### ❌ Проблема 3: Localhost URL
**Ошибка:** Runware не принимает localhost
**Решение:** Загрузка через uploadImage вместо URL

### ❌ Проблема 4: Data URI
**Ошибка:** Invalid format
**Решение:** Data URI работает для uploadImage, UUID для videoInference

---

## 📝 NEXT STEPS (опционально)

### Будущие улучшения:
1. **Async режим** для длинных видео (опционально)
2. **Batch генерация** - несколько видео одновременно
3. **Video editing** - обрезка, склейка
4. **Advanced параметры** - больше контроля

### CDN (если нужен):
```python
# Для production можно настроить CDN:
# 1. AWS S3 / Cloudflare R2
# 2. Загрузка изображений на CDN
# 3. Использование публичного URL вместо uploadImage

def upload_to_cdn(image_bytes):
    # Upload to S3/R2
    return public_url
```

---

## ✅ ФИНАЛЬНЫЙ ЧЕКЛИСТ

- [x] T2V работает (Google Veo 2.0/3.0)
- [x] I2V работает (Vidu Q1/2.0)
- [x] Localhost поддержка через uploadImage
- [x] Автоматическая настройка параметров
- [x] Sync режим - видео моментально
- [x] Динамические поля провайдера
- [x] Автоперевод промптов
- [x] Списание токенов
- [x] Сохранение в галерею
- [x] Git commit создан
- [x] Документация готова

---

## 🎉 ПРОЕКТ ГОТОВ!

**Всё сохранено, всё работает, завтра ничего не сломается!**

### Запуск проекта:
```bash
# 1. Активируйте виртуальное окружение
python -m venv venv
venv\Scripts\activate

# 2. Запустите сервер
python manage.py runserver

# 3. Откройте http://localhost:8000/generate/
```

### Тестирование:
```bash
# T2V
1. Выберите "Text-to-Video"
2. Model: Google Veo 3.0 PRO
3. Prompt: "Beautiful sunset over ocean"
4. Generate!

# I2V
1. Выберите "Image-to-Video"
2. Model: Vidu Q1
3. Upload image
4. Prompt: "Camera slowly pans right"
5. Generate!
```

**🚀 ВСЁ РАБОТАЕТ! ПРОЕКТ СОХРАНЁН!**
