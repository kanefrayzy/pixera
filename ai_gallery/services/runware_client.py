import requests
import uuid
import logging
import base64
import os
from typing import Optional, Dict, Any, List
from django.conf import settings
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _get_api_key() -> str:
    """
    Динамически загружает API ключ из .env файла.
    Это позволяет обновлять ключ без перезапуска сервера.
    """
    load_dotenv(override=True)
    key = os.getenv("RUNWARE_API_KEY", "")
    if not key:
        raise RunwareError("RUNWARE_API_KEY не задан")
    return key

def runware_image_url(image_uuid: str) -> str:
    """
    Построить канонический CDN-URL Runware для загруженного изображения, как в Playground:
      https://im.runware.ai/image/ii/<UUID>.jpg
    """
    u = str(image_uuid).strip()
    return f"https://im.runware.ai/image/ii/{u}.jpg"


class RunwareError(Exception):
    """Базовое исключение для ошибок Runware API."""
    pass


class RunwareVideoError(RunwareError):
    """Исключение для ошибок генерации видео."""
    pass


def generate_image_via_rest(prompt: str, model_id: str | None, width=1024, height=1024, number_results=1):
    """Генерация изображения через Runware API."""
    api_key = _get_api_key()

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
            "Authorization": f"Bearer {api_key}",
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
    """Извлекает video URL из разнообразных форматов ответа Runware/провайдеров."""
    try:
        def pick_url(obj: dict) -> Optional[str]:
            if not isinstance(obj, dict):
                return None
            # flat keys first
            for k in ("videoURL", "videoUrl", "url", "outputURL", "resultURL", "referenceVideoURL", "movieURL"):
                v = obj.get(k)
                if isinstance(v, str) and v.startswith(("http://", "https://")):
                    return v
            # nested output/result
            out = obj.get("output") or obj.get("result")
            if isinstance(out, dict):
                for k in ("videoURL", "videoUrl", "url", "outputURL", "resultURL", "referenceVideoURL", "movieURL"):
                    v = out.get(k)
                    if isinstance(v, str) and v.startswith(("http://", "https://")):
                        return v
                vid = out.get("video")
                if isinstance(vid, dict):
                    for k in ("videoURL", "videoUrl", "url", "referenceVideoURL", "movieURL"):
                        v = vid.get(k)
                        if isinstance(v, str) and v.startswith(("http://", "https://")):
                            return v
            # arrays
            vids = obj.get("videos") or obj.get("outputs")
            if isinstance(vids, list):
                # prefer entries marked as video
                for it in vids:
                    if isinstance(it, dict):
                        t = (it.get("type") or "").lower()
                        if t in ("video", "mp4", "movie"):
                            for k in ("videoURL", "videoUrl", "url", "referenceVideoURL", "movieURL"):
                                v = it.get(k)
                                if isinstance(v, str) and v.startswith(("http://", "https://")):
                                    return v
                # fallback: first url-like
                for it in vids:
                    if isinstance(it, dict):
                        for k in ("videoURL", "videoUrl", "url", "referenceVideoURL", "movieURL"):
                            v = it.get(k)
                            if isinstance(v, str) and v.startswith(("http://", "https://")):
                                return v
            return None

        # top-level scan
        url = pick_url(data)
        if url:
            return url

        # common container: data: [...]
        arr = data.get("data")
        if isinstance(arr, list):
            for item in arr:
                if isinstance(item, dict):
                    url = pick_url(item)
                    if url:
                        return url
        elif isinstance(arr, dict):
            url = pick_url(arr)
            if url:
                return url

        return None
    except Exception:
        return None


def _sanitize_default_duration(obj):
    """
    Recursively remove any 'defaultDuration' keys from dicts/lists.
    Ensures payload never contains this parameter at any nesting level.
    """
    if isinstance(obj, dict):
        obj.pop("defaultDuration", None)
        for k, v in list(obj.items()):
            obj[k] = _sanitize_default_duration(v)
        return obj
    if isinstance(obj, list):
        return [_sanitize_default_duration(x) for x in obj]
    return obj


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
        bytedance_settings = {}
        if kwargs.get('camera_fixed') is not None:
            bytedance_settings['cameraFixed'] = kwargs.get('camera_fixed')
        # ВАЖНО: ByteDance поддерживает ТОЛЬКО cameraFixed в providerSettings
        # defaultDuration НЕ поддерживается!
        if bytedance_settings:
            provider_settings['bytedance'] = bytedance_settings

    # Google Veo
    elif provider == 'google':
        google_settings = {
            'enhancePrompt': kwargs.get('enhance_prompt', True),
        }
        # generateAudio только для Veo 3.0
        if model_id == 'google:3@0':
            google_settings['generateAudio'] = kwargs.get(
                'generate_audio', False)
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

    # OpenAI
    elif provider == 'openai':
        # OpenAI Sora 2 Pro: providerSettings не требуются
        pass

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
    api_key = _get_api_key()
    task_uuid = str(uuid.uuid4())
    provider = model_id.split(':')[0].lower() if ':' in model_id else ''
    # подготовим fallback как data URI на случай, если провайдер не принимает UUID в frameImages
    data_uri_fallback: Optional[str] = None

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
        # Выбираем разрешение: сначала пытаемся совпасть с указанным resolution, иначе ближайшее, иначе дефолт низкого уровня
        desired = None
        try:
            res_str = str(resolution or "").lower()
            if "x" in res_str:
                w_str, h_str = res_str.split("x", 1)
                desired = (int(w_str), int(h_str))
        except Exception:
            desired = None
        allowed = bytedance_resolutions.get(ar, bytedance_resolutions["16:9"])
        if desired and desired in allowed:
            width, height = desired
        elif desired:
            width, height = min(allowed, key=lambda wh: abs(
                wh[0] * wh[1] - desired[0] * desired[1]))
        else:
            default_map = {"16:9": (864, 480), "9:16": (
                480, 864), "1:1": (640, 640)}
            width, height = default_map.get(ar, (864, 480))
        # Allow explicit width/height from UI for ByteDance (T2V)
        try:
            w_ui = int(kwargs.get("width") or 0)
            h_ui = int(kwargs.get("height") or 0)
            if w_ui and h_ui:
                width, height = w_ui, h_ui
        except Exception:
            pass

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

    elif provider == 'openai':
        # OpenAI 3@2: recommended 4s, 30 FPS, 1280x720 or 720x1280
        ar = str(aspect_ratio or "16:9").strip()
        if ar == "9:16":
            width, height = 720, 1280
        elif ar == "1:1":
            width, height = 720, 720
        else:
            width, height = 1280, 720

        # Default to 4s if ambiguous and snap to allowed values (4, 8, 12)
        allowed_openai = [4.0, 8.0, 12.0]
        try:
            _inp = 4.0 if duration is None else float(duration)
        except Exception:
            _inp = 4.0
        dur_value = min(allowed_openai, key=lambda x: abs(x - _inp))

        # Ensure default FPS 30 if not provided by UI
        if kwargs.get('fps') is None:
            kwargs['fps'] = 30

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
                    logger.warning(
                        f"BGM удален для Vidu 1.5: пользователь запросил {duration}s вместо точно 4s")
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
            raise RunwareVideoError(
                "Vidu 2.0 поддерживает только Image-to-Video генерацию. Используйте Vidu 1.1 или Vidu 1.5 для Text-to-Video.")

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
            raise RunwareVideoError(
                "KlingAI 1.6 Pro поддерживает только Image-to-Video генерацию. Пожалуйста, загрузите исходное изображение.")
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
    # Подготовим payload (добавим подробный лог для отладки провайдеров)
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

    # If ByteDance, rebuild payload in the exact order expected by Runware Playground
    if provider == 'bytedance':
        # compute ordered fields
        try:
            _nr = int(kwargs.get("number_results",
                      kwargs.get("numberResults", 1)))
        except Exception:
            _nr = 1
        try:
            _outq = int(kwargs.get("output_quality",
                        kwargs.get("outputQuality", 85)))
        except Exception:
            _outq = 85
        _outfmt = str(kwargs.get("output_format", kwargs.get(
            "outputFormat", "mp4"))).lower() or "mp4"
        _seed_val = seed if seed is not None else kwargs.get("seed")
        _seed_int = None
        try:
            _seed_candidate = int(_seed_val) if _seed_val is not None and str(
                _seed_val).strip() != "" else None
            if _seed_candidate is not None and 1 <= _seed_candidate <= 9223372036854775807:
                _seed_int = _seed_candidate
        except Exception:
            _seed_int = None
        _include_cost = True if kwargs.get(
            "include_cost", kwargs.get("includeCost", True)) else False
        _camera_fixed = bool(kwargs.get("camera_fixed", False))

        # ВАЖНО: ByteDance требует duration как ЦЕЛОЕ ЧИСЛО из списка: 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
        # НЕ float, а int!
        _duration_int = int(dur_value)

        payload[0] = {
            "taskType": "videoInference",
            "duration": _duration_int,
            "fps": 24,
            "model": model_id,
            "outputFormat": _outfmt,
            "height": int(height),
            "width": int(width),
            "numberResults": _nr,
            "includeCost": _include_cost,
            "outputQuality": _outq,
            "providerSettings": {
                "bytedance": {
                    "cameraFixed": _camera_fixed
                }
            },
            "positivePrompt": prompt,
            "taskUUID": task_uuid,
        }
        if _seed_int is not None:
            payload[0]["seed"] = _seed_int
    else:
        # Для НЕ-ByteDance провайдеров: добавляем стандартные параметры
        # includeCost
        payload[0]["includeCost"] = True if kwargs.get(
            "include_cost", kwargs.get("includeCost", True)) else False

        # numberResults
        try:
            payload[0]["numberResults"] = int(kwargs.get(
                "number_results", kwargs.get("numberResults", 1)))
        except Exception:
            payload[0]["numberResults"] = 1

        # outputQuality
        try:
            payload[0]["outputQuality"] = int(kwargs.get(
                "output_quality", kwargs.get("outputQuality", 85)))
        except Exception:
            payload[0]["outputQuality"] = 85

        # outputFormat
        payload[0]["outputFormat"] = str(kwargs.get(
            "output_format", kwargs.get("outputFormat", "mp4"))).lower() or "mp4"

        # Добавляем seed если указан
        if seed:
            payload[0]["seed"] = int(seed) if str(seed).isdigit() else seed

        # FPS — верхнеуровневый параметр (по документации Runware)
        _fps = kwargs.get('fps')
        if _fps is not None and str(_fps).strip() != '':
            try:
                payload[0]["fps"] = int(_fps)
            except Exception:
                pass

        # Negative Prompt (если передан)
        neg = kwargs.get('negative_prompt')
        if neg:
            payload[0]["negativePrompt"] = str(neg)

        # Добавляем providerSettings на основе модели
        provider_settings = _build_provider_settings(
            model_id, camera_movement=camera_movement, **kwargs)
        if provider_settings:
            payload[0]["providerSettings"] = provider_settings

    logger.info(
        f"Отправка запроса на генерацию видео: model={model_id}, duration={duration}s")

    # ВАЖНО: Используем deliveryMethod="sync" чтобы получить результат СРАЗУ!
    # Точно как в submit_image_inference_sync()
    # НО ByteDance НЕ поддерживает sync режим - работает только async
    if provider != 'bytedance':
        payload[0]["deliveryMethod"] = "sync"
    else:
        payload[0]["deliveryMethod"] = "async"
        logger.info(
            "ByteDance: используется асинхронный режим (sync не поддерживается)")

    try:
        logger.info(
            f"T2V payload → model={model_id}, provider={provider}: {payload}")
        # Safety: ensure defaultDuration absent (top-level and nested) - НО НЕ ДЛЯ BYTEDANCE!
        # ByteDance требует defaultDuration в providerSettings
        if provider != 'bytedance':
            try:
                payload = _sanitize_default_duration(payload)
            except Exception:
                pass
        r = requests.post(
            settings.RUNWARE_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            # Connect timeout 15s, Read timeout 180s (3 минуты)
            timeout=(15, 180),
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
            raise RunwareVideoError(
                "Недостаточно кредитов на аккаунте Runware")
        elif r.status_code == 400:
            # Извлекаем подробности из поля 'errors' если оно есть
            error_msg = data.get('error') or data.get('message')
            if not error_msg:
                errs = data.get('errors') or []
                if isinstance(errs, list) and errs:
                    e0 = errs[0] or {}
                    error_msg = e0.get('message') or e0.get(
                        'code') or 'Неверные параметры запроса'
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
            # Fallback: try async delivery if provider sync endpoint is flaky
            logger.warning(
                "Runware 5xx on sync T2V submit (model=%s, provider=%s). Trying async fallback...", model_id, provider)
            try:
                payload_async = [dict(payload[0])]
                payload_async[0]["deliveryMethod"] = "async"
                # Post again as async
                r2 = requests.post(
                    settings.RUNWARE_API_URL,
                    json=payload_async,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=(15, 60),
                )
                try:
                    data2 = r2.json()
                except ValueError:
                    data2 = {}
                if r2.status_code in (200, 201) and isinstance(data2, dict):
                    task_data = data2.get('data', [])
                    if isinstance(task_data, list) and task_data and isinstance(task_data[0], dict):
                        tu = task_data[0].get('taskUUID')
                        if tu:
                            logger.info(
                                "Async fallback accepted, taskUUID=%s", tu)
                            return {'taskUUID': tu, 'async': True}
            except Exception as _e:
                logger.error("Async fallback failed: %s", _e)
            raise RunwareVideoError("Сервис Runware временно недоступен")

        r.raise_for_status()

        # Проверяем наличие ошибки в ответе
        if data.get('error'):
            raise RunwareVideoError(data['error'])
        if data.get('errors'):
            e0 = (data.get('errors') or [{}])[0] or {}
            msg = e0.get('message') or e0.get(
                'code') or 'Неверные параметры запроса'
            param = e0.get('parameter')
            if param:
                if isinstance(param, list):
                    param = ",".join(map(str, param))
                msg += f" (param: {param})"
            raise RunwareVideoError(msg)

        # Для ByteDance - асинхронный режим, возвращаем taskUUID
        if provider == 'bytedance':
            # Извлекаем taskUUID из ответа
            task_data = data.get('data', [])
            if task_data and isinstance(task_data, list) and task_data[0].get('taskUUID'):
                returned_uuid = task_data[0]['taskUUID']
                logger.info(f"ByteDance задача создана: {returned_uuid}")
                # Возвращаем dict с taskUUID для асинхронной обработки
                return {'taskUUID': returned_uuid, 'async': True}
            else:
                raise RunwareVideoError(
                    f"ByteDance не вернул taskUUID: {str(data)[:500]}")

        # SYNC режим для других провайдеров - извлекаем videoURL из ответа СРАЗУ!
        video_url = _extract_video_url(data)
        if video_url:
            logger.info(f"Видео готово! URL: {video_url}")
            return video_url

        # Если URL нет, но провайдер вернул taskUUID — переходим в polling без повторной отправки
        try:
            tu = None
            items = data.get('data', [])
            if isinstance(items, list) and items and isinstance(items[0], dict):
                tu = items[0].get('taskUUID') or items[0].get('taskUuid') or items[0].get('uuid')
            elif isinstance(items, dict):
                tu = items.get('taskUUID') or items.get('taskUuid') or items.get('uuid')
            if not tu and isinstance(data, dict):
                tu = data.get('taskUUID') or data.get('taskUuid') or data.get('uuid')
            if tu:
                logger.info(f"Sync response без URL, но с taskUUID={tu} → переключаемся на async polling")
                return {'taskUUID': tu, 'async': True}
        except Exception:
            pass

        # Если URL не найден — пробуем async fallback
        logger.warning(
            "No video URL returned in sync T2V response, trying async fallback...")
        try:
            payload_async = [dict(payload[0])]
            payload_async[0]["deliveryMethod"] = "async"
            r2 = requests.post(
                settings.RUNWARE_API_URL,
                json=payload_async,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=(15, 60),
            )
            try:
                data2 = r2.json()
            except ValueError:
                data2 = {}
            if r2.status_code in (200, 201) and isinstance(data2, dict):
                task_data = data2.get('data', [])
                if isinstance(task_data, list) and task_data and isinstance(task_data[0], dict):
                    tu = task_data[0].get('taskUUID')
                    if tu:
                        logger.info("Async fallback accepted, taskUUID=%s", tu)
                        return {'taskUUID': tu, 'async': True}
        except Exception as _e:
            logger.error("Async fallback failed: %s", _e)
        # Если и async не помог — ошибка
        raise RunwareVideoError(
            f"Sync submit returned no video URL: {str(data)[:500]}")

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
    Загружает изображение в Runware через imageUpload (или mediaStorage fallback).
    Возвращает UUID загруженного изображения.
    """
    api_key = _get_api_key()

    # MIME
    if image_bytes[:2] == b'\xff\xd8':
        mime_type = 'image/jpeg'
    elif image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        mime_type = 'image/png'
    elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        mime_type = 'image/webp'
    else:
        mime_type = 'image/jpeg'

    data_uri = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"

    def try_upload(task_type: str) -> Optional[dict]:
        # По документации для imageUpload поле называется 'image' (data URI | base64 | публичный URL).
        # Для mediaStorage требуется action='upload', и ряд реализаций принимает ключ 'file'.
        payload_item = {
            "taskType": task_type,          # 'imageUpload' (правильный) или fallback 'mediaStorage'
            "taskUUID": str(uuid.uuid4()),
            "deliveryMethod": "sync",
            "image": data_uri,              # корректное имя поля для imageUpload
        }
        if task_type == "mediaStorage":
            payload_item["action"] = "upload"
            payload_item["file"] = data_uri  # на некоторых аккаунтах требуется 'file'
        payload = [payload_item]
        logger.info(f"Загрузка изображения в Runware через taskType='{task_type}' ...")
        r = requests.post(
            settings.RUNWARE_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=(15, 60),
        )
        logger.info(f"Upload '{task_type}' status: {r.status_code}")
        try:
            j = r.json()
        except Exception:
            j = {}
        logger.info(f"Upload '{task_type}' response: {j}")
        if r.status_code == 400:
            # оставим возможность фоллбэка
            return {"ok": False, "data": j}
        r.raise_for_status()
        return {"ok": True, "data": j}

    # 1) Правильный taskType: imageUpload
    res = try_upload("imageUpload")
    if not res or not res.get("ok"):
        # 2) Фоллбек: mediaStorage (API перечисляет как валидный taskType)
        res2 = try_upload("mediaStorage")
        if not res2 or not res2.get("ok"):
            # отдаём подробности первой ошибки
            data_err = (res or {}).get("data") or (res2 or {}).get("data") or {}
            raise RunwareError(f"upload failed: {data_err}")
        data = res2["data"]
    else:
        data = res["data"]

    # Извлекаем UUID
    def _pick_uuid(d: dict) -> Optional[str]:
        for k in ("imageUUID", "uuid", "imageUuid", "assetUUID", "assetId", "fileUUID"):
            v = d.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        out = d.get("output") or {}
        if isinstance(out, dict):
            for k in ("imageUUID", "uuid", "imageUuid", "assetUUID", "assetId", "fileUUID"):
                v = out.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        # иногда API возвращает fileURL — вытащим uuid из URL
        file_url = d.get("fileURL") or d.get("url") or ((d.get("output") or {}).get("fileURL"))
        if isinstance(file_url, str):
            import re
            m = re.search(r"([0-9a-fA-F\-]{36})", file_url)
            if m:
                return m.group(1)
        return None

    if isinstance(data, dict) and "data" in data:
        items = data["data"]
        if isinstance(items, list) and items:
            cand = items[0] if isinstance(items[0], dict) else {}
            image_uuid = _pick_uuid(cand) or _pick_uuid(data)
            if not image_uuid and isinstance(cand, dict):
                reso = cand.get("result") or cand.get("output")
                if isinstance(reso, dict):
                    image_uuid = _pick_uuid(reso)
            if image_uuid:
                logger.info("Изображение загружено в Runware, UUID: %s", image_uuid)
                return image_uuid
        elif isinstance(items, dict):
            image_uuid = _pick_uuid(items) or _pick_uuid(data)
            if image_uuid:
                logger.info("Изображение загружено в Runware, UUID: %s", image_uuid)
                return image_uuid

    raise RunwareError(f"Не удалось получить UUID: {data}")


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
    api_key = _get_api_key()
    task_uuid = str(uuid.uuid4())
    provider = model_id.split(':')[0].lower() if ':' in model_id else ''

    # Для I2V используем videoInference с frameImages
    # frameImages у Runware должны быть строками: UUID предыдущей загрузки или публичный URL
    frame_images: List[str] = []

    if image_bytes:
        # Подготавливаем data URI сразу, чтобы иметь кросс‑провайдерный формат
        b = image_bytes
        try:
            if b[:2] == b'\xff\xd8':
                _mime = 'image/jpeg'
            elif b[:8] == b'\x89PNG\r\n\x1a\n':
                _mime = 'image/png'
            elif b[:4] == b'RIFF' and b[8:12] == b'WEBP':
                _mime = 'image/webp'
            else:
                _mime = 'image/jpeg'
            import base64 as _b64
            data_uri_fallback = f"data:{_mime};base64,{_b64.b64encode(b).decode('ascii')}"
        except Exception:
            data_uri_fallback = None
        try:
            # Всегда: сначала upload -> UUID (как в Face Retouch) для всех провайдеров, включая Vidu
            image_uuid = _upload_image_to_runware(b)
            frame_images.append(image_uuid)
            logger.info(f"I2V: bytes -> upload -> UUID={image_uuid}")
        except Exception as e:
            logger.error(f"Ошибка подготовки frameImages: {e}")
            raise RunwareVideoError(f"Не удалось подготовить исходное изображение: {str(e)}")
    elif image_url:
        # Проверяем - если это localhost URL, тоже не сработает
        is_local = 'localhost' in image_url or '127.0.0.1' in image_url
        if is_local:
            raise RunwareVideoError(
                "Localhost URL не поддерживается. Требуется публичный URL или загрузка файла.")
        # Всегда пытаемся конвертировать внешний URL в предыдущую загрузку (UUID),
        # чтобы поведение совпадало с Face Retouch и работало одинаково на локалке/проде.
        try:
            r = requests.get(image_url, timeout=20)
            if r.ok and r.content:
                try:
                    b = r.content
                    # Построим data URI
                    try:
                        if b[:2] == b'\xff\xd8':
                            _mime = 'image/jpeg'
                        elif b[:8] == b'\x89PNG\r\n\x1a\n':
                            _mime = 'image/png'
                        elif b[:4] == b'RIFF' and b[8:12] == b'WEBP':
                            _mime = 'image/webp'
                        else:
                            _mime = 'image/jpeg'
                        import base64 as _b64
                        data_uri_fallback = f"data:{_mime};base64,{_b64.b64encode(b).decode('ascii')}"
                    except Exception:
                        data_uri_fallback = None
                    # Всегда: внешний URL скачиваем, заливаем в Runware и используем UUID
                    image_uuid = _upload_image_to_runware(b)
                    frame_images.append(image_uuid)
                    logger.info(f"I2V: внешний URL загружен в Runware, UUID={image_uuid}")
                except Exception as up_e:
                    logger.warning(f"I2V: подготовка из URL не удалась, фоллбек на прямой URL: {up_e}")
                    frame_images.append(str(image_url))
            else:
                logger.warning(f"I2V: не удалось скачать внешний URL (status={getattr(r,'status_code',None)}), фоллбек на URL")
                frame_images.append(str(image_url))
        except Exception as dl_e:
            logger.warning(f"I2V: ошибка скачивания внешнего URL, фоллбек на прямой URL: {dl_e}")
            frame_images.append(str(image_url))
        logger.info(f"Используется источник для I2V: {'UUID' if len(frame_images) and len(frame_images[-1])==36 else 'URL'}")
    else:
        raise RunwareVideoError(
            "Image-to-Video: требуется image_url или image_bytes")

    # Определяем разрешение и duration для I2V моделей
    width = None
    height = None
    dur_value = duration

    if provider == 'bytedance':
        # Специфичные разрешения ByteDance для I2V
        ar = str(aspect_ratio or "16:9").strip()
        bytedance_resolutions = {
            "16:9": [(1920, 1088), (1504, 640), (1248, 704), (1120, 832), (960, 416), (864, 480)],
            "9:16": [(1088, 1920), (640, 1504), (704, 1248), (832, 1120), (416, 960), (480, 864)],
            "1:1": [(1440, 1440), (960, 960), (640, 640)],
        }
        # Выбираем разрешение для I2V аналогично T2V
        desired = None
        try:
            res_str = str(resolution or "").lower()
            if "x" in res_str:
                w_str, h_str = res_str.split("x", 1)
                desired = (int(w_str), int(h_str))
        except Exception:
            desired = None
        allowed = bytedance_resolutions.get(ar, bytedance_resolutions["16:9"])
        if desired and desired in allowed:
            width, height = desired
        elif desired:
            width, height = min(allowed, key=lambda wh: abs(
                wh[0] * wh[1] - desired[0] * desired[1]))
        else:
            default_map = {"16:9": (864, 480), "9:16": (
                480, 864), "1:1": (640, 640)}
            width, height = default_map.get(ar, (864, 480))
        # Allow explicit width/height from UI for ByteDance (I2V)
        try:
            w_ui = int(kwargs.get("width") or 0)
            h_ui = int(kwargs.get("height") or 0)
            if w_ui and h_ui:
                width, height = w_ui, h_ui
        except Exception:
            pass

        # Допустимые длительности ByteDance: 3..12
        allowed_durations = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        if duration not in allowed_durations:
            dur_value = min(allowed_durations, key=lambda x: abs(x - duration))
        else:
            dur_value = float(duration)

    elif provider == 'vidu':
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

    # Wan2.5-Preview (runware:201@1): разрешены только 5 и 10 секунд — нормализуем
    try:
        if str(model_id).lower() == 'runware:201@1':
            allowed = [5.0, 10.0]
            _inp = float(duration if duration is not None else 5.0)
            dur_value = min(allowed, key=lambda x: abs(x - _inp))
    except Exception:
        pass

    def _normalize_frame_images(items: List[str]) -> List[str]:
        out: List[str] = []
        import re
        uuid_re = re.compile(r"^[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}$")
        for s in (items or []):
            if not isinstance(s, str):
                continue
            v = s.strip()
            if not v:
                continue
            # Разрешаем форматы из документации: UUID v4, data URI, base64 (как строка), публичный URL
            if v.startswith("data:"):
                out.append(v)
                continue
            if v.startswith("http://") or v.startswith("https://"):
                out.append(v)
                continue
            if uuid_re.match(v):
                out.append(v)
                continue
            # Базовый хак: если это длинная base64-строка без префикса data:, завернём в data:image/jpeg;base64,
            b64_like = re.fullmatch(r"[A-Za-z0-9+/=\r\n]+", v)
            if b64_like and len(v) >= 128:
                out.append(f"data:image/jpeg;base64,{v}")
        return out

    # Подготовим payload (с логом для отладки I2V)
    images_list = _normalize_frame_images(frame_images)
    payload = [{
        "taskType": "videoInference",
        "taskUUID": task_uuid,
        "positivePrompt": prompt,
        "model": model_id,
        "duration": float(dur_value),  # Используем float для I2V
        "width": int(width),
        "height": int(height),
        "outputType": "URL",
    }]
    # Wan2.5-Preview (runware:201@1) требует referenceImages, а не frameImages
    mid = str(model_id).lower()
    if mid == "runware:201@1":
        payload[0]["referenceImages"] = images_list
    elif provider == 'bytedance':
        # ByteDance ожидает массив объектов { inputImage: <uuid|url|data> }
        payload[0]["frameImages"] = [{"inputImage": v} for v in images_list]
    elif provider == 'klingai':
        # KlingAI I2V: ожидает массив объектов { inputImage: <uuid|url|data> }.
        # Если у нас есть UUID, конвертируем его в канонический CDN-URL Runware, как в Playground.
        import re
        uuid_re2 = re.compile(r"^[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}$")
        converted: List[Dict[str, str]] = []
        for v in images_list:
            val = v
            if isinstance(v, str) and uuid_re2.match(v):
                # Превращаем UUID в https://im.runware.ai/image/ii/<UUID>.jpg
                try:
                    val = runware_image_url(v)
                except Exception:
                    val = v
            converted.append({"inputImage": val})
        payload[0]["frameImages"] = converted
    else:
        payload[0]["frameImages"] = images_list

    # Аудио-входы (URL/UUID/Data URI) — прокидываем как есть, если указаны
    audio_inputs = kwargs.get("audioInputs") or kwargs.get("audio_inputs")
    if audio_inputs:
        if isinstance(audio_inputs, str):
            ai = [audio_inputs.strip()] if audio_inputs.strip() else []
        elif isinstance(audio_inputs, list):
            ai = [str(x).strip() for x in audio_inputs if str(x).strip()]
        else:
            ai = []
        if ai:
            payload[0]["audioInputs"] = ai

    # ByteDance I2V requires integer seconds for duration
    if provider == 'bytedance':
        try:
            payload[0]["duration"] = int(dur_value)
        except Exception:
            pass

    # Дополнительные рекомендуемые параметры (с возможностью переопределения)
    payload[0]["includeCost"] = True if kwargs.get(
        "include_cost", True) else False
    try:
        payload[0]["numberResults"] = int(kwargs.get("number_results", 1))
    except Exception:
        payload[0]["numberResults"] = 1
    try:
        payload[0]["outputQuality"] = int(kwargs.get("output_quality", 85))
    except Exception:
        payload[0]["outputQuality"] = 85
    payload[0]["outputFormat"] = str(kwargs.get(
        "output_format", "mp4")).lower() or "mp4"

    # Добавляем опциональные параметры только если они явно указаны
    if seed:
        payload[0]["seed"] = int(seed) if str(seed).isdigit() else seed

    # FPS — верхнеуровневый параметр (по документации Runware)
    if provider == 'bytedance':
        payload[0]["fps"] = 24
    else:
        _fps = kwargs.get('fps')
        # Для KlingAI по умолчанию используем 24 FPS, если UI не задал другое значение
        if _fps is None and provider == 'klingai':
            _fps = 24
        if _fps is not None and str(_fps).strip() != '':
            try:
                payload[0]["fps"] = int(_fps)
            except Exception:
                pass

    # Negative Prompt (если передан)
    neg = kwargs.get('negative_prompt')
    if neg:
        payload[0]["negativePrompt"] = str(neg)


    # Добавляем providerSettings для I2V
    provider_settings = _build_provider_settings(
        model_id, camera_movement=camera_movement, **kwargs)
    if provider_settings:
        payload[0]["providerSettings"] = provider_settings

    # ВАЖНО: ByteDance требует async; Wan2.5‑Preview на 10 сек — тоже async (долгая генерация); остальные — sync
    payload[0]["deliveryMethod"] = "async" if (provider == 'bytedance' or (mid == "runware:201@1" and float(dur_value) >= 9.5)) else "sync"

    logger.info(f"Отправка запроса на I2V: model={model_id}")
    logger.info(f"I2V Payload: {payload}")

    try:
        logger.info(
            f"I2V payload → model={model_id}, provider={provider}: {payload}")
        # Safety: ensure defaultDuration absent (top-level and nested)
        try:
            payload = _sanitize_default_duration(payload)
        except Exception:
            pass
        r = requests.post(
            settings.RUNWARE_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            # Connect 15s, Read 180s для синхронного ожидания
            timeout=(15, 180),
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
            raise RunwareVideoError(
                "Недостаточно кредитов на аккаунте Runware")
        elif r.status_code == 400:
            # Если провайдер не принял UUID/URL, попробуем повторить с data URI (как это допускает документация)
            try:
                errs = data.get('errors') or []
                e0 = (errs[0] if isinstance(errs, list) and errs else {}) or {}
                code = (e0.get('code') or '').lower()
                param = (e0.get('parameter') or '')
            except Exception:
                code = ''
                param = ''
            if (code in ('invalidframeimages', 'invalidvalue') or 'frameimages' in str(param).lower()) and data_uri_fallback:
                try:
                    logger.warning("I2V: frameImages rejected (%s). Retrying with data URI fallback...", code or '400')
                    payload_retry = [dict(payload[0])]
                    payload_retry[0]["frameImages"] = _normalize_frame_images([data_uri_fallback])
                    r_retry = requests.post(
                        settings.RUNWARE_API_URL,
                        json=payload_retry,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        timeout=(15, 180),
                    )
                    logger.info(f"I2V retry with data URI status: {r_retry.status_code}")
                    try:
                        data_retry = r_retry.json()
                        logger.info(f"I2V retry response: {data_retry}")
                    except ValueError:
                        data_retry = {}
                    if r_retry.status_code in (200, 201):
                        # успех — продолжаем обработку как обычно
                        data = data_retry
                        r = r_retry  # важно: заменить исходный ответ, чтобы ниже не сработал блок поднятия ошибки
                    else:
                        # провал — вернём подробное сообщение ниже
                        r = r_retry
                        data = data_retry
                except Exception as _re:
                    logger.error(f"I2V retry with data URI failed: {_re}")
            # если после ретрая всё ещё 400 — сформируем человекочитаемую ошибку
            if r.status_code == 400:
                error_msg = data.get('error') or data.get('message')
                if not error_msg:
                    errs = data.get('errors') or []
                    if isinstance(errs, list) and errs:
                        e0 = errs[0] or {}
                        error_msg = e0.get('message') or e0.get(
                            'code') or 'Неверные параметры запроса'
                        param = e0.get('parameter')
                        if param:
                            if isinstance(param, list):
                                param = ",".join(map(str, param))
                            error_msg += f" (param: {param})"
                    else:
                        error_msg = 'Неверные параметры запроса'
                raise RunwareVideoError(f"Ошибка параметров I2V: {error_msg}")
        elif r.status_code >= 500:
            # Fallback: try async delivery for I2V
            logger.warning(
                "Runware 5xx on sync I2V submit (model=%s, provider=%s). Trying async fallback...", model_id, provider)
            try:
                payload_async = [dict(payload[0])]
                payload_async[0]["deliveryMethod"] = "async"
                r2 = requests.post(
                    settings.RUNWARE_API_URL,
                    json=payload_async,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=(15, 60),
                )
                try:
                    data2 = r2.json()
                except ValueError:
                    data2 = {}
                if r2.status_code in (200, 201) and isinstance(data2, dict):
                    task_data = data2.get('data', [])
                    if isinstance(task_data, list) and task_data and isinstance(task_data[0], dict):
                        tu = task_data[0].get('taskUUID')
                        if tu:
                            logger.info(
                                "Async I2V fallback accepted, taskUUID=%s", tu)
                            return {'taskUUID': tu, 'async': True}
            except Exception as _e:
                logger.error("Async I2V fallback failed: %s", _e)
            raise RunwareVideoError("Сервис Runware временно недоступен")

        r.raise_for_status()

        # Проверяем наличие ошибки в ответе
        if data.get('error'):
            raise RunwareVideoError(data['error'])
        if data.get('errors'):
            e0 = (data.get('errors') or [{}])[0] or {}
            msg = e0.get('message') or e0.get(
                'code') or 'Неверные параметры запроса'
            param = e0.get('parameter')
            if param:
                if isinstance(param, list):
                    param = ",".join(map(str, param))
                msg += f" (param: {param})"
            raise RunwareVideoError(f"Ошибка параметров I2V: {msg}")

        # Для ByteDance I2V — всегда async: возвращаем taskUUID, не ждём videoURL
        if provider == 'bytedance':
            try:
                task_data = data.get('data', [])
                tu = None
                if isinstance(task_data, list) and task_data and isinstance(task_data[0], dict):
                    tu = task_data[0].get('taskUUID')
                elif isinstance(task_data, dict):
                    tu = task_data.get('taskUUID')
                if not tu:
                    tu = data.get('taskUUID')
                if tu:
                    logger.info(f"ByteDance I2V задача создана: {tu}")
                    return {'taskUUID': tu, 'async': True}
            except Exception:
                # если не нашли taskUUID — пойдём ниже в общий разбор
                pass

        # SYNC режим - извлекаем videoURL из ответа СРАЗУ!
        video_url = _extract_video_url(data)
        if video_url:
            logger.info(f"I2V видео готово! URL: {video_url}")
            return video_url

        # Если URL не найден — пробуем async fallback
        logger.warning(
            "No video URL returned in sync I2V response, trying async fallback...")
        try:
            payload_async = [dict(payload[0])]
            payload_async[0]["deliveryMethod"] = "async"
            r2 = requests.post(
                settings.RUNWARE_API_URL,
                json=payload_async,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=(15, 60),
            )
            try:
                data2 = r2.json()
            except ValueError:
                data2 = {}
            if r2.status_code in (200, 201) and isinstance(data2, dict):
                task_data = data2.get('data', [])
                if isinstance(task_data, list) and task_data and isinstance(task_data[0], dict):
                    tu = task_data[0].get('taskUUID')
                    if tu:
                        logger.info(
                            "Async I2V fallback accepted, taskUUID=%s", tu)
                        return {'taskUUID': tu, 'async': True}
        except Exception as _e:
            logger.error("Async I2V fallback failed: %s", _e)
        raise RunwareVideoError(
            f"I2V sync submit returned no video URL: {str(data)[:500]}")

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

    Корректный способ: отправить задачу {"taskType":"getResponse","taskUUID": "..."}
    и получить статус именно нашей задачи, вместо эвристики с пустым массивом.

    Args:
        task_uuid: UUID задачи

    Returns:
        Dict с ключами:
          - data: [ { taskUUID, status, videoURL|url|videos, ... } ] или []
          - status: "success"/"succeeded"/"completed"/"processing"/"failed"/...
    """
    api_key = _get_api_key()

    payload = [{
        "taskType": "getResponse",
        "taskUUID": str(task_uuid),
    }]

    try:
        r = requests.post(
            settings.RUNWARE_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        logger.info(f"Status check(getResponse) for {task_uuid}: HTTP {r.status_code}")

        # 401 — неправильный ключ
        if r.status_code == 401:
            raise RunwareError("Unauthorized - check API key")

        # 400 у некоторых провайдеров (например, ByteDance) означает «пока нет результата»
        if r.status_code == 400:
            return {'data': [], 'status': 'processing'}

        # 5xx — временная ошибка сервера: считаем, что всё ещё обрабатывается
        if r.status_code >= 500:
            logger.warning(f"Runware server error {r.status_code} on getResponse")
            return {'data': [], 'status': 'processing'}

        # Парсим JSON
        try:
            data = r.json()
        except ValueError:
            logger.error(f"Status parse error: {r.text[:300]}")
            return {'data': [], 'status': 'processing'}

        # Нормализуем формат
        if isinstance(data, dict) and 'data' in data:
            items = data.get('data') or []
            if isinstance(items, list) and items:
                item = items[0] if isinstance(items[0], dict) else {}
                st = (item.get('status') or data.get('status') or 'processing')
                return {'data': items, 'status': st}
            return {'data': [], 'status': data.get('status', 'processing')}

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
