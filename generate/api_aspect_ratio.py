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
        model_id: ID модели
        
    Returns:
        JSON со структурой:
        {
            "aspect_ratios": [
                {
                    "ratio": "16:9",
                    "qualities": [
                        {
                            "quality": "hd",
                            "quality_label": "HD",
                            "width": 1920,
                            "height": 1080,
                            "is_default": true
                        }
                    ]
                }
            ]
        }
    """
    configs = AspectRatioQualityConfig.objects.filter(
        model_type=model_type,
        model_id=model_id,
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
