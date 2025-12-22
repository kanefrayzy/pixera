"""
API endpoints для получения конфигураций соотношений сторон
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models_aspect_ratio import AspectRatioQualityConfig


@require_http_methods(["GET"])
def get_model_aspect_ratio_configs(request, model_type, model_id):
    """
    Получить все доступные конфигурации соотношений сторон для модели
    
    Args:
        model_type: 'image' или 'video'
        model_id: ID модели (может быть числовой pk или строковый model_id вроде "runware:101@1")
        
    Returns:
        JSON со структурой
    """
    # Пробуем найти модель по model_id (строка) или по pk (число)
    try:
        # Сначала пробуем как числовой pk
        pk = int(model_id)
        configs = AspectRatioQualityConfig.objects.filter(
            model_type=model_type,
            model_id=pk,
            is_active=True
        ).order_by('order', 'aspect_ratio', 'quality')
    except (ValueError, TypeError):
        # Если не число, значит это строковый model_id - нужно найти pk модели
        if model_type == 'image':
            from .models_image import ImageModelConfiguration
            try:
                model = ImageModelConfiguration.objects.get(model_id=model_id, is_active=True)
                pk = model.pk
            except ImageModelConfiguration.DoesNotExist:
                return JsonResponse({'error': 'Model not found', 'aspect_ratios': [], 'count': 0}, status=404)
        else:  # video
            from .models_video import VideoModelConfiguration
            try:
                model = VideoModelConfiguration.objects.get(model_id=model_id, is_active=True)
                pk = model.pk
            except VideoModelConfiguration.DoesNotExist:
                return JsonResponse({'error': 'Model not found', 'aspect_ratios': [], 'count': 0}, status=404)
        
        configs = AspectRatioQualityConfig.objects.filter(
            model_type=model_type,
            model_id=pk,
            is_active=True
        ).order_by('order', 'aspect_ratio', 'quality')
    
    # Группируем по aspect_ratio
    result = {}
    quality_labels = {
        'sd': 'SD',
        'hd': 'HD',
        'full_hd': 'Full HD',
        '2k': '2K',
        '4k': '4K',
        '8k': '8K',
    }
    
    for config in configs:
        if config.aspect_ratio not in result:
            result[config.aspect_ratio] = []
        
        result[config.aspect_ratio].append({
            'quality': config.quality,
            'quality_label': quality_labels.get(config.quality, config.quality.upper()),
            'width': config.width,
            'height': config.height,
            'is_default': config.is_default
        })
    
    # Преобразуем в список
    aspect_ratios = [
        {
            'ratio': ratio,
            'qualities': qualities
        }
        for ratio, qualities in result.items()
    ]
    
    return JsonResponse({
        'aspect_ratios': aspect_ratios,
        'count': len(configs)
    })
