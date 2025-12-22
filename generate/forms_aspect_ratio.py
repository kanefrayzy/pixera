"""
Form для создания/редактирования конфигураций соотношений сторон и качества
"""
from django import forms
from django.forms import formset_factory
from .models_aspect_ratio import AspectRatioQualityConfig, AspectRatioPreset


def get_default_dimensions(aspect_ratio, quality):
    """
    Рассчитывает размеры по умолчанию на основе соотношения сторон и качества
    """
    # Базовые размеры для каждого качества (высота)
    quality_heights = {
        'sd': 480,      # SD: 480p
        'hd': 720,      # HD: 720p
        'full_hd': 1080, # Full HD: 1080p
        '2k': 1440,     # 2K: 1440p
        '4k': 2160,     # 4K: 2160p
        '8k': 4320,     # 8K: 4320p
    }

    height = quality_heights.get(quality, 1080)

    # Парсим соотношение сторон
    try:
        if ':' in aspect_ratio:
            w, h = map(float, aspect_ratio.split(':'))
            ratio = w / h
        else:
            ratio = float(aspect_ratio)
    except:
        ratio = 16 / 9  # По умолчанию 16:9

    width = int(height * ratio)

    # Округляем до кратного 8 для совместимости с большинством моделей
    width = (width // 8) * 8
    height = (height // 8) * 8

    return width, height


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
                
                # Проверяем есть ли хоть одно выбранное качество для этого соотношения
                has_selected = any(f"{preset.aspect_ratio}_{q[0]}" in existing_configs for q in qualities)
                selected_count = sum(1 for q in qualities if f"{preset.aspect_ratio}_{q[0]}" in existing_configs)
                
                html_parts.append(f'''
                <div class="ar-ratio-group {'active' if has_selected else ''} bg-white dark:bg-gray-800 border-2 {'border-green-500' if has_selected else 'border-gray-200 dark:border-gray-700'} rounded-lg overflow-hidden shadow-sm transition-all" data-ratio="{preset.aspect_ratio}">
                    <div class="ar-ratio-header {'bg-gradient-to-r from-green-600 to-emerald-600' if has_selected else 'bg-gradient-to-r from-gray-600 to-gray-700'} hover:from-blue-700 hover:to-purple-700 text-white px-4 py-3 flex items-center gap-3 cursor-pointer transition-all" onclick="this.parentElement.classList.toggle('active')">
                        <div class="ar-ratio-toggle w-5 h-5 border-2 border-white rounded flex-shrink-0 flex items-center justify-center">
                            {f'<svg class="w-4 h-4" fill="white" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>' if has_selected else ''}
                        </div>
                        <div class="flex-1">
                            <div class="font-semibold text-sm flex items-center gap-2">
                                {preset.aspect_ratio} — {preset.name}
                                {f'<span class="px-2 py-0.5 bg-white/20 rounded-full text-xs font-bold">{selected_count}</span>' if has_selected else ''}
                            </div>
                            <div class="text-xs opacity-90 mt-0.5">{preset.description or 'Кликните чтобы настроить качество'}</div>
                        </div>
                        <svg class="w-5 h-5 transition-transform ar-chevron" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                    <div class="ar-qualities {'block' if has_selected else 'hidden'} p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                ''')

                for quality_key, quality_label in qualities:
                    config_key = f"{preset.aspect_ratio}_{quality_key}"
                    existing = existing_configs.get(config_key, {})
                    width = existing.get('width', '')
                    height = existing.get('height', '')
                    is_checked = config_key in existing_configs
                    checked = 'checked' if is_checked else ''
                    selected_class = 'ar-quality-selected' if is_checked else ''

                    # Определяем размеры по умолчанию на основе соотношения сторон и качества
                    default_width, default_height = '', ''
                    if not width or not height:
                        default_width, default_height = get_default_dimensions(preset.aspect_ratio, quality_key)

                    display_width = width or default_width
                    display_height = height or default_height

                    html_parts.append(f'''
                        <div class="ar-quality-item {selected_class} flex flex-col gap-2 p-3 bg-gray-50 dark:bg-gray-700 border-2 {'border-green-500 bg-green-50 dark:bg-green-900/20' if is_checked else 'border-gray-200 dark:border-gray-600'} rounded-lg hover:border-blue-400 dark:hover:border-blue-500 transition-all" data-quality="{quality_key}">
                            <div class="flex items-center gap-2">
                                <input type="checkbox" class="w-5 h-5 rounded text-green-600 focus:ring-green-500 dark:bg-gray-700 dark:border-gray-600 cursor-pointer" {checked}
                                       onchange="handleQualityCheck(this, '{preset.aspect_ratio}', '{quality_key}'); updateConfigs()">
                                <label class="font-semibold text-sm {'text-green-700 dark:text-green-300' if is_checked else 'text-gray-700 dark:text-gray-300'} cursor-pointer" onclick="this.previousElementSibling.click()">{quality_label}</label>
                                {f'<svg class="w-4 h-4 text-green-600 ml-auto" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>' if is_checked else ''}
                            </div>
                            <div class="ar-dimensions {'flex' if is_checked else 'hidden'} flex-col gap-2">
                                <div class="flex items-center gap-1.5">
                                    <label class="text-xs text-gray-600 dark:text-gray-400 font-medium w-16">Ширина:</label>
                                    <input type="number" value="{display_width}" placeholder="{default_width}"
                                           class="flex-1 px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent font-mono"
                                           data-ratio="{preset.aspect_ratio}" data-quality="{quality_key}" data-dimension="width"
                                           onchange="updateConfigs()">
                                </div>
                                <div class="flex items-center gap-1.5">
                                    <label class="text-xs text-gray-600 dark:text-gray-400 font-medium w-16">Высота:</label>
                                    <input type="number" value="{display_height}" placeholder="{default_height}"
                                           class="flex-1 px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent font-mono"
                                           data-ratio="{preset.aspect_ratio}" data-quality="{quality_key}" data-dimension="height"
                                           onchange="updateConfigs()">
                                </div>
                            </div>
                        </div>
                    ''')

                html_parts.append('</div></div>')

        # Статистика и стили
        html_parts.append('''
            <div class="mt-4 p-3 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <div class="flex items-center justify-between text-sm">
                    <span class="text-gray-700 dark:text-gray-300 font-medium">Выбрано конфигураций:</span>
                    <span class="inline-flex items-center gap-1 px-3 py-1 bg-blue-600 text-white text-sm font-bold rounded-full shadow" id="config-count">0</span>
                </div>
            </div>

            <style>
                .ar-ratio-group.active .ar-qualities {
                    display: grid !important;
                }
                .ar-ratio-group.active .ar-chevron {
                    transform: rotate(180deg);
                }
                .ar-quality-item.ar-quality-selected {
                    background-color: #f0fdf4 !important;
                    border-color: #22c55e !important;
                }
                .dark .ar-quality-item.ar-quality-selected {
                    background-color: rgba(34, 197, 94, 0.15) !important;
                    border-color: #22c55e !important;
                }
            </style>
        ''')

        # JavaScript для сохранения данных
        html_parts.append(f'''
            <script>
            // Таблица размеров по умолчанию
            const DEFAULT_DIMENSIONS = {{
                'sd': 480,
                'hd': 720,
                'full_hd': 1080,
                '2k': 1440,
                '4k': 2160,
                '8k': 4320
            }};

            function calculateDimensions(aspectRatio, quality) {{
                const height = DEFAULT_DIMENSIONS[quality] || 1080;

                // Парсим соотношение сторон
                let ratio = 16 / 9;
                if (aspectRatio.includes(':')) {{
                    const [w, h] = aspectRatio.split(':').map(Number);
                    ratio = w / h;
                }} else {{
                    ratio = parseFloat(aspectRatio);
                }}

                let width = Math.round(height * ratio);

                // Округляем до кратного 8
                width = Math.floor(width / 8) * 8;
                const roundedHeight = Math.floor(height / 8) * 8;

                return {{ width, height: roundedHeight }};
            }}

            function handleQualityCheck(checkbox, aspectRatio, quality) {{
                const item = checkbox.closest('.ar-quality-item');
                const dimensionsDiv = item.querySelector('.ar-dimensions');
                
                if (checkbox.checked) {{
                    item.classList.add('ar-quality-selected');
                    dimensionsDiv.classList.remove('hidden');
                    dimensionsDiv.classList.add('flex');
                    
                    // Автоподстановка размеров
                    const widthInput = item.querySelector('[data-dimension="width"]');
                    const heightInput = item.querySelector('[data-dimension="height"]');

                    if (!widthInput.value || !heightInput.value) {{
                        const dimensions = calculateDimensions(aspectRatio, quality);
                        widthInput.value = dimensions.width;
                        heightInput.value = dimensions.height;
                    }}
                    
                    // Обновляем заголовок группы
                    updateRatioGroupHeader(aspectRatio);
                }} else {{
                    item.classList.remove('ar-quality-selected');
                    dimensionsDiv.classList.add('hidden');
                    dimensionsDiv.classList.remove('flex');
                    updateRatioGroupHeader(aspectRatio);
                }}
            }}
            
            function updateRatioGroupHeader(aspectRatio) {{
                const group = document.querySelector(`.ar-ratio-group[data-ratio="${{aspectRatio}}"]`);
                if (!group) return;
                
                const header = group.querySelector('.ar-ratio-header');
                const checkedCount = group.querySelectorAll('.ar-quality-item.ar-quality-selected').length;
                
                if (checkedCount > 0) {{
                    group.classList.add('active');
                    header.classList.remove('from-gray-600', 'to-gray-700');
                    header.classList.add('from-green-600', 'to-emerald-600');
                    group.style.borderColor = '#22c55e';
                }} else {{
                    header.classList.remove('from-green-600', 'to-emerald-600');
                    header.classList.add('from-gray-600', 'to-gray-700');
                    group.style.borderColor = '';
                }}
            }}

            function updateConfigs() {{
                const configs = [];
                document.querySelectorAll('.ar-quality-item.ar-quality-selected').forEach(item => {{
                    const ratio = item.querySelector('[data-ratio]').dataset.ratio;
                    const quality = item.querySelector('[data-quality]').dataset.quality;
                    let width = item.querySelector('[data-dimension="width"]').value;
                    let height = item.querySelector('[data-dimension="height"]').value;

                    // Валидация значений
                    width = parseInt(width) || 0;
                    height = parseInt(height) || 0;

                    // Проверяем диапазон
                    if (width < 64) width = 64;
                    if (width > 8192) width = 8192;
                    if (height < 64) height = 64;
                    if (height > 8192) height = 8192;

                    if (width && height) {{
                        configs.push({{
                            aspect_ratio: ratio,
                            quality: quality,
                            width: width,
                            height: height,
                            is_active: true
                        }});
                    }}
                }});

                const jsonValue = JSON.stringify(configs);
                document.getElementById('id_{name}').value = jsonValue;

                console.log('[AspectRatio Widget] updateConfigs called');
                console.log('[AspectRatio Widget] Found ' + configs.length + ' selected configs');
                console.log('[AspectRatio Widget] JSON value:', jsonValue);
                console.log('[AspectRatio Widget] Hidden field ID: id_{name}');
                console.log('[AspectRatio Widget] Hidden field exists:', !!document.getElementById('id_{name}'));

                // Обновляем счетчик
                const countBadge = document.getElementById('config-count');
                if (countBadge) {{
                    countBadge.textContent = configs.length;
                }}
            }}

            // Инициализация при загрузке
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('[AspectRatio Widget] DOMContentLoaded - initializing');
                updateConfigs();

                // Логирование перед отправкой формы
                const form = document.querySelector('form');
                if (form) {{
                    form.addEventListener('submit', function(e) {{
                        const hiddenField = document.getElementById('id_{name}');
                        console.log('[AspectRatio Widget] Form submitting');
                        console.log('[AspectRatio Widget] Hidden field value:', hiddenField ? hiddenField.value : 'FIELD NOT FOUND');
                        console.log('[AspectRatio Widget] Hidden field name:', hiddenField ? hiddenField.name : 'N/A');
                    }});
                }} else {{
                    console.warn('[AspectRatio Widget] Form not found for submit listener');
                }}
            }});
            </script>
        </div>
        ''')

        return mark_safe(''.join(html_parts))

    def value_from_datadict(self, data, files, name):
        """
        Собирает данные из POST запроса
        Теперь данные приходят из скрытого поля с JSON
        """
        import logging
        logger = logging.getLogger(__name__)

        # Получаем JSON из скрытого поля
        json_value = data.get(name, '')

        logger.info(f"[AspectRatioWidget] value_from_datadict called for field: {name}")
        logger.info(f"[AspectRatioWidget] Raw value from POST: {json_value[:500] if json_value else 'EMPTY'}")
        logger.info(f"[AspectRatioWidget] All POST keys: {list(data.keys())}")

        return json_value if json_value else ''


class AspectRatioConfigurationFormMixin:
    """
    Mixin для добавления конфигурации соотношений в форму модели
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[AspectRatioMixin] __init__ called, instance.pk: {self.instance.pk if hasattr(self, 'instance') else 'NO INSTANCE'}")

        # Определяем тип модели по Meta.model
        from .models_image import ImageModelConfiguration
        from .models_video import VideoModelConfiguration

        model_type = 'image' if self.Meta.model == ImageModelConfiguration else 'video'

        logger.info(f"[AspectRatioMixin] Model type: {model_type}")

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
                logger.info(f"[AspectRatioMixin] Loading {len(config_data)} existing configs")
                self.fields['aspect_ratio_configurations'].initial = json.dumps(config_data)
            else:
                logger.info(f"[AspectRatioMixin] No existing configs found")
        else:
            logger.info(f"[AspectRatioMixin] New instance, no configs to load")

    def save(self, commit=True):
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"[AspectRatioMixin] save() called, commit={commit}")
        logger.info(f"[AspectRatioMixin] cleaned_data keys: {list(self.cleaned_data.keys())}")
        logger.info(f"[AspectRatioMixin] aspect_ratio_configurations value: {self.cleaned_data.get('aspect_ratio_configurations', 'NOT FOUND')[:200]}")

        instance = super().save(commit=commit)

        logger.info(f"[AspectRatioMixin] Instance saved, pk={instance.pk}")

        # Сохраняем JSON в переменную экземпляра для использования в save_model админки
        self._pending_aspect_ratio_configs = self.cleaned_data.get('aspect_ratio_configurations', '')
        logger.info(f"[AspectRatioMixin] Stored configs in _pending_aspect_ratio_configs")

        # ТАКЖЕ сохраняем в thread-local для сигнала post_save
        configs_json = self.cleaned_data.get('aspect_ratio_configurations', '')
        if configs_json:
            from threading import local
            # Импортируем функцию сигнала чтобы получить доступ к её thread_locals
            from generate.admin import save_image_model_aspect_ratio_configs
            _thread_locals = getattr(save_image_model_aspect_ratio_configs, '_thread_locals', None)
            if _thread_locals is None:
                _thread_locals = local()
                save_image_model_aspect_ratio_configs._thread_locals = _thread_locals

            _thread_locals.pending_configs = configs_json
            logger.info(f"[AspectRatioMixin] Stored configs in thread-local for signal")
            print(f">>> [AspectRatioMixin] Stored configs in thread-local: {configs_json[:100]}")

        if commit:
            # Если commit=True, сохраняем сразу
            logger.info(f"[AspectRatioMixin] commit=True, calling _save_aspect_ratio_configurations immediately")
            self._save_aspect_ratio_configurations(instance)
        else:
            logger.warning(f"[AspectRatioMixin] commit=False, configs will be saved by signal")

        return instance

    def _save_aspect_ratio_configurations(self, instance):
        """Сохраняет конфигурации соотношений"""
        import json
        import logging

        logger = logging.getLogger(__name__)

        from .models_image import ImageModelConfiguration
        from .models_video import VideoModelConfiguration

        model_type = 'image' if isinstance(instance, ImageModelConfiguration) else 'video'

        logger.info(f"[AspectRatioMixin] Saving aspect ratio configurations for {model_type} model ID: {instance.pk}")

        # Получаем JSON из переменной или из cleaned_data
        configs_json = getattr(self, '_pending_aspect_ratio_configs', None) or self.cleaned_data.get('aspect_ratio_configurations', '')
        logger.info(f"[AspectRatioMixin] Configs JSON source: {'_pending_aspect_ratio_configs' if hasattr(self, '_pending_aspect_ratio_configs') else 'cleaned_data'}")
        logger.info(f"[AspectRatioMixin] Configs JSON from form: {configs_json[:200] if configs_json else 'EMPTY'}")

        # Удаляем старые конфигурации
        deleted_count = AspectRatioQualityConfig.objects.filter(
            model_type=model_type,
            model_id=instance.pk
        ).delete()

        logger.info(f"[AspectRatioMixin] Deleted {deleted_count[0] if deleted_count else 0} old configurations")

        if configs_json:
            try:
                configs = json.loads(configs_json)
                logger.info(f"[AspectRatioMixin] Parsed {len(configs)} configurations")

                for i, config in enumerate(configs):
                    created_config = AspectRatioQualityConfig.objects.create(
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
                    logger.info(f"[AspectRatioMixin] Created config: {created_config.aspect_ratio} {created_config.quality} ({created_config.width}x{created_config.height})")

                logger.info(f"[AspectRatioMixin] Successfully saved {len(configs)} configurations")
            except Exception as e:
                logger.error(f"[AspectRatioMixin] Error saving aspect ratio configurations: {e}", exc_info=True)
        else:
            logger.warning("[AspectRatioMixin] No configurations to save (empty JSON)")
