import requests
import uuid
import logging
import base64
from typing import Optional, Dict, Any, List
from django.conf import settings

logger = logging.getLogger(__name__)


class RunwareError(Exception):
    """Базовое исключение для ошибок Runware API."""
    pass


class RunwareVideoError(RunwareError):
    """Исключение для ошибок генерации видео."""
    pass


def generate_image_via_rest(prompt: str, model_id: str | None, width=1024, height=1024, number_results=1):
    """Генерация изображения через Runware API."""
    if not settings.RUNWARE_API_KEY:
        raise RunwareError("RUNWARE_API_KEY not configured")

    model = model_id or settings.RUNWARE_DEFAULT_MODEL
    if model not in settings.RUNWARE_ALLOWED_MODELS:
        raise RunwareError("Model is not allowed")

    payload = [{
        "taskType": "imageInference",
        "taskUUID": str(uuid.uuid4()),
        "positivePrompt": prompt,
        "width": width,
        "height": height,
        "model": model,
        "numberResults": number_results,
        "outputType": "URL",
        "checkNSFW": bool(settings.RUNWARE_CHECK_NSFW),
    }]
    r = requests.post(
        settings.RUNWARE_API_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {settings.RUNWARE_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    items = data.get("data") or []
    urls = [it["imageURL"] for it in items if it.get("imageURL")]
    if not urls:
        raise RunwareError(f"No images: {data}")
    return urls


def _extract_video_url(data: dict) -> Optional[str]:
    """Извлекает videoURL из ответа Runware."""
    try:
        arr = data.get("data") or []
        if not isinstance(arr, list):
            return None
        for item in arr:
            if not isinstance(item, dict):
                continue
            # Пробуем разные варианты названия поля
            if isinstance(item.get("videoURL"), str):
                return item["videoURL"]
            if isinstance(item.get("url"), str):
                return item["url"]
            # Может быть вложенное
            videos = item.get("videos")
            if isinstance(videos, list) and videos and isinstance(videos[0], dict):
                u = videos[0].get("url")
                if isinstance(u, str):
                    return u
    except Exception:
        pass
    return None


def _build_provider_settings(model_id: str, **kwargs) -> Dict[str, Any]:
    """
    Формирует providerSettings на основе model_id и дополнительных параметров.

    Args:
        model_id: ID модели (например, 'bytedance:1@1', 'google:3@0')
        **kwargs: Дополнительные параметры (camera_movement, style, effect и т.д.)

    Returns:
        Dict с providerSettings или пустой dict
    """
    provider_settings = {}

    # Определяем провайдера из model_id
    provider = model_id.split(':')[0].lower() if ':' in model_id else ''

    # ByteDance
    if provider == 'bytedance':
        provider_settings['bytedance'] = {
            'cameraFixed': kwargs.get('camera_fixed', False)
        }

    # Google Veo
    elif provider == 'google':
        google_settings = {
            'enhancePrompt': kwargs.get('enhance_prompt', True),
        }
        # generateAudio только для Veo 3.0
        if model_id == 'google:3@0':
            google_settings['generateAudio'] = kwargs.get('generate_audio', False)
        provider_settings['google'] = google_settings

    # MiniMax
    elif provider == 'minimax':
        provider_settings['minimax'] = {
            'promptOptimizer': kwargs.get('prompt_optimizer', False)
        }

    # PixVerse
    elif provider == 'pixverse':
        pixverse_settings = {}

        if kwargs.get('style'):
            pixverse_settings['style'] = kwargs['style']

        if kwargs.get('effect'):
            pixverse_settings['effect'] = kwargs['effect']

        if kwargs.get('camera_movement'):
            pixverse_settings['cameraMovement'] = kwargs['camera_movement']

        if kwargs.get('motion_mode'):
            pixverse_settings['motionMode'] = kwargs['motion_mode']

        if kwargs.get('sound_effect_switch') is not None:
            pixverse_settings['soundEffectSwitch'] = kwargs['sound_effect_switch']

        if kwargs.get('sound_effect_content'):
            pixverse_settings['soundEffectContent'] = kwargs['sound_effect_content']

        if pixverse_settings:
            provider_settings['pixverse'] = pixverse_settings

    # Vidu
    elif provider == 'vidu':
        vidu_settings = {}

        if kwargs.get('movement_amplitude'):
            vidu_settings['movementAmplitude'] = kwargs['movement_amplitude']

        if kwargs.get('bgm') is not None:
            vidu_settings['bgm'] = kwargs['bgm']

        if kwargs.get('style'):
            vidu_settings['style'] = kwargs['style']

        if vidu_settings:
            provider_settings['vidu'] = vidu_settings

    return provider_settings


def generate_video_via_rest(
    prompt: str,
    model_id: str,
    duration: int = 5,
    aspect_ratio: str = "16:9",
    resolution: str = "1920x1080",
    camera_movement: Optional[str] = None,
    seed: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Генерация видео через Runware API (Text-to-Video).

    ОБЯЗАТЕЛЬНЫЕ параметры:
        - prompt: Текстовое описание видео
        - model_id: ID модели видео (например, 'vidu:2@0')
        - duration: Длительность в секундах (2-10)

    ОПЦИОНАЛЬНЫЕ параметры (добавляются только если поддерживаются моделью):
        - aspect_ratio: Соотношение сторон ('16:9', '9:16', '1:1')
        - resolution: Разрешение видео ('1920x1080', '1280x720')
        - camera_movement: Движение камеры (для PixVerse)
        - seed: Seed для воспроизводимости

    Специфичные параметры провайдеров (через kwargs):
        ByteDance: camera_fixed
        Google: enhance_prompt, generate_audio
        MiniMax: prompt_optimizer
        PixVerse: style, effect, camera_movement, motion_mode, sound_effect_switch, sound_effect_content
        Vidu: movement_amplitude, bgm, style

    Returns:
        Dict с taskUUID и другими данными ответа
    """
    if not settings.RUNWARE_API_KEY:
        raise RunwareError("RUNWARE_API_KEY not configured")

    task_uuid = str(uuid.uuid4())
    provider = model_id.split(':')[0].lower() if ':' in model_id else ''

    # Определяем разрешение и длительность с учетом специфики моделей
    width = None
    height = None
    dur_value = duration

    # Модель-специфичная обработка
    if provider == 'bytedance':
        # ByteDance поддерживает только специфичные разрешения
        ar = str(aspect_ratio or "16:9").strip()
        bytedance_resolutions = {
            "16:9": [(1920, 1088), (1504, 640), (1248, 704), (1120, 832), (960, 416), (864, 480)],
            "9:16": [(1088, 1920), (640, 1504), (704, 1248), (832, 1120), (416, 960), (480, 864)],
            "1:1": [(1440, 1440), (960, 960), (640, 640)],
        }
        allowed = bytedance_resolutions.get(ar, bytedance_resolutions["16:9"])
        width, height = allowed[0]  # Берем самое высокое разрешение

        # ByteDance требует duration из списка: 3,4,5,6,7,8,9,10,11,12
        # Нормализуем к ближайшему допустимому значению
        allowed_durations = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        if duration not in allowed_durations:
            # Берем ближайшее допустимое значение
            dur_value = min(allowed_durations, key=lambda x: abs(x - duration))
        else:
            dur_value = float(duration)

    elif provider == 'google':
        # Google Veo поддерживает только 1280x720 или 720x1280
        ar = str(aspect_ratio or "16:9").strip()
        if ar == "9:16":
            width, height = 720, 1280
        else:
            width, height = 1280, 720

        # Google Veo 3.0 требует ровно 8 секунд
        if model_id == 'google:3@0':
            dur_value = 8.0

    elif provider == 'vidu':
        # Vidu 1.5 требует ровно 4 секунды
        if model_id == 'vidu:1@5':
            dur_value = 4.0
            # BGM требует РОВНО 4 секунды - если пользователь не запросил именно 4, убираем bgm
            # Важно: даже если мы корректируем duration до 4, но пользователь изначально указал другое значение,
            # API все равно может выдать ошибку. Поэтому проверяем оригинальный запрос пользователя.
            if kwargs.get('bgm') is not None:
                # Если bgm=False, то просто не добавляем его в провайдер настройки
                if not kwargs.get('bgm'):
                    kwargs.pop('bgm', None)
                # Если bgm=True, проверяем что оригинальный duration был ровно 4
                elif abs(float(duration) - 4.0) > 0.01:
                    logger.warning(f"BGM удален для Vidu 1.5: пользователь запросил {duration}s вместо точно 4s")
                    kwargs.pop('bgm', None)

        # Vidu 1.1 (Q1) - это I2V модель
        elif model_id == 'vidu:1@1':
            # Vidu 1.1 поддерживает только точные разрешения
            ar = str(aspect_ratio or "16:9").strip()
            if ar == "9:16":
                width, height = 1080, 1920
            elif ar == "1:1":
                width, height = 1080, 1080
            else:
                width, height = 1920, 1080

        # Vidu 2.0 - это I2V модель, не поддерживает T2V
        elif model_id == 'vidu:2@0':
            raise RunwareVideoError("Vidu 2.0 поддерживает только Image-to-Video генерацию. Используйте Vidu 1.1 или Vidu 1.5 для Text-to-Video.")

        # Стандартное разрешение для остальных Vidu моделей
        if not width or not height:
            ar = str(aspect_ratio or "16:9").strip()
            if ar == "9:16":
                width, height = 720, 1280
            elif ar == "1:1":
                width, height = 720, 720
            else:
                width, height = 1280, 720

    elif provider == 'klingai':
        # KlingAI 1.6 Pro - это только I2V модель
        if model_id == 'klingai:3@2':
            raise RunwareVideoError("KlingAI 1.6 Pro поддерживает только Image-to-Video генерацию. Пожалуйста, загрузите исходное изображение.")
        # Продолжаем обработку для других моделей KlingAI
        pass

    # Если width/height еще не установлены, используем стандартную логику
    if not width or not height:
        try:
            res_str = str(resolution or "").lower()
            if "x" in res_str:
                w_str, h_str = res_str.split("x", 1)
                width = int(w_str)
                height = int(h_str)
        except Exception:
            pass

        if not width or not height:
            ar = str(aspect_ratio or "16:9").strip()
            if ar == "9:16":
                width, height = 720, 1280
            elif ar == "1:1":
                width, height = 720, 720
            else:
                width, height = 1280, 720

    # Базовый payload
    payload = [{
        "taskType": "videoInference",
        "taskUUID": task_uuid,
        "positivePrompt": prompt,
        "model": model_id,
        "duration": float(dur_value),
        "width": int(width),
        "height": int(height),
        "outputType": "URL",
    }]

    # Добавляем seed если указан
    if seed:
        payload[0]["seed"] = int(seed) if str(seed).isdigit() else seed

    # Добавляем providerSettings на основе модели
    provider_settings = _build_provider_settings(model_id, camera_movement=camera_movement, **kwargs)
    if provider_settings:
        payload[0]["providerSettings"] = provider_settings

    logger.info(f"Отправка запроса на генерацию видео: model={model_id}, duration={duration}s")

    # ВАЖНО: Используем deliveryMethod="sync" чтобы получить результат СРАЗУ!
    # Точно как в submit_image_inference_sync()
    payload[0]["deliveryMethod"] = "sync"

    try:
        r = requests.post(
            settings.RUNWARE_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.RUNWARE_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=(15, 180),  # Connect timeout 15s, Read timeout 180s (3 минуты)
        )

        # Логируем статус код
        logger.info(f"Runware API status code: {r.status_code}")

        # Пытаемся получить JSON даже при ошибке
        try:
            data = r.json()
            logger.info(f"Ответ Runware API: {data}")
        except ValueError:
            logger.error(f"Не удалось распарсить JSON. Ответ: {r.text[:500]}")
            data = {}

        # Проверяем статус код
        if r.status_code == 401:
            raise RunwareVideoError("Неверный API ключ Runware")
        elif r.status_code == 402:
            raise RunwareVideoError("Недостаточно кредитов на аккаунте Runware")
        elif r.status_code == 400:
            # Извлекаем подробности из поля 'errors' если оно есть
            error_msg = data.get('error') or data.get('message')
            if not error_msg:
                errs = data.get('errors') or []
                if isinstance(errs, list) and errs:
                    e0 = errs[0] or {}
                    error_msg = e0.get('message') or e0.get('code') or 'Неверные параметры запроса'
                    param = e0.get('parameter')
                    if param:
                        # parameter может быть строкой или списком
                        if isinstance(param, list):
                            param = ",".join(map(str, param))
                        error_msg += f" (param: {param})"
                else:
                    error_msg = 'Неверные параметры запроса'
            raise RunwareVideoError(f"Ошибка параметров: {error_msg}")
        elif r.status_code >= 500:
            raise RunwareVideoError("Сервис Runware временно недоступен")

        r.raise_for_status()

        # Проверяем наличие ошибки в ответе
        if data.get('error'):
            raise RunwareVideoError(data['error'])
        if data.get('errors'):
            e0 = (data.get('errors') or [{}])[0] or {}
            msg = e0.get('message') or e0.get('code') or 'Неверные параметры запроса'
            param = e0.get('parameter')
            if param:
                if isinstance(param, list):
                    param = ",".join(map(str, param))
                msg += f" (param: {param})"
            raise RunwareVideoError(msg)

        # SYNC режим - извлекаем videoURL из ответа СРАЗУ!
        # Точно как в submit_image_inference_sync()
        video_url = _extract_video_url(data)
        if video_url:
            logger.info(f"Видео готово! URL: {video_url}")
            return video_url

        # Если URL не найден - ошибка
        raise RunwareVideoError(f"Sync submit returned no video URL: {str(data)[:500]}")

    except RunwareVideoError:
        raise
    except requests.exceptions.Timeout:
        logger.error("Timeout при генерации видео")
        raise RunwareVideoError("Превышено время ожидания ответа от сервиса")
    except requests.exceptions.ConnectionError:
        logger.error("Connection error при генерации видео")
        raise RunwareVideoError("Не удалось подключиться к сервису генерации")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при генерации видео: {e}")
        raise RunwareVideoError(f"Ошибка сети: {str(e)}")


def _upload_image_to_runware(image_bytes: bytes) -> str:
    """
    Загружает изображение в Runware через uploadImage API.
    Возвращает UUID загруженного изображения.

    Args:
        image_bytes: Байты изображения

    Returns:
        UUID загруженного изображения
    """
    if not settings.RUNWARE_API_KEY:
        raise RunwareError("RUNWARE_API_KEY not configured")

    # Определяем MIME тип
    if image_bytes[:2] == b'\xff\xd8':
        mime_type = 'image/jpeg'
    elif image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        mime_type = 'image/png'
    elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        mime_type = 'image/webp'
    else:
        mime_type = 'image/jpeg'

    # Конвертируем в data URI
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_uri = f"data:{mime_type};base64,{b64}"

    # Используем uploadImage API
    upload_payload = [{
        "taskType": "uploadImage",
        "taskUUID": str(uuid.uuid4()),
        "inputImage": data_uri,
    }]

    logger.info("Загрузка изображения в Runware через uploadImage API...")

    try:
        r = requests.post(
            settings.RUNWARE_API_URL,
            json=upload_payload,
            headers={
                "Authorization": f"Bearer {settings.RUNWARE_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=(15, 60),
        )

        logger.info(f"Upload response status: {r.status_code}")

        try:
            data = r.json()
            logger.info(f"Upload response: {data}")
        except:
            logger.error(f"Failed to parse JSON: {r.text[:500]}")
            raise

        r.raise_for_status()

        # Извлекаем imageUUID из ответа
        if isinstance(data, dict) and 'data' in data:
            items = data['data']
            if isinstance(items, list) and items:
                image_uuid = items[0].get('imageUUID')
                if image_uuid:
                    logger.info(f"Изображение загружено в Runware, UUID: {image_uuid}")
                    return image_uuid

        raise RunwareError(f"Не удалось получить UUID: {data}")

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        logger.error(f"Response: {r.text[:500]}")
        raise RunwareError(f"Ошибка загрузки: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise RunwareError(f"Ошибка загрузки: {str(e)}")


def generate_video_from_image(
    prompt: str,
    model_id: str,
    image_url: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    duration: int = 5,
    motion_strength: int = 45,
    aspect_ratio: str = "16:9",
    resolution: str = "1920x1080",
    camera_movement: Optional[str] = None,
    seed: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Генерация видео из изображения через Runware API (Image-to-Video).

    Можно передавать либо публичный URL (image_url), либо сам файл в виде bytes (image_bytes).
    Второй вариант работает в локальной разработке без внешнего URL.

    ОБЯЗАТЕЛЬНЫЕ параметры:
        - prompt: Текстовое описание желаемого движения/анимации
        - model_id: ID модели видео (например, 'klingai:2@1')
        - image_url или image_bytes: исходное изображение
        - duration: Длительность в секундах (2-10)

    ОПЦИОНАЛЬНЫЕ параметры:
        - seed: Seed для воспроизводимости

    Returns:
        Dict с taskUUID и другими данными ответа
    """
    if not settings.RUNWARE_API_KEY:
        raise RunwareError("RUNWARE_API_KEY not configured")

    task_uuid = str(uuid.uuid4())
    provider = model_id.split(':')[0].lower() if ':' in model_id else ''

    # Для I2V используем videoInference с frameImages
    # frameImages принимает: UUID, base64, или публичный URL
    frame_images: List[str] = []

    if image_bytes:
        # Загружаем изображение в Runware и получаем UUID
        try:
            image_uuid = _upload_image_to_runware(image_bytes)
            frame_images.append(image_uuid)
            logger.info(f"Используется UUID для I2V: {image_uuid}")
        except Exception as e:
            logger.error(f"Ошибка загрузки изображения: {e}")
            raise RunwareVideoError(f"Не удалось загрузить изображение: {str(e)}")
    elif image_url:
        # Проверяем - если это localhost URL, тоже не сработает
        is_local = 'localhost' in image_url or '127.0.0.1' in image_url
        if is_local:
            raise RunwareVideoError("Localhost URL не поддерживается. Требуется публичный URL или загрузка файла.")
        frame_images.append(str(image_url))
        logger.info(f"Используется публичный URL для I2V: {image_url}")
    else:
        raise RunwareVideoError("Image-to-Video: требуется image_url или image_bytes")

    # Определяем разрешение и duration для I2V моделей
    width = None
    height = None
    dur_value = duration

    if provider == 'vidu':
        # Vidu 1.1 (Q1) требует ТОЛЬКО 1920x1080 и duration=5.0
        if model_id == 'vidu:1@1':
            width, height = 1920, 1080
            dur_value = 5.0  # РОВНО 5 секунд как float!
        # Vidu 2.0 тоже для I2V
        elif model_id == 'vidu:2@0':
            width, height = 1920, 1080
    elif provider == 'klingai':
        # KlingAI для I2V
        width, height = 1920, 1080

    # Если не установлено, используем стандартное
    if not width or not height:
        ar = str(aspect_ratio or "16:9").strip()
        if ar == "9:16":
            width, height = 720, 1280
        elif ar == "1:1":
            width, height = 720, 720
        else:
            width, height = 1920, 1080

    payload = [{
        "taskType": "videoInference",
        "taskUUID": task_uuid,
        "positivePrompt": prompt,
        "model": model_id,
        "frameImages": frame_images,
        "duration": float(dur_value),  # Используем float для I2V
        "width": int(width),
        "height": int(height),
        "outputType": "URL",
    }]

    # Добавляем опциональные параметры только если они явно указаны
    if seed:
        payload[0]["seed"] = int(seed) if str(seed).isdigit() else seed

    # Добавляем providerSettings для I2V
    provider_settings = _build_provider_settings(model_id, camera_movement=camera_movement, **kwargs)
    if provider_settings:
        payload[0]["providerSettings"] = provider_settings

    # ВАЖНО: Используем deliveryMethod="sync" для получения результата СРАЗУ!
    payload[0]["deliveryMethod"] = "sync"

    logger.info(f"Отправка запроса на I2V: model={model_id}")
    logger.info(f"I2V Payload: {payload}")

    try:
        r = requests.post(
            settings.RUNWARE_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.RUNWARE_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=(15, 180),  # Connect 15s, Read 180s для синхронного ожидания
        )

        # Логируем статус код
        logger.info(f"Runware API I2V status code: {r.status_code}")

        # Пытаемся получить JSON даже при ошибке
        try:
            data = r.json()
            logger.info(f"Ответ Runware API (I2V): {data}")
        except ValueError:
            logger.error(f"Не удалось распарсить JSON. Ответ: {r.text[:500]}")
            data = {}

        # Проверяем наличие errors в ответе
        if data.get('errors'):
            error_details = data['errors'][0] if data['errors'] else {}
            error_msg = error_details.get('message', 'Неизвестная ошибка')
            logger.error(f"API вернул ошибку: {error_msg}")
            logger.error(f"Детали ошибки: {error_details}")

        # Проверяем статус код
        if r.status_code == 401:
            raise RunwareVideoError("Неверный API ключ Runware")
        elif r.status_code == 402:
            raise RunwareVideoError("Недостаточно кредитов на аккаунте Runware")
        elif r.status_code == 400:
            error_msg = data.get('error') or data.get('message')
            if not error_msg:
                errs = data.get('errors') or []
                if isinstance(errs, list) and errs:
                    e0 = errs[0] or {}
                    error_msg = e0.get('message') or e0.get('code') or 'Неверные параметры запроса'
                    param = e0.get('parameter')
                    if param:
                        if isinstance(param, list):
                            param = ",".join(map(str, param))
                        error_msg += f" (param: {param})"
                else:
                    error_msg = 'Неверные параметры запроса'
            raise RunwareVideoError(f"Ошибка параметров I2V: {error_msg}")
        elif r.status_code >= 500:
            raise RunwareVideoError("Сервис Runware временно недоступен")

        r.raise_for_status()

        # Проверяем наличие ошибки в ответе
        if data.get('error'):
            raise RunwareVideoError(data['error'])
        if data.get('errors'):
            e0 = (data.get('errors') or [{}])[0] or {}
            msg = e0.get('message') or e0.get('code') or 'Неверные параметры запроса'
            param = e0.get('parameter')
            if param:
                if isinstance(param, list):
                    param = ",".join(map(str, param))
                msg += f" (param: {param})"
            raise RunwareVideoError(f"Ошибка параметров I2V: {msg}")

        # SYNC режим - извлекаем videoURL из ответа СРАЗУ!
        video_url = _extract_video_url(data)
        if video_url:
            logger.info(f"I2V видео готово! URL: {video_url}")
            return video_url

        # Если URL не найден - ошибка
        raise RunwareVideoError(f"I2V sync submit returned no video URL: {str(data)[:500]}")

    except RunwareVideoError:
        raise
    except requests.exceptions.Timeout:
        logger.error("Timeout при генерации I2V")
        raise RunwareVideoError("Превышено время ожидания ответа от сервиса")
    except requests.exceptions.ConnectionError:
        logger.error("Connection error при генерации I2V")
        raise RunwareVideoError("Не удалось подключиться к сервису генерации")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при генерации I2V: {e}")
        raise RunwareVideoError(f"Ошибка сети: {str(e)}")


def check_video_status(task_uuid: str) -> Dict[str, Any]:
    """
    Проверка статуса генерации видео через Runware API.

    Отправляем пустой массив в API - Runware вернёт все последние результаты,
    среди которых может быть наша задача.

    Args:
        task_uuid: UUID задачи

    Returns:
        Dict со статусом и данными (или пустой если ещё в процессе)
    """
    if not settings.RUNWARE_API_KEY:
        raise RunwareError("RUNWARE_API_KEY not configured")

    try:
        # Отправляем пустой массив - получим последние результаты
        r = requests.post(
            settings.RUNWARE_API_URL,
            json=[],
            headers={
                "Authorization": f"Bearer {settings.RUNWARE_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        logger.info(f"Status check for {task_uuid}: HTTP {r.status_code}")

        if r.status_code == 401:
            raise RunwareError("Unauthorized - check API key")

        if r.status_code >= 500:
            logger.warning(f"Runware server error {r.status_code}")
            return {'data': [], 'status': 'processing'}

        # Парсим ответ
        try:
            data = r.json()
            logger.debug(f"Status response: {str(data)[:500]}")

            # Ищем наш taskUUID в массиве результатов
            if isinstance(data, dict) and 'data' in data:
                items = data['data']
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and item.get('taskUUID') == task_uuid:
                            logger.info(f"Найден результат для {task_uuid}: status={item.get('status')}")
                            return {'data': [item], 'status': item.get('status', 'processing')}

            # Результат ещё не готов
            return {'data': [], 'status': 'processing'}

        except ValueError as e:
            logger.error(f"JSON parse error: {e}, response: {r.text[:200]}")
            return {'data': [], 'status': 'processing'}

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout checking status for {task_uuid}")
        return {'data': [], 'status': 'processing'}
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request error checking status: {e}")
        return {'data': [], 'status': 'processing'}
    except Exception as e:
        logger.error(f"Unexpected error checking status: {e}", exc_info=True)
        return {'data': [], 'status': 'processing'}
