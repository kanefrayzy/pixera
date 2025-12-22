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
        html_parts.append('<div class="aspect-ratio-configurator space-y-3">')

        if not presets:
            html_parts.append('''
                <div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                    <div class="flex items-start gap-3">
                        <svg class="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                        </svg>
                        <div>
                            <h3 class="text-sm font-semibold text-yellow-800 dark:text-yellow-200">Нет пресетов соотношений сторон</h3>
                            <p class="text-xs text-yellow-700 dark:text-yellow-300 mt-1">
                                Выполните на сервере: <code class="px-1.5 py-0.5 bg-yellow-100 dark:bg-yellow-800 rounded text-xs font-mono">docker-compose exec web python populate_aspect_ratio_presets.py</code>
                            </p>
                        </div>
                    </div>
                </div>
            ''')
        else:
            for preset in presets:
                ratio_safe = preset.aspect_ratio.replace(':', '_').replace('.', '_')
                html_parts.append(f'''
                <div class="ar-ratio-group bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden shadow-sm" data-ratio="{preset.aspect_ratio}">
                    <div class="ar-ratio-header bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-4 py-3 flex items-center gap-3 cursor-pointer transition-all" onclick="this.parentElement.classList.toggle('active')">
                        <div class="ar-ratio-toggle w-5 h-5 border-2 border-white rounded flex-shrink-0 flex items-center justify-center"></div>
                        <div class="flex-1">
                            <div class="font-semibold text-sm">{preset.aspect_ratio} — {preset.name}</div>
                            <div class="text-xs opacity-90 mt-0.5">{preset.description or ''}</div>
                        </div>
                    </div>
                    <div class="ar-qualities hidden p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                ''')

                for quality_key, quality_label in qualities:
                    config_key = f"{preset.aspect_ratio}_{quality_key}"
                    existing = existing_configs.get(config_key, {})
                    width = existing.get('width', '')
                    height = existing.get('height', '')
                    checked = 'checked' if existing else ''
                    selected_class = 'selected' if existing else ''

                    html_parts.append(f'''
                        <div class="ar-quality-item flex flex-col gap-2 p-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg hover:border-blue-400 dark:hover:border-blue-500 transition-all {selected_class}" data-quality="{quality_key}">
                            <div class="flex items-center gap-2">
                                <input type="checkbox" class="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600" {checked}
                                       onchange="this.closest('.ar-quality-item').classList.toggle('selected', this.checked); updateConfigs()">
                                <label class="font-semibold text-sm text-gray-700 dark:text-gray-300">{quality_label}</label>
                            </div>
                            <div class="ar-dimensions hidden gap-2">
                                <div class="flex items-center gap-1.5 flex-1">
                                    <label class="text-xs text-gray-600 dark:text-gray-400 font-medium">Ширина:</label>
                                    <input type="number" value="{width}" placeholder="1920" min="64" max="8192" step="8"
                                           class="w-full px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
                                           data-ratio="{preset.aspect_ratio}" data-quality="{quality_key}" data-dimension="width"
                                           onchange="updateConfigs()">
                                </div>
                                <div class="flex items-center gap-1.5 flex-1">
                                    <label class="text-xs text-gray-600 dark:text-gray-400 font-medium">Высота:</label>
                                    <input type="number" value="{height}" placeholder="1080" min="64" max="8192" step="8"
                                           class="w-full px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
                                           data-ratio="{preset.aspect_ratio}" data-quality="{quality_key}" data-dimension="height"
                                           onchange="updateConfigs()">
                                </div>
                            </div>
                        </div>
                    ''')

                html_parts.append('</div></div>')

        # Статистика и стили
        html_parts.append('''
            <div class="mt-4 p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div class="flex items-center justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Выбрано конфигураций:</span>
                    <span class="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 text-xs font-medium rounded" id="config-count">0</span>
                </div>
            </div>

            <style>
                .ar-ratio-group.active .ar-qualities {
                    display: grid !important;
                }
                .ar-ratio-group.active .ar-ratio-toggle::after {
                    content: '✓';
                    color: #2563eb;
                    font-weight: bold;
                    font-size: 14px;
                }
                .ar-quality-item.selected {
                    background-color: #eff6ff !important;
                    border-color: #3b82f6 !important;
                }
                .dark .ar-quality-item.selected {
                    background-color: rgba(29, 78, 216, 0.2) !important;
                    border-color: #3b82f6 !important;
                }
                .ar-quality-item.selected .ar-dimensions {
                    display: flex !important;
                }
            </style>
        ''')

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

                // Обновляем счетчик
                const countBadge = document.getElementById('config-count');
                if (countBadge) {{
                    countBadge.textContent = configs.length;
                }}
            }}

            // Инициализация при загрузке
            document.addEventListener('DOMContentLoaded', function() {{
                updateConfigs();
            }});
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
