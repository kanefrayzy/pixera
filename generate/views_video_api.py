"""
API views для генерации видео с полной поддержкой асинхронной обработки через Redis.
"""

import logging
import requests
from datetime import timedelta
from typing import Dict, Any

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from .views_api import _hard_fingerprint, _guest_cookie_id, _ensure_session_key

from ai_gallery.services.runware_client import (
    generate_video_via_rest,
    generate_video_from_image,
    check_video_status,
    RunwareVideoError,
    RunwareError,
)
from dashboard.models import Wallet
from gallery.models import Image as GalleryImage
from generate.models import GenerationJob, VideoModel, FreeGrant, VideoPromptCategory
from generate.utils.image_processor import process_image_for_video, get_optimal_video_dimensions
from generate.services.translator import translate_prompt_if_needed

logger = logging.getLogger(__name__)

# Robust URL extractor for various provider payloads (ByteDance, etc.)
def _extract_video_url_from_payload(payload: dict) -> str | None:
    try:
        def pick_url(d: dict) -> str | None:
            # common keys
            for k in ("videoURL", "videoUrl", "url", "outputURL", "resultURL", "referenceVideoURL", "movieURL"):
                v = d.get(k)
                if isinstance(v, str) and v.startswith(("http://", "https://")):
                    return v

            # nested common shapes: output/result
            out = d.get("output")
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

            res = d.get("result")
            if isinstance(res, dict):
                for k in ("videoURL", "videoUrl", "url", "outputURL", "resultURL", "referenceVideoURL", "movieURL"):
                    v = res.get(k)
                    if isinstance(v, str) and v.startswith(("http://", "https://")):
                        return v
                vid = res.get("video")
                if isinstance(vid, dict):
                    for k in ("videoURL", "videoUrl", "url", "referenceVideoURL", "movieURL"):
                        v = vid.get(k)
                        if isinstance(v, str) and v.startswith(("http://", "https://")):
                            return v

            # arrays: outputs/videos
            outs = d.get("outputs") or d.get("videos")
            if isinstance(outs, list):
                # prefer entries explicitly marked as video
                for it in outs:
                    if isinstance(it, dict):
                        t = (it.get("type") or "").lower()
                        if t in ("video", "mp4", "movie"):
                            for k in ("videoURL", "videoUrl", "url", "referenceVideoURL", "movieURL"):
                                v = it.get(k)
                                if isinstance(v, str) and v.startswith(("http://", "https://")):
                                    return v
                # fallback: first url-like field
                for it in outs:
                    if isinstance(it, dict):
                        for k in ("videoURL", "videoUrl", "url", "referenceVideoURL", "movieURL"):
                            v = it.get(k)
                            if isinstance(v, str) and v.startswith(("http://", "https://")):
                                return v
            return None

        # try item-level first
        url = pick_url(payload)
        if url:
            return url

        # try nested lists: images, data
        imgs = payload.get("images")
        if isinstance(imgs, list) and imgs:
            for it in imgs:
                if isinstance(it, dict):
                    url = pick_url(it)
                    if url:
                        return url

        data_arr = payload.get("data")
        if isinstance(data_arr, list) and data_arr:
            for it in data_arr:
                if isinstance(it, dict):
                    url = pick_url(it)
                    if url:
                        return url

        return None
    except Exception:
        return None


@require_http_methods(["GET"])
def video_category_prompts_api(request, category_id):
    """API для получения промптов видео категории."""
    try:
        category = VideoPromptCategory.objects.get(id=category_id, is_active=True)
        prompts = category.video_prompts.filter(is_active=True).order_by('order', 'title')

        data = {
            'category': {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
            },
            'prompts': [
                {
                    'id': p.id,
                    'title': p.title,
                    'prompt_text': p.prompt_text,
                    'prompt_en': p.prompt_en,
                }
                for p in prompts
            ]
        }

        return JsonResponse(data)

    except VideoPromptCategory.DoesNotExist:
        return JsonResponse({'error': 'Категория не найдена'}, status=404)
    except Exception as e:
        logger.error(f"Ошибка при получении промптов видео: {e}")
        return JsonResponse({'error': 'Внутренняя ошибка'}, status=500)


@require_http_methods(["GET"])
def video_models_list(request):
    """Список доступных моделей видео из VideoModelConfiguration."""
    try:
        # Импортируем новую модель
        from generate.models_video import VideoModelConfiguration

        # Получаем активные модели, отсортированные по порядку
        models = VideoModelConfiguration.objects.filter(is_active=True).order_by('order', 'name')

        data = []
        for model in models:
            # Формируем данные модели для фронтенда
            model_data = {
                'id': model.id,
                'name': model.name,
                'model_id': model.runware_model_id,
                'category': model.get_category_for_js(),  # 't2v', 'i2v', 'anime'
                'category_display': model.get_category_display_name(),
                'description': model.description or '',
                'token_cost': model.token_cost,
                'max_duration': model.get_max_duration(),
                'max_resolution': model.get_max_resolution(),
                'image_url': model.image.url if model.image else None,

                # Параметры модели
                'available_resolutions': model.get_available_resolutions(),
                'available_aspect_ratios': model.get_available_aspect_ratios(),
                'available_durations': model.get_available_durations(),
                'available_camera_movements': model.get_available_camera_movements() if model.supports_camera_movement else [],

                # Поддержка функций
                'supports_image_to_video': model.supports_image_to_video,
                'supports_camera_movement': model.supports_camera_movement,
                'supports_motion_strength': model.supports_motion_strength,
                'supports_seed': model.supports_seed,
                'supports_negative_prompt': model.supports_negative_prompt,
                'supports_reference_images': model.supports_reference_images,
                'supports_fps': model.supports_fps,
                'supports_guidance_scale': model.supports_guidance_scale,
                'supports_inference_steps': model.supports_inference_steps,

                # Доступные дискретные FPS (ограничены VALID_FPS и min/max модели)
                'available_fps': model.get_available_fps() if model.supports_fps else [],

                # Диапазоны параметров
                'motion_strength_range': {
                    'min': model.min_motion_strength,
                    'max': model.max_motion_strength,
                    'default': model.default_motion_strength
                } if model.supports_motion_strength else None,

                'fps_range': {
                    'min': model.min_fps,
                    'max': model.max_fps,
                    'default': model.default_fps
                } if model.supports_fps else None,

                'guidance_scale_range': {
                    'min': model.min_guidance_scale,
                    'max': model.max_guidance_scale,
                    'default': model.default_guidance_scale
                } if model.supports_guidance_scale else None,

                'inference_steps_range': {
                    'min': model.min_inference_steps,
                    'max': model.max_inference_steps,
                    'default': model.default_inference_steps
                } if model.supports_inference_steps else None,

                # Multiple videos support
                'supports_multiple_videos': model.supports_multiple_videos,
                'multiple_videos_range': {
                    'min': model.min_videos or 1,
                    'max': model.max_videos or 4,
                    'default': model.default_videos or 1
                } if model.supports_multiple_videos else None,

                # Optional fields configuration
                'optional_fields': model.optional_fields or {},
            }

            data.append(model_data)

        return JsonResponse({
            'success': True,
            'models': data,
            'count': len(data)
        })

    except Exception as e:
        logger.error(f"Ошибка при получении списка моделей видео: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Не удалось загрузить модели видео'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@transaction.non_atomic_requests
def video_submit(request):
    """
    Отправка задачи на генерацию видео с полной поддержкой асинхронной обработки через Redis.

    POST параметры:
    - prompt: текстовое описание
    - video_model_id: ID модели видео (из БД)
    - generation_mode: 't2v' или 'i2v'
    - duration: длительность в секундах (2-10)
    - aspect_ratio: '16:9', '9:16', '1:1'
    - resolution: '1920x1080', '1280x720'
    - camera_movement: 'static', 'slow pan', 'orbit', 'dolly' (опционально)
    - seed: seed для воспроизводимости (опционально)

    Для I2V дополнительно:
    - source_image: файл изображения
    - motion_strength: сила движения (0-100)
    """
    try:
        # Получаем параметры
        prompt = request.POST.get('prompt', '').strip()
        video_model_id = request.POST.get('video_model_id')
        generation_mode = request.POST.get('generation_mode', 't2v')
        duration = int(request.POST.get('duration', 5))
        aspect_ratio = request.POST.get('aspect_ratio', '16:9')
        resolution = request.POST.get('resolution', '1920x1080')
        camera_movement = request.POST.get('camera_movement', '').strip() or None
        seed = request.POST.get('seed', '').strip() or None

        # Валидация
        if not prompt:
            return JsonResponse({
                'success': False,
                'error': 'Промпт обязателен'
            }, status=400)

        if not video_model_id:
            return JsonResponse({
                'success': False,
                'error': 'Модель видео не выбрана'
            }, status=400)

        # Переводим промпт на английский если нужно
        auto_translate_raw = request.POST.get('auto_translate', '1')
        auto_translate = str(auto_translate_raw).lower() in ('1', 'true', 'on', 'yes')
        if auto_translate:
            try:
                translated_prompt = translate_prompt_if_needed(prompt)
                original_prompt = prompt
                prompt = translated_prompt
            except Exception as e:
                logger.error(f"Ошибка перевода промпта для видео: {e}")
                original_prompt = prompt
        else:
            original_prompt = prompt

        # Получаем модель видео из VideoModelConfiguration
        try:
            from generate.models_video import VideoModelConfiguration
            video_model_config = VideoModelConfiguration.objects.get(id=video_model_id, is_active=True)
        except VideoModelConfiguration.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Модель видео не найдена'
            }, status=404)

        # Проверяем совместимость модели с выбранным режимом
        allowed_both = (str(video_model_config.model_id).lower() == 'bytedance:1@1')
        if generation_mode == 'i2v' and not video_model_config.supports_image_to_video and not allowed_both:
            return JsonResponse({
                'success': False,
                'error': 'Выбранная модель не поддерживает режим «Оживить фото (I2V)». Выберите модель из раздела I2V.'
            }, status=400)
        if generation_mode == 't2v' and video_model_config.supports_image_to_video and not allowed_both:
            return JsonResponse({
                'success': False,
                'error': 'Эта модель предназначена для Image‑to‑Video. Переключитесь в режим I2V или выберите модель T2V.'
            }, status=400)

        # Проверяем длительность
        if duration < 2 or duration > video_model_config.max_duration:
            return JsonResponse({
                'success': False,
                'error': f'Длительность должна быть от 2 до {video_model_config.max_duration} секунд'
            }, status=400)

        # Получаем или создаем соответствующую запись в VideoModel для совместимости
        try:
            video_model, created = VideoModel.objects.get_or_create(
                model_id=video_model_config.model_id,
                defaults={
                    'name': video_model_config.name,
                    'category': VideoModel.Category.I2V if video_model_config.supports_image_to_video else VideoModel.Category.T2V,
                    'max_duration': video_model_config.max_duration,
                    'token_cost': video_model_config.token_cost,
                    'is_active': True,
                }
            )
            if not created and video_model.token_cost != video_model_config.token_cost:
                # Обновляем стоимость если изменилась
                video_model.token_cost = video_model_config.token_cost
                video_model.max_duration = video_model_config.max_duration
                video_model.name = video_model_config.name
                video_model.save()
        except Exception as e:
            logger.error(f"Ошибка при создании/обновлении VideoModel: {e}")
            # Используем конфигурацию напрямую
            video_model = None

        # Проверяем баланс/токены
        user = request.user if request.user.is_authenticated else None
        token_cost = video_model.token_cost

        if not getattr(settings, 'ALLOW_FREE_LOCAL_VIDEO', False):
            if user and not user.is_staff:
                wallet = Wallet.objects.filter(user=user).first()
                if not wallet or wallet.balance < token_cost:
                    return JsonResponse({
                        'success': False,
                        'error': f'Недостаточно токенов. Требуется: {token_cost} TOK'
                    }, status=402)
            elif not user:
                from .security import ensure_guest_grant_with_security

                grant, device, error = ensure_guest_grant_with_security(request)

                if error or not grant:
                    return JsonResponse({
                        'success': False,
                        'error': error or 'Ошибка получения токенов'
                    }, status=403)

                if grant.left < token_cost:
                    return JsonResponse({
                        'success': False,
                        'error': f'Недостаточно токенов. Требуется: {token_cost} TOK'
                    }, status=402)
        else:
            logger.info("DEV MODE: ALLOW_FREE_LOCAL_VIDEO=True — пропускаем проверку баланса")

        # Создаем задачу в БД
        guest_session_key = ''
        guest_gid = ''
        guest_fp = ''
        if not request.user.is_authenticated:
            try:
                _ensure_session_key(request)
            except Exception:
                pass
            guest_session_key = request.session.session_key or ''
            guest_gid = request.COOKIES.get('gid', '')
            guest_fp = _hard_fingerprint(request)

        with transaction.atomic():
            job = GenerationJob.objects.create(
                user=user,
                generation_type='video',
                prompt=prompt,
                original_prompt=original_prompt,
                video_model=video_model,
                video_duration=duration,
                video_aspect_ratio=aspect_ratio,
                video_resolution=resolution,
                video_camera_movement=camera_movement or '',
                video_seed=seed or '',
                status=GenerationJob.Status.PENDING,
                tokens_spent=0,
                guest_session_key=guest_session_key,
                guest_gid=guest_gid,
                guest_fp=guest_fp,
            )

            # Save reference images if any and upload to Runware
            reference_uuids = []
            try:
                from .models import ReferenceImage
                from ai_gallery.services.runware_client import _upload_image_to_runware

                reference_images = request.FILES.getlist('reference_images')
                for ref_img in reference_images[:5]:  # Max 5 images
                    # Save to database
                    ref_obj = ReferenceImage.objects.create(
                        job=job,
                        image=ref_img
                    )

                    # Upload to Runware to get UUID
                    try:
                        ref_img.seek(0)  # Reset file pointer
                        image_data = ref_img.read()
                        ref_uuid = _upload_image_to_runware(image_data)
                        reference_uuids.append(ref_uuid)
                        logger.info(f"Uploaded reference image to Runware: {ref_uuid}")
                    except Exception as upload_err:
                        logger.error(f"Failed to upload reference image to Runware: {upload_err}")
            except Exception as e:
                logger.error(f"Failed to save reference images for video: {e}")

            # Save and upload audio files if any
            audio_uuids = []
            try:
                from ai_gallery.services.runware_client import _upload_audio_to_runware

                audio_files = request.FILES.getlist('audio_files')
                for audio_file in audio_files[:3]:  # Max 3 audio files
                    try:
                        audio_file.seek(0)  # Reset file pointer
                        audio_data = audio_file.read()
                        audio_uuid = _upload_audio_to_runware(audio_data, audio_file.name)
                        audio_uuids.append(audio_uuid)
                        logger.info(f"Uploaded audio file to Runware: {audio_uuid}")
                    except Exception as upload_err:
                        logger.error(f"Failed to upload audio file to Runware: {upload_err}")
            except Exception as e:
                logger.error(f"Failed to process audio files: {e}")

        # Для I2V обрабатываем изображение
        source_image_url = None
        image_bytes = None
        if generation_mode == 'i2v':
            if 'source_image' not in request.FILES:
                job.delete()
                return JsonResponse({
                    'success': False,
                    'error': 'Для I2V требуется исходное изображение'
                }, status=400)

            source_image = request.FILES['source_image']

            if source_image.size > 10 * 1024 * 1024:
                job.delete()
                return JsonResponse({
                    'success': False,
                    'error': 'Размер изображения не должен превышать 10MB'
                }, status=400)

            logger.info(f"Обработка изображения для I2V: {source_image.name}, размер: {source_image.size / 1024:.2f} KB")
            processed_image = process_image_for_video(source_image, max_size=(1024, 1024), quality=85)

            job.video_source_image = processed_image
            motion_strength = int(request.POST.get('motion_strength', 45))
            job.video_motion_strength = motion_strength
            job.save()

            source_image_url = request.build_absolute_uri(job.video_source_image.url)
            try:
                with default_storage.open(job.video_source_image.name, "rb") as f:
                    image_bytes = f.read()
            except Exception as e:
                logger.error(f"Не удалось прочитать файл исходного изображения: {e}")
            logger.info(f"Исходное изображение для I2V: url={source_image_url}, bytes={'yes' if image_bytes else 'no'}")

        # Получаем специфичные поля провайдера
        provider_fields_json = request.POST.get('provider_fields', '{}')
        try:
            import json
            provider_fields = json.loads(provider_fields_json)
        except Exception as e:
            logger.warning(f"Не удалось распарсить provider_fields: {e}")
            provider_fields = {}

        if isinstance(provider_fields, dict):
            if 'seed' in provider_fields:
                if not seed and str(provider_fields.get('seed')).strip() != '':
                    seed = provider_fields.get('seed')
                provider_fields.pop('seed', None)

            for k in ('duration', 'aspect_ratio', 'resolution', 'camera_movement', 'generation_mode',
                      'model_id', 'video_model_id'):
                provider_fields.pop(k, None)

        # Нормализация параметров для ByteDance
        try:
            provider_name = str(video_model.model_id).split(':')[0].lower()
        except Exception:
            provider_name = ''
        if provider_name == 'bytedance' and isinstance(provider_fields, dict):
            try:
                oq = int(provider_fields.get('outputQuality', 95))
            except Exception:
                oq = 95
            provider_fields['outputQuality'] = max(20, min(99, oq))

            provider_fields['fps'] = 24
            provider_fields['outputFormat'] = 'mp4'

            nr = provider_fields.get('numberResults') or provider_fields.get('number_results')
            try:
                nr = int(nr)
            except Exception:
                nr = 1
            provider_fields['numberResults'] = max(1, min(4, nr))
            provider_fields.pop('number_results', None)

            ar = (aspect_ratio or '16:9').strip()
            if ar == '9:16':
                w, h = 480, 864
            elif ar == '1:1':
                w, h = 720, 720
            else:
                w, h = 864, 480
            provider_fields['width'] = w
            provider_fields['height'] = h

        # Add reference UUIDs to provider_fields if available
        if reference_uuids:
            provider_fields['frameImages'] = reference_uuids
            logger.info(f"Added {len(reference_uuids)} reference UUIDs to provider_fields")

        # Add audio UUIDs to provider_fields if available
        if audio_uuids:
            provider_fields['audioInputs'] = audio_uuids
            logger.info(f"Added {len(audio_uuids)} audio UUIDs to provider_fields")

        # Проверяем режим работы: синхронный или асинхронный
        use_celery = getattr(settings, 'USE_CELERY', False)
        celery_always_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', True)

        if use_celery and not celery_always_eager:
            # Асинхронный режим через Celery/Redis
            logger.info(f"Запуск асинхронной генерации видео: job_id={job.id}, mode={generation_mode}, model={video_model.model_id}")

            from generate.tasks import process_video_generation_async
            process_video_generation_async.apply_async(
                args=[job.id, generation_mode, source_image_url, None, provider_fields],
                queue=getattr(settings, 'CELERY_QUEUE_SUBMIT', 'runware_submit')
            )

            with transaction.atomic():
                job.status = GenerationJob.Status.RUNNING
                job.save()

            return JsonResponse({
                'success': True,
                'job_id': job.id,
                'status': 'processing',
                'message': 'Видео генерируется асинхронно...'
            })
        else:
            # Синхронный режим (для разработки)
            logger.info(f"Запуск синхронной генерации видео: job_id={job.id}, mode={generation_mode}, model={video_model.model_id}")

            from generate.tasks import process_video_generation_async

            try:
                # Вызываем задачу напрямую (синхронно)
                process_video_generation_async(
                    job_id=job.id,
                    generation_mode=generation_mode,
                    source_image_url=source_image_url,
                    image_bytes=image_bytes,
                    provider_fields=provider_fields
                )

                # Перезагружаем job чтобы получить обновленные данные
                job.refresh_from_db()

                if job.status == GenerationJob.Status.DONE:
                    return JsonResponse({
                        'success': True,
                        'job_id': job.id,
                        'status': 'done',
                        'video_url': job.result_video_url,
                        'message': 'Видео успешно сгенерировано'
                    })
                elif job.status == GenerationJob.Status.FAILED:
                    return JsonResponse({
                        'success': False,
                        'error': job.error or 'Ошибка генерации видео'
                    }, status=500)
                else:
                    return JsonResponse({
                        'success': True,
                        'job_id': job.id,
                        'status': 'processing',
                        'message': 'Видео генерируется...'
                    })

            except Exception as e:
                logger.error(f"Ошибка синхронной генерации видео: {e}", exc_info=True)
                with transaction.atomic():
                    job.status = GenerationJob.Status.FAILED
                    job.error = str(e)
                    job.save()

                return JsonResponse({
                    'success': False,
                    'error': f'Ошибка генерации: {e}'
                }, status=500)

    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке видео: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Внутренняя ошибка сервера: {e}'
        }, status=500)


@require_http_methods(["GET"])
def video_status(request, job_id):
    """Проверка статуса генерации видео."""
    try:
        job = GenerationJob.objects.get(id=job_id, generation_type='video')

        # Проверяем права доступа
        owner_ok = False
        try:
            if job.user_id:
                owner_ok = (request.user.is_authenticated and request.user.id == job.user_id)
            else:
                try:
                    _ensure_session_key(request)
                except Exception:
                    pass
                sk = request.session.session_key or ''
                gid = request.COOKIES.get('gid', '')
                fp = _hard_fingerprint(request)
                owner_ok = (job.guest_session_key == sk) or (job.guest_gid == gid) or (job.guest_fp == fp)
        except Exception:
            owner_ok = False

        if not owner_ok:
            return JsonResponse({'success': False, 'error': 'not found'}, status=404)

        # Если уже готово
        if job.status == GenerationJob.Status.DONE:
            return JsonResponse({
                'success': True,
                'status': 'done',
                'video_url': job.result_video_url,
                'job_id': job.id,
                'cached_until': job.video_cached_until.isoformat() if job.video_cached_until else None
            })

        # Если ошибка
        if job.status == GenerationJob.Status.FAILED:
            return JsonResponse({
                'success': False,
                'status': 'failed',
                'error': job.error or 'Неизвестная ошибка'
            })

        # Всё ещё обрабатывается — но сначала попробуем «самовосстановление», если провайдер уже вернул video_url
        try:
            if job.status in (GenerationJob.Status.PENDING, GenerationJob.Status.RUNNING) and isinstance(getattr(job, 'provider_payload', None), dict):
                video_url = _extract_video_url_from_payload(job.provider_payload)
                if video_url:
                    logger.info(f"[video_status] Self-heal: job {job.id} has video_url in provider_payload, finalizing as DONE")
                    token_cost = job.video_model.token_cost if job.video_model else 20
                    with transaction.atomic():
                        # списываем токены только если ещё не списывали
                        if int(job.tokens_spent or 0) <= 0:
                            if job.user and not job.user.is_staff:
                                wallet = Wallet.objects.select_for_update().get(user=job.user)
                                wallet.balance -= token_cost
                                wallet.save()
                            elif not job.user:
                                grant = FreeGrant.objects.filter(
                                    Q(gid=job.guest_gid) | Q(fp=job.guest_fp),
                                    user__isnull=True
                                ).select_for_update().first()
                                if grant:
                                    grant.spend(token_cost)
                            job.tokens_spent = token_cost

                        if not job.result_video_url:
                            job.result_video_url = video_url
                        job.status = GenerationJob.Status.DONE
                        if not job.video_cached_until:
                            job.video_cached_until = timezone.now() + timedelta(hours=24)
                        job.save()

                    return JsonResponse({
                        'success': True,
                        'status': 'done',
                        'video_url': job.result_video_url,
                        'job_id': job.id,
                        'cached_until': job.video_cached_until.isoformat() if job.video_cached_until else None
                    })
        except Exception as e:
            logger.error(f"[video_status] Self-heal failed for job {job_id}: {e}", exc_info=True)

        # Попробуем опросить Runware напрямую, если есть provider_task_uuid (на случай, если Celery не отработал)
        try:
            if getattr(job, "provider_task_uuid", None):
                status_data = check_video_status(job.provider_task_uuid)
                raw = status_data or {}
                data_val = raw.get("data")
                item = None
                if isinstance(data_val, list) and data_val:
                    item = data_val[0]
                elif isinstance(data_val, dict):
                    item = data_val
                else:
                    item = raw

                status_val = (item or {}).get('status') or raw.get('status') or (item or {}).get('state')
                # вытащим video_url тем же способом, что и в self-heal
                video_url = _extract_video_url_from_payload(item or {}) or _extract_video_url_from_payload(raw or {})

                if str(status_val).lower() in {'completed', 'done', 'finished', 'success', 'succeeded'} and video_url:
                    logger.info(f"[video_status] Live poll: job {job.id} completed at provider, finalizing as DONE")
                    token_cost = job.video_model.token_cost if job.video_model else 20
                    with transaction.atomic():
                        if int(job.tokens_spent or 0) <= 0:
                            if job.user and not job.user.is_staff:
                                wallet = Wallet.objects.select_for_update().get(user=job.user)
                                wallet.balance -= token_cost
                                wallet.save()
                            elif not job.user:
                                grant = FreeGrant.objects.filter(
                                    Q(gid=job.guest_gid) | Q(fp=job.guest_fp),
                                    user__isnull=True
                                ).select_for_update().first()
                                if grant:
                                    grant.spend(token_cost)
                            job.tokens_spent = token_cost

                        if not job.result_video_url:
                            job.result_video_url = video_url
                        job.status = GenerationJob.Status.DONE
                        if not job.video_cached_until:
                            job.video_cached_until = timezone.now() + timedelta(hours=24)
                        job.save()

                    return JsonResponse({
                        'success': True,
                        'status': 'done',
                        'video_url': job.result_video_url,
                        'job_id': job.id,
                        'cached_until': job.video_cached_until.isoformat() if job.video_cached_until else None
                    })

                if str(status_val).lower() in {'failed', 'error'}:
                    logger.warning(f"[video_status] Live poll: job {job.id} failed at provider with status={status_val}")
                    job.status = GenerationJob.Status.FAILED
                    job.error = raw.get('error') or (item or {}).get('error') or 'Video generation failed at provider'
                    job.save()
                    return JsonResponse({
                        'success': False,
                        'status': 'failed',
                        'error': job.error
                    })
        except Exception as e:
            logger.error(f"[video_status] Live poll failed for job {job_id}: {e}", exc_info=True)

        progress = None
        try:
            if hasattr(job, 'provider_payload') and isinstance(job.provider_payload, dict):
                keys = ('progress', 'percentage', 'percent', 'pct')
                for k in keys:
                    if progress is not None:
                        break
                    progress = job.provider_payload.get(k)
                    if progress is None and isinstance(job.provider_payload.get('data'), dict):
                        progress = job.provider_payload.get('data', {}).get(k)

                if isinstance(progress, (float, int)):
                    progress = max(0, min(100, float(progress)))
                else:
                    progress = None
        except Exception:
            progress = None

        return JsonResponse({
            'success': True,
            'status': 'processing',
            'message': 'Видео генерируется...',
            'progress': progress
        })

    except GenerationJob.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Задача не найдена'
        }, status=404)
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }, status=500)


@require_http_methods(["GET"])
def video_last_pending(request):
    """
    Возвращает последний незавершенный (PENDING/RUNNING) видео-джоб для текущего пользователя
    или гостя (по session_key/gid/fp).
    """
    try:
        qs = GenerationJob.objects.filter(
            generation_type='video',
            status__in=[GenerationJob.Status.PENDING, GenerationJob.Status.RUNNING],
        )
        if request.user.is_authenticated:
            qs = qs.filter(user=request.user)
        else:
            try:
                _ensure_session_key(request)
            except Exception:
                pass
            sk = request.session.session_key or ''
            gid = request.COOKIES.get('gid', '')
            fp = _hard_fingerprint(request)
            qs = qs.filter(Q(guest_session_key=sk) | Q(guest_gid=gid) | Q(guest_fp=fp))

        job = qs.order_by('-created_at').first()
        if job:
            return JsonResponse({'success': True, 'job_id': job.id, 'status': 'found'})
        return JsonResponse({'success': True, 'job_id': None, 'status': 'none'})
    except Exception as e:
        logger.error(f"video_last_pending error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'internal'}, status=500)
