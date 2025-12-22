"""
Form для создания/редактирования конфигураций соотношений сторон и качества
"""
from django import forms
from django.forms import formset_factory
from .models_aspect_ratio import AspectRatioQualityConfig, AspectRatioPreset


class AspectRatioQualityForm(forms.Form):
    """
    Форма для одной комбинации соотношение + качество
    """
    aspect_ratio = forms.CharField(max_length=20, widget=forms.HiddenInput())
    aspect_ratio_name = forms.CharField(max_length=100, required=False, widget=forms.HiddenInput())

    # Галочки для качеств
    quality_sd = forms.BooleanField(required=False, label='SD')
    quality_hd = forms.BooleanField(required=False, label='HD')
    quality_full_hd = forms.BooleanField(required=False, label='Full HD')
    quality_2k = forms.BooleanField(required=False, label='2K')
    quality_4k = forms.BooleanField(required=False, label='4K')
    quality_8k = forms.BooleanField(required=False, label='8K')

    # Поля для размеров по качествам
    width_sd = forms.IntegerField(required=False, min_value=64, max_value=8192)
    height_sd = forms.IntegerField(required=False, min_value=64, max_value=8192)

    width_hd = forms.IntegerField(required=False, min_value=64, max_value=8192)
    height_hd = forms.IntegerField(required=False, min_value=64, max_value=8192)

    width_full_hd = forms.IntegerField(required=False, min_value=64, max_value=8192)
    height_full_hd = forms.IntegerField(required=False, min_value=64, max_value=8192)

    width_2k = forms.IntegerField(required=False, min_value=64, max_value=8192)
    height_2k = forms.IntegerField(required=False, min_value=64, max_value=8192)

    width_4k = forms.IntegerField(required=False, min_value=64, max_value=8192)
    height_4k = forms.IntegerField(required=False, min_value=64, max_value=8192)

    width_8k = forms.IntegerField(required=False, min_value=64, max_value=8192)
    height_8k = forms.IntegerField(required=False, min_value=64, max_value=8192)


class AspectRatioConfigurationWidget(forms.Widget):
    """
    Кастомный виджет для красивого отображения матрицы соотношений × качеств
    """
    template_name = 'admin/aspect_ratio_configuration_widget.html'

    def __init__(self, model_type='image', attrs=None):
        self.model_type = model_type
        super().__init__(attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        # Получаем все соотношения сторон, отсортированные по порядку
        presets = list(AspectRatioPreset.objects.all().order_by('order', 'aspect_ratio'))

        # Парсим существующие конфигурации из value (JSON)
        existing_configs = {}
        if value:
            import json
            try:
                configs = json.loads(value)
                for config in configs:
                    key = f"{config['aspect_ratio']}_{config['quality']}"
                    existing_configs[key] = {
                        'width': config['width'],
                        'height': config['height'],
                        'is_active': config.get('is_active', True)
                    }
            except:
                pass

        context.update({
            'presets': presets,
            'existing_configs': existing_configs,
            'qualities': [
                ('sd', 'SD'),
                ('hd', 'HD'),
                ('full_hd', 'Full HD'),
                ('2k', '2K'),
                ('4k', '4K'),
                ('8k', '8K'),
            ],
            'widget_name': name,
            'model_type': self.model_type,
        })

        return context

    def value_from_datadict(self, data, files, name):
        """
        Собирает данные из POST запроса
        """
        import json
        configs = []

        # Ищем все поля вида aspect_ratio_RATIO_quality_QUALITY_enabled
        for key in data.keys():
            if key.startswith('aspect_ratio_') and '_quality_' in key and key.endswith('_enabled'):
                # Парсим ключ: aspect_ratio_1:1_quality_hd_enabled
                parts = key.replace('aspect_ratio_', '').replace('_enabled', '').split('_quality_')
                if len(parts) == 2:
                    aspect_ratio = parts[0].replace('_', ':')  # Восстанавливаем :
                    quality = parts[1]

                    # Получаем width и height
                    width_key = f'aspect_ratio_{parts[0]}_quality_{quality}_width'
                    height_key = f'aspect_ratio_{parts[0]}_quality_{quality}_height'

                    width = data.get(width_key)
                    height = data.get(height_key)

                    if width and height:
                        configs.append({
                            'aspect_ratio': aspect_ratio,
                            'quality': quality,
                            'width': int(width),
                            'height': int(height),
                            'is_active': True
                        })

        return json.dumps(configs) if configs else ''


class AspectRatioConfigurationFormMixin:
    """
    Mixin для добавления конфигурации соотношений в форму модели
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Определяем тип модели по Meta.model
        from .models_image import ImageModelConfiguration
        from .models_video import VideoModelConfiguration

        model_type = 'image' if self.Meta.model == ImageModelConfiguration else 'video'

        # Добавляем поле с кастомным виджетом
        self.fields['aspect_ratio_configurations'] = forms.CharField(
            required=False,
            widget=AspectRatioConfigurationWidget(model_type=model_type),
            label='Конфигурация соотношений сторон и качества',
            help_text='Выберите соотношения галочкой, затем укажите качества и размеры'
        )

        # Загружаем существующие конфигурации
        if self.instance.pk:
            configs = AspectRatioQualityConfig.objects.filter(
                model_type=model_type,
                model_id=self.instance.pk,
                is_active=True
            ).order_by('order')

            import json
            config_data = []
            for config in configs:
                config_data.append({
                    'aspect_ratio': config.aspect_ratio,
                    'quality': config.quality,
                    'width': config.width,
                    'height': config.height,
                    'is_active': config.is_active
                })

            if config_data:
                self.fields['aspect_ratio_configurations'].initial = json.dumps(config_data)

    def save(self, commit=True):
        instance = super().save(commit=commit)

        if commit:
            # Сохраняем конфигурации
            self._save_aspect_ratio_configurations(instance)

        return instance

    def _save_aspect_ratio_configurations(self, instance):
        """Сохраняет конфигурации соотношений"""
        import json

        from .models_image import ImageModelConfiguration
        from .models_video import VideoModelConfiguration

        model_type = 'image' if isinstance(instance, ImageModelConfiguration) else 'video'

        # Удаляем старые конфигурации
        AspectRatioQualityConfig.objects.filter(
            model_type=model_type,
            model_id=instance.pk
        ).delete()

        # Создаем новые
        configs_json = self.cleaned_data.get('aspect_ratio_configurations', '')
        if configs_json:
            try:
                configs = json.loads(configs_json)
                for i, config in enumerate(configs):
                    AspectRatioQualityConfig.objects.create(
                        model_type=model_type,
                        model_id=instance.pk,
                        aspect_ratio=config['aspect_ratio'],
                        quality=config['quality'],
                        width=config['width'],
                        height=config['height'],
                        is_active=config.get('is_active', True),
                        is_default=i == 0,  # Первая конфигурация - по умолчанию
                        order=i
                    )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error saving aspect ratio configurations: {e}")
