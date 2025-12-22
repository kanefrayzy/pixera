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

    def __init__(self, model_type='image', attrs=None):
        self.model_type = model_type
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        """Рендерит виджет напрямую без использования template"""
        from django.utils.html import format_html
        from django.utils.safestring import mark_safe
        import json

        # Получаем все соотношения сторон
        presets = list(AspectRatioPreset.objects.all().order_by('order', 'aspect_ratio'))

        # Парсим существующие конфигурации
        existing_configs = {}
        if value:
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

        qualities = [
            ('sd', 'SD'),
            ('hd', 'HD'),
            ('full_hd', 'Full HD'),
            ('2k', '2K'),
            ('4k', '4K'),
            ('8k', '8K'),
        ]

        # Генерируем HTML
        html_parts = []

        # Скрытое поле для хранения JSON данных
        html_parts.append(f'<input type="hidden" name="{name}" id="id_{name}" value="">')

        # Контейнер
        html_parts.append('''
        <div class="aspect-ratio-configurator" style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; margin: 15px 0;">
            <style>
                .ar-ratio-group { background: white; border: 1px solid #dee2e6; border-radius: 6px; overflow: hidden; margin-bottom: 15px; }
                .ar-ratio-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 16px; display: flex; align-items: center; gap: 12px; cursor: pointer; }
                .ar-ratio-toggle { width: 20px; height: 20px; border: 2px solid white; border-radius: 4px; cursor: pointer; flex-shrink: 0; }
                .ar-ratio-name { font-weight: 600; font-size: 14px; }
                .ar-ratio-desc { font-size: 12px; opacity: 0.9; margin-top: 2px; }
                .ar-qualities { padding: 16px; display: none; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
                .ar-ratio-group.active .ar-qualities { display: grid; }
                .ar-ratio-group.active .ar-ratio-toggle { background: white; }
                .ar-quality-item { display: flex; align-items: center; gap: 12px; padding: 12px; background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; }
                .ar-quality-item.selected { background: #e7f3ff; border-color: #0066cc; }
                .ar-quality-checkbox { width: 18px; height: 18px; border: 2px solid #6c757d; border-radius: 3px; cursor: pointer; flex-shrink: 0; }
                .ar-quality-label { font-weight: 600; font-size: 13px; color: #495057; min-width: 70px; }
                .ar-dimensions { display: none; flex: 1; gap: 8px; }
                .ar-quality-item.selected .ar-dimensions { display: flex; }
                .ar-dimension-input { display: flex; align-items: center; gap: 6px; flex: 1; }
                .ar-dimension-input label { font-size: 12px; color: #6c757d; font-weight: 500; }
                .ar-dimension-input input { width: 100%; padding: 6px 10px; border: 1px solid #ced4da; border-radius: 4px; font-size: 13px; }
            </style>
        ''')

        if not presets:
            html_parts.append('<div style="padding: 20px; background: #fff3cd; border: 1px solid #ffc107; color: #856404;">⚠️ Нет пресетов. Выполните: docker-compose exec web python populate_aspect_ratio_presets.py</div>')
        else:
            for preset in presets:
                ratio_safe = preset.aspect_ratio.replace(':', '_').replace('.', '_')
                html_parts.append(f'''
                <div class="ar-ratio-group" data-ratio="{preset.aspect_ratio}">
                    <div class="ar-ratio-header" onclick="this.parentElement.classList.toggle('active')">
                        <div class="ar-ratio-toggle"></div>
                        <div>
                            <div class="ar-ratio-name">{preset.aspect_ratio} — {preset.name}</div>
                            <div class="ar-ratio-desc">{preset.description or ''}</div>
                        </div>
                    </div>
                    <div class="ar-qualities">
                ''')

                for quality_key, quality_label in qualities:
                    config_key = f"{preset.aspect_ratio}_{quality_key}"
                    existing = existing_configs.get(config_key, {})
                    width = existing.get('width', '')
                    height = existing.get('height', '')
                    checked = 'checked' if existing else ''
                    selected_class = 'selected' if existing else ''

                    html_parts.append(f'''
                        <div class="ar-quality-item {selected_class}" data-quality="{quality_key}">
                            <input type="checkbox" class="ar-quality-checkbox" {checked}
                                   onchange="this.parentElement.classList.toggle('selected', this.checked); updateConfigs()">
                            <label class="ar-quality-label">{quality_label}</label>
                            <div class="ar-dimensions">
                                <div class="ar-dimension-input">
                                    <label>W:</label>
                                    <input type="number" value="{width}" placeholder="Width" min="64" max="8192" step="8"
                                           data-ratio="{preset.aspect_ratio}" data-quality="{quality_key}" data-dimension="width"
                                           onchange="updateConfigs()">
                                </div>
                                <div class="ar-dimension-input">
                                    <label>H:</label>
                                    <input type="number" value="{height}" placeholder="Height" min="64" max="8192" step="8"
                                           data-ratio="{preset.aspect_ratio}" data-quality="{quality_key}" data-dimension="height"
                                           onchange="updateConfigs()">
                                </div>
                            </div>
                        </div>
                    ''')

                html_parts.append('</div></div>')

        # JavaScript для сохранения данных
        html_parts.append(f'''
            <script>
            function updateConfigs() {{
                const configs = [];
                document.querySelectorAll('.ar-quality-item.selected').forEach(item => {{
                    const ratio = item.querySelector('[data-ratio]').dataset.ratio;
                    const quality = item.querySelector('[data-quality]').dataset.quality;
                    const width = item.querySelector('[data-dimension="width"]').value;
                    const height = item.querySelector('[data-dimension="height"]').value;

                    if (width && height) {{
                        configs.push({{
                            aspect_ratio: ratio,
                            quality: quality,
                            width: parseInt(width),
                            height: parseInt(height),
                            is_active: true
                        }});
                    }}
                }});

                document.getElementById('id_{name}').value = JSON.stringify(configs);
            }}

            // Инициализация при загрузке
            document.addEventListener('DOMContentLoaded', updateConfigs);
            </script>
        </div>
        ''')

        return mark_safe(''.join(html_parts))

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
