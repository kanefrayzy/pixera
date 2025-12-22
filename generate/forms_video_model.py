"""
Forms for Video Model Configuration
Provides comprehensive admin interface for managing video models
"""
from django import forms
from .models_video import VideoModelConfiguration, VALID_FPS
from .forms_aspect_ratio import AspectRatioConfigurationFormMixin


class VideoModelConfigurationForm(AspectRatioConfigurationFormMixin, forms.ModelForm):
    """
    Comprehensive form for video model configuration with organized fieldsets
    Includes aspect ratio + quality configuration
    """

    # Чекбоксы для типов референсов
    reference_frameImages = forms.BooleanField(
        label="Frame Images",
        required=False,
        help_text="Массив изображений для I2V (ByteDance, KlingAI, Vidu)"
    )
    reference_referenceImages = forms.BooleanField(
        label="Reference Images",
        required=False,
        help_text="Референсные изображения (Wan2.5-Preview)"
    )
    reference_audioInputs = forms.BooleanField(
        label="Audio Inputs",
        required=False,
        help_text="Аудио для V2V"
    )
    reference_controlNet = forms.BooleanField(
        label="ControlNet",
        required=False,
        help_text="Управление структурой"
    )

    class Meta:
        model = VideoModelConfiguration
        exclude = [
            # Старые поля разрешений (заменены на AspectRatioQualityConfig)
            'resolution_512x512', 'resolution_512x768', 'resolution_512x1024',
            'resolution_768x512', 'resolution_768x768', 'resolution_768x1024',
            'resolution_1024x512', 'resolution_1024x768', 'resolution_1024x1024',
            'resolution_1280x720', 'resolution_1920x1080', 'resolution_2560x1440',
            'resolution_3840x2160',
            # Старые поля соотношений сторон (заменены на AspectRatioQualityConfig)
            'aspect_ratio_1_1', 'aspect_ratio_4_3', 'aspect_ratio_3_2', 'aspect_ratio_5_4',
            'aspect_ratio_16_9', 'aspect_ratio_16_10', 'aspect_ratio_15_9', 'aspect_ratio_17_9',
            'aspect_ratio_1_85_1', 'aspect_ratio_2_00_1', 'aspect_ratio_2_20_1',
            'aspect_ratio_2_35_1', 'aspect_ratio_2_39_1', 'aspect_ratio_2_40_1',
            'aspect_ratio_18_9', 'aspect_ratio_19_9', 'aspect_ratio_20_9',
            'aspect_ratio_21_9', 'aspect_ratio_24_10', 'aspect_ratio_32_9',
            'aspect_ratio_9_16', 'aspect_ratio_3_4', 'aspect_ratio_2_3',
            'aspect_ratio_4_5', 'aspect_ratio_5_8', 'aspect_ratio_10_16',
            'aspect_ratio_9_19_5', 'aspect_ratio_9_20', 'aspect_ratio_9_21',
            'aspect_ratio_7_5', 'aspect_ratio_8_10',
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white',
                'placeholder': 'Описание модели...',
                'autocomplete': 'off'
            }),
            'admin_notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white',
                'placeholder': 'Внутренние заметки для администраторов...',
                'autocomplete': 'off'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white',
                'placeholder': 'Название модели',
                'autocomplete': 'off'
            }),
            'model_id': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white',
                'placeholder': 'runware:xxx@x',
                'autocomplete': 'off'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white',
                'placeholder': 'model-slug',
                'autocomplete': 'off'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add help text for key fields
        self.fields['model_id'].help_text = 'ID модели в формате Runware API (например: runware:100@1)'
        self.fields['token_cost'].help_text = 'Стоимость генерации в токенах'

        # Make slug optional (will be auto-generated)
        self.fields['slug'].required = False

        # FPS fields: use discrete select with allowed values only
        fps_choices = [(v, str(v)) for v in VALID_FPS]
        for fname in ('min_fps', 'max_fps', 'default_fps'):
            if fname in self.fields:
                # allow blank (None) as "—" for min/max/default
                self.fields[fname].widget = forms.Select(
                    choices=[('', '—')] + fps_choices
                )
                self.fields[fname].help_text = 'Допустимые значения FPS: 15, 24, 30, 60, 90, 120'

        # Group checkbox fields for better UX
        self._add_field_groups()

    def _add_field_groups(self):
        """Add CSS classes and attributes to group related fields"""

        # Duration checkboxes
        duration_fields = [
            'duration_2', 'duration_3', 'duration_4', 'duration_5', 'duration_6',
            'duration_8', 'duration_10', 'duration_12', 'duration_15', 'duration_20', 'duration_30'
        ]

        for field in duration_fields:
            if field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': 'rounded text-blue-600 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600'
                })

        # Camera movement checkboxes
        camera_fields = [
            'camera_static', 'camera_pan_left', 'camera_pan_right',
            'camera_tilt_up', 'camera_tilt_down', 'camera_zoom_in', 'camera_zoom_out',
            'camera_dolly_in', 'camera_dolly_out', 'camera_orbit_left', 'camera_orbit_right',
            'camera_crane_up', 'camera_crane_down'
        ]

        for field in camera_fields:
            if field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': 'rounded text-blue-600 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600'
                })

        # Quality checkboxes
        quality_fields = ['quality_low', 'quality_medium', 'quality_high', 'quality_ultra']

        for field in quality_fields:
            if field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': 'rounded text-blue-600 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600'
                })

        # Style checkboxes
        style_fields = [
            'style_realistic', 'style_anime', 'style_cartoon',
            'style_cinematic', 'style_artistic'
        ]

        for field in style_fields:
            if field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': 'rounded text-blue-600 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600'
                })

        # FPS checkboxes
        fps_fields = ['fps_15', 'fps_24', 'fps_30', 'fps_60', 'fps_90', 'fps_120']

        for field in fps_fields:
            if field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': 'rounded text-blue-600 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600'
                })

        # Output format checkboxes
        output_fields = ['supports_mp4', 'supports_webm', 'supports_gif']

        for field in output_fields:
            if field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': 'rounded text-blue-600 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600'
                })

        # Reference type checkboxes
        reference_fields = [
            'reference_frameImages', 'reference_referenceImages',
            'reference_audioInputs', 'reference_controlNet'
        ]

        for field in reference_fields:
            if field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': 'rounded text-blue-600 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600'
                })

        # Заполняем чекбоксы из JSON-поля supported_references
        if self.instance and self.instance.pk:
            supported = self.instance.supported_references or []
            self.fields['reference_frameImages'].initial = 'frameImages' in supported
            self.fields['reference_referenceImages'].initial = 'referenceImages' in supported
            self.fields['reference_audioInputs'].initial = 'audioInputs' in supported
            self.fields['reference_controlNet'].initial = 'controlNet' in supported

    def clean_model_id(self):
        """Validate model_id format"""
        model_id = self.cleaned_data.get('model_id', '').strip()
        if not model_id:
            raise forms.ValidationError('ID модели обязателен')

        # Basic format validation (provider:id@version or similar)
        if ':' not in model_id:
            raise forms.ValidationError('ID модели должен содержать ":" (например: runware:100@1)')

        return model_id

    def save(self, commit=True):
        """Save form and populate optional_fields from checkboxes"""
        instance = super().save(commit=False)

        # Build optional_fields configuration from form data
        optional_fields = {}

        # Get checkbox values from POST data
        if hasattr(self, 'data'):
            # Basic fields
            optional_fields['duration'] = 'duration_enabled' in self.data
            optional_fields['resolution'] = 'resolution_enabled' in self.data
            optional_fields['camera_movement'] = 'camera_movement_enabled' in self.data
            optional_fields['seed'] = 'seed_enabled' in self.data

            # I2V fields (source_image управляется режимом I2V/T2V автоматически)
            optional_fields['motion_strength'] = 'motion_strength_enabled' in self.data
            optional_fields['audio_inputs'] = 'audio_inputs_enabled' in self.data

            # Mode and prompt fields
            optional_fields['generation_mode'] = 'generation_mode_enabled' in self.data
            optional_fields['prompt'] = 'prompt_enabled' in self.data
            optional_fields['auto_translate'] = 'auto_translate_enabled' in self.data

            # Advanced fields
            optional_fields['aspect_ratio'] = 'aspect_ratio_enabled' in self.data
            optional_fields['reference_images'] = 'reference_images_enabled' in self.data
            optional_fields['prompt_generator'] = 'prompt_generator_enabled' in self.data

            # Advanced parameters (new)
            optional_fields['fps'] = 'fps_enabled' in self.data
            optional_fields['guidance_scale'] = 'guidance_scale_enabled' in self.data
            optional_fields['inference_steps'] = 'inference_steps_enabled' in self.data
            optional_fields['quality'] = 'quality_enabled' in self.data
            optional_fields['style'] = 'style_enabled' in self.data
            optional_fields['output_format'] = 'output_format_enabled' in self.data
            optional_fields['negative_prompt'] = 'negative_prompt_enabled' in self.data

            # Multiple videos support
            optional_fields['number_videos'] = 'number_videos_enabled' in self.data

        instance.optional_fields = optional_fields

        # Сохраняем поддерживаемые референсы из чекбоксов
        supported = []
        if self.cleaned_data.get('reference_frameImages'):
            supported.append('frameImages')
        if self.cleaned_data.get('reference_referenceImages'):
            supported.append('referenceImages')
        if self.cleaned_data.get('reference_audioInputs'):
            supported.append('audioInputs')
        if self.cleaned_data.get('reference_controlNet'):
            supported.append('controlNet')

        instance.supported_references = supported

        if commit:
            instance.save()

        return instance

    def clean(self):
        """Additional validation"""
        cleaned_data = super().clean()

        # Validate resolution limits (only if both values are provided and > 0)
        min_width = cleaned_data.get('min_width')
        max_width = cleaned_data.get('max_width')
        min_height = cleaned_data.get('min_height')
        max_height = cleaned_data.get('max_height')

        if min_width is not None and max_width is not None and min_width > 0 and max_width > 0:
            if min_width > max_width:
                raise forms.ValidationError('Минимальная ширина не может быть больше максимальной')

        if min_height is not None and max_height is not None and min_height > 0 and max_height > 0:
            if min_height > max_height:
                raise forms.ValidationError('Минимальная высота не может быть больше максимальной')

        # Validate duration limits
        min_duration = cleaned_data.get('min_duration')
        max_duration = cleaned_data.get('max_duration')

        if min_duration is not None and max_duration is not None and min_duration > 0 and max_duration > 0:
            if min_duration > max_duration:
                raise forms.ValidationError('Минимальная длительность не может быть больше максимальной')

        # Validate FPS limits
        min_fps = cleaned_data.get('min_fps')
        max_fps = cleaned_data.get('max_fps')

        if min_fps is not None and max_fps is not None and min_fps > 0 and max_fps > 0:
            if min_fps > max_fps:
                raise forms.ValidationError('Минимальный FPS не может быть больше максимального')

        # Restrict FPS to allowed discrete values
        allowed_fps = VALID_FPS
        default_fps = cleaned_data.get('default_fps')

        for label, value in (('Минимальный FPS', min_fps), ('Максимальный FPS', max_fps), ('FPS по умолчанию', default_fps)):
            if value is not None and value not in allowed_fps:
                raise forms.ValidationError(
                    f'{label} должен быть одним из: {", ".join(str(v) for v in allowed_fps)}'
                )

        # Ensure default FPS lies within [min_fps, max_fps] when all are set
        if default_fps is not None and min_fps is not None and max_fps is not None:
            if not (min_fps <= default_fps <= max_fps):
                raise forms.ValidationError('FPS по умолчанию должен находиться между минимальным и максимальным FPS')

        # Validate guidance scale limits
        min_guidance = cleaned_data.get('min_guidance_scale')
        max_guidance = cleaned_data.get('max_guidance_scale')

        if min_guidance is not None and max_guidance is not None and min_guidance > 0 and max_guidance > 0:
            if min_guidance > max_guidance:
                raise forms.ValidationError('Минимальный guidance scale не может быть больше максимального')

        # Validate inference steps limits
        min_steps = cleaned_data.get('min_inference_steps')
        max_steps = cleaned_data.get('max_inference_steps')

        if min_steps is not None and max_steps is not None and min_steps > 0 and max_steps > 0:
            if min_steps > max_steps:
                raise forms.ValidationError('Минимум шагов не может быть больше максимума')

        # Validate motion strength limits
        min_motion = cleaned_data.get('min_motion_strength')
        max_motion = cleaned_data.get('max_motion_strength')

        if min_motion is not None and max_motion is not None and min_motion >= 0 and max_motion >= 0:
            if min_motion > max_motion:
                raise forms.ValidationError('Минимальная сила движения не может быть больше максимальной')

        # Validate multiple videos limits
        min_videos = cleaned_data.get('min_videos')
        max_videos = cleaned_data.get('max_videos')

        if min_videos is not None and max_videos is not None and min_videos > 0 and max_videos > 0:
            if min_videos > max_videos:
                raise forms.ValidationError('Минимум видео не может быть больше максимума')
            if min_videos < 1:
                raise forms.ValidationError('Минимум видео должен быть не менее 1')
            if max_videos > 20:
                raise forms.ValidationError('Максимум видео не должен превышать 20')

        return cleaned_data


class VideoModelQuickEditForm(forms.ModelForm):
    """
    Quick edit form for common fields
    """

    class Meta:
        model = VideoModelConfiguration
        fields = [
            'name', 'model_id', 'category', 'token_cost',
            'is_active', 'is_beta', 'is_premium', 'order'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white'
            }),
            'model_id': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white'
            }),
        }
