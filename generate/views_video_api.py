"""
API views для генерации видео.
"""

import logging
from datetime import timedelta
from typing import Dict, Any

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ai_gallery.services.runware_client import (
    generate_video_via_rest,
    generate_video_from_image,
    check_video_status,
    RunwareVideoError
)
from dashboard.models import Wallet
from gallery.models import Image as GalleryImage
from generate.models import GenerationJob, VideoModel, FreeGrant, VideoPromptCategory
from generate.utils.image_processor import process_image_for_video, get_optimal_video_dimensions
from generate.services.translator import translate_prompt_if_needed

logger = logging.getLogger(__name__)


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
    """Список доступных моделей видео."""
    try:
        models = VideoModel.objects.filter(is_active=True).order_by('category', 'order')

        data = []
        for model in models:
            data.append({
                'id': model.id,
                'name': model.name,
                'model_id': model.model_id,
                'category': model.category,
                'category_display': model.get_category_display(),
                'description': model.description,
                'token_cost': model.token_cost,
                'max_duration': model.max_duration,
                'max_resolution': model.max_resolution,
            })

        return JsonResponse({
            'success': True,
            'models': data,
            'count': len(data)
        })

    except Exception as e:
        logger.error(f"Ошибка при получении списка моделей видео: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Не удалось загрузить модели видео'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def video_submit(request):
    """
    Отправка задачи на генерацию видео.

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
        try:
            translated_prompt = translate_prompt_if_needed(prompt)
            # Сохраняем оригинальный промпт для отображения пользователю
            original_prompt = prompt
            prompt = translated_prompt
        except Exception as e:
            # В случае ошибки перевода, используем оригинальный промпт
            logger.error(f"Ошибка перевода промпта для видео: {e}")
            original_prompt = prompt

        # Получаем модель видео
        try:
            video_model = VideoModel.objects.get(id=video_model_id, is_active=True)
        except VideoModel.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Модель видео не найдена'
            }, status=404)

        # Проверяем длительность
        if duration < 2 or duration > video_model.max_duration:
            return JsonResponse({
                'success': False,
                'error': f'Длительность должна быть от 2 до {video_model.max_duration} секунд'
            }, status=400)

        # Проверяем баланс/токены
        user = request.user if request.user.is_authenticated else None
        token_cost = video_model.token_cost

        if user and not user.is_staff:
            wallet = Wallet.objects.filter(user=user).first()
            if not wallet or wallet.balance < token_cost:
                return JsonResponse({
                    'success': False,
                    'error': f'Недостаточно токенов. Требуется: {token_cost} TOK'
                }, status=402)
        elif not user:
            # Гостевой режим - проверяем FreeGrant
            fp = request.COOKIES.get(settings.FP_COOKIE_NAME, '')
            gid = request.COOKIES.get('gid', '')

            grant = FreeGrant.objects.filter(
                fp=fp if fp else None,
                gid=gid if gid else None,
                user__isnull=True
            ).first()

            if not grant or grant.left < token_cost:
                return JsonResponse({
                    'success': False,
                    'error': f'Недостаточно токенов. Требуется: {token_cost} TOK'
                }, status=402)

        # Создаем задачу в БД
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
            tokens_spent=0,  # Спишем после успешной генерации
        )

        # Для I2V обрабатываем изображение
        source_image_url = None
        if generation_mode == 'i2v':
            if 'source_image' not in request.FILES:
                job.delete()
                return JsonResponse({
                    'success': False,
                    'error': 'Для I2V требуется исходное изображение'
                }, status=400)

            source_image = request.FILES['source_image']

            # Проверяем размер (макс 10MB)
            if source_image.size > 10 * 1024 * 1024:
                job.delete()
                return JsonResponse({
                    'success': False,
                    'error': 'Размер изображения не должен превышать 10MB'
                }, status=400)

            # Обрабатываем и оптимизируем изображение
            logger.info(f"Обработка изображения для I2V: {source_image.name}, размер: {source_image.size / 1024:.2f} KB")
            processed_image = process_image_for_video(source_image, max_size=(1024, 1024), quality=85)

            # Сохраняем обработанное изображение
            job.video_source_image = processed_image
            motion_strength = int(request.POST.get('motion_strength', 45))
            job.video_motion_strength = motion_strength
            job.save()

            # Получаем URL и bytes изображения (для локальной разработки можно отправлять base64)
            source_image_url = request.build_absolute_uri(job.video_source_image.url)
            image_bytes = None
            try:
                with default_storage.open(job.video_source_image.name, "rb") as f:
                    image_bytes = f.read()
            except Exception as e:
                logger.error(f"Не удалось прочитать файл исходного изображения: {e}")
            logger.info(f"Исходное изображение для I2V: url={source_image_url}, bytes={'yes' if image_bytes else 'no'}")

        # Получаем специфичные поля провайдера из формы
        provider_fields_json = request.POST.get('provider_fields', '{}')
        try:
            import json
            provider_fields = json.loads(provider_fields_json)
        except Exception as e:
            logger.warning(f"Не удалось распарсить provider_fields: {e}")
            provider_fields = {}

        # Отправляем запрос в Runware
        try:
            logger.info(f"Начало генерации видео: mode={generation_mode}, model={video_model.model_id}, user={user}")
            logger.info(f"Provider fields: {provider_fields}")

            if generation_mode == 'i2v':
                # Для I2V: если URL локальный - используем base64, иначе URL
                is_local = source_image_url and ('localhost' in source_image_url or '127.0.0.1' in source_image_url)
                video_url = generate_video_from_image(
                    prompt=prompt,
                    model_id=video_model.model_id,
                    image_url=None if is_local else source_image_url,
                    image_bytes=image_bytes if is_local else None,
                    duration=duration,
                    seed=seed,
                    **provider_fields  # Передаем специфичные поля провайдера
                )
            else:
                # Для T2V передаем обязательные параметры + seed + специфичные поля провайдера
                video_url = generate_video_via_rest(
                    prompt=prompt,
                    model_id=video_model.model_id,
                    duration=duration,
                    seed=seed,
                    **provider_fields  # Передаем специфичные поля провайдера
                )

            # SYNC режим - видео ГОТОВО СРАЗУ!
            # Точно как генерация изображений
            logger.info(f"Видео готово моментально! URL: {video_url}")

            # Списываем токены
            if job.user and not job.user.is_staff:
                wallet = Wallet.objects.select_for_update().get(user=job.user)
                wallet.balance -= token_cost
                wallet.save()
            elif not job.user:
                # Гость - списываем из FreeGrant
                fp = request.COOKIES.get(settings.FP_COOKIE_NAME, '')
                gid = request.COOKIES.get('gid', '')
                grant = FreeGrant.objects.filter(
                    fp=fp if fp else None,
                    gid=gid if gid else None
                ).first()
                if grant:
                    grant.spend(token_cost)

            # Обновляем задачу
            job.result_video_url = video_url
            job.status = GenerationJob.Status.DONE
            job.tokens_spent = token_cost
            job.video_cached_until = timezone.now() + timedelta(hours=24)
            job.save()

            # Сохраняем в галерею
            gallery_image_id = None
            if job.user:
                try:
                    gallery_image = GalleryImage.objects.create(
                        user=job.user,
                        prompt=job.prompt,
                        image_url=video_url,
                        is_video=True,
                        is_public=False,
                        is_nsfw=False,
                    )
                    gallery_image_id = gallery_image.id
                    logger.info(f"Видео сохранено в галерею: ID={gallery_image.id}")
                except Exception as e:
                    logger.error(f"Ошибка при сохранении видео в галерею: {e}")

            # Возвращаем ГОТОВОЕ видео сразу!
            return JsonResponse({
                'success': True,
                'job_id': job.id,
                'status': 'done',
                'video_url': video_url,
                'gallery_id': gallery_image_id,
                'instant': True
            })

        except RunwareVideoError as e:
            job.status = GenerationJob.Status.FAILED
            job.error = str(e)
            job.save()

            logger.error(f"Ошибка Runware при генерации видео (job #{job.id}): {e}", exc_info=True)

            # Возвращаем конкретное сообщение об ошибке
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке видео: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }, status=500)


@require_http_methods(["GET"])
def video_status(request, job_id):
    """Проверка статуса генерации видео."""
    try:
        job = GenerationJob.objects.get(id=job_id, generation_type='video')

        # Проверяем права доступа
        user = request.user if request.user.is_authenticated else None
        if job.user and job.user != user:
            return JsonResponse({
                'success': False,
                'error': 'Доступ запрещен'
            }, status=403)

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

        # Проверяем статус в Runware
        if job.provider_task_uuid:
            try:
                status_data = check_video_status(job.provider_task_uuid)
                logger.info(f"Статус видео job #{job_id}: {status_data}")

                # Нормализация ответа провайдера (статус/URL/прогресс могут быть вложены)
                raw = status_data or {}
                data_val = raw.get('data')
                item = None
                if isinstance(data_val, list) and data_val:
                    item = data_val[0]
                elif isinstance(data_val, dict):
                    item = data_val
                else:
                    item = raw

                status_val = (item or {}).get('status') or raw.get('status') or (item or {}).get('state')
                video_url = (
                    (item or {}).get('videoURL')
                    or raw.get('videoURL')
                    or ((item or {}).get('output') or {}).get('videoURL')
                )

                logger.info(f"Извлечено: status={status_val}, video_url={video_url}")
                progress = (
                    (item or {}).get('progress')
                    or (item or {}).get('percentage')
                    or raw.get('progress')
                )
                try:
                    if isinstance(progress, (int, float)):
                        progress = max(0, min(100, float(progress)))
                    else:
                        progress = None
                except Exception:
                    progress = None

                # Успешно завершено
                if str(status_val).lower() in {'completed', 'done', 'finished'} and video_url:
                    # Списываем токены
                    token_cost = job.video_model.token_cost if job.video_model else 20

                    if job.user and not job.user.is_staff:
                        wallet = Wallet.objects.select_for_update().get(user=job.user)
                        wallet.balance -= token_cost
                        wallet.save()
                    elif not job.user:
                        # Гость - списываем из FreeGrant
                        fp = request.COOKIES.get(settings.FP_COOKIE_NAME, '')
                        gid = request.COOKIES.get('gid', '')
                        grant = FreeGrant.objects.filter(
                            fp=fp if fp else None,
                            gid=gid if gid else None
                        ).first()
                        if grant:
                            grant.spend(token_cost)

                    # Обновляем задачу
                    job.result_video_url = video_url
                    job.status = GenerationJob.Status.DONE
                    job.tokens_spent = token_cost
                    job.video_cached_until = timezone.now() + timedelta(hours=24)
                    job.save()

                    # Сохраняем видео в галерею для авторизованных пользователей
                    gallery_image_id = None
                    if job.user:
                        try:
                            gallery_image = GalleryImage.objects.create(
                                user=job.user,
                                prompt=job.prompt,
                                image_url=video_url,  # Сохраняем URL видео
                                is_video=True,  # Помечаем как видео
                                is_public=False,  # По умолчанию приватное
                                is_nsfw=False,
                            )
                            gallery_image_id = gallery_image.id
                            logger.info(f"Видео сохранено в галерею: ID={gallery_image.id}")
                        except Exception as e:
                            logger.error(f"Ошибка при сохранении видео в галерею: {e}")

                    return JsonResponse({
                        'success': True,
                        'status': 'done',
                        'video_url': video_url,
                        'job_id': job.id,
                        'gallery_id': gallery_image_id,
                        'cached_until': job.video_cached_until.isoformat()
                    })

                # Провал
                if str(status_val).lower() in {'failed', 'error'}:
                    job.status = GenerationJob.Status.FAILED
                    job.error = raw.get('error') or (item or {}).get('error') or 'Ошибка генерации'
                    job.save()
                    return JsonResponse({
                        'success': False,
                        'status': 'failed',
                        'error': job.error
                    })

                # Иначе — всё ещё в процессе: вернём прогресс, чтобы фронт показывал реальный процент
                return JsonResponse({
                    'success': True,
                    'status': 'processing',
                    'message': 'Видео генерируется...',
                    'progress': progress
                })

            except Exception as e:
                logger.error(f"Ошибка при проверке статуса видео: {e}")

        # Все еще в процессе — пробуем пробросить прогресс провайдера (если он есть)
        progress = None
        try:
            # Для разных провайдеров поле может называться по-разному
            # Пробуем несколько ключей в корне и внутри data
            keys = ('progress', 'percentage', 'percent', 'pct')
            for k in keys:
                if progress is not None:
                    break
                if 'status_data' in locals() and isinstance(status_data, dict):
                    progress = status_data.get(k)
                    if progress is None and isinstance(status_data.get('data'), dict):
                        progress = status_data.get('data', {}).get(k)
            # Нормализуем в 0..100
            if isinstance(progress, float) or isinstance(progress, int):
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
