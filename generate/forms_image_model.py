"""
Forms for Image Model Configuration
Provides admin interface for managing image generation models
"""
from django import forms
from .models_image import ImageModelConfiguration


class ImageModelConfigurationForm(forms.ModelForm):
    """
    Form for image model configuration with organized fieldsets
    """

    class Meta:
        model = ImageModelConfiguration
        fields = '__all__'
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
            'provider': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white',
                'placeholder': 'Runware',
                'autocomplete': 'off'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add help text for key fields
        self.fields['model_id'].help_text = 'ID модели в формате Runware API (например: runware:101@1)'
        self.fields['token_cost'].help_text = 'Стоимость генерации в токенах'
        self.fields['supports_custom_resolution'].help_text = 'Разрешить пользователям вводить произвольное разрешение'

        # Make slug optional (will be auto-generated)
        self.fields['slug'].required = False

        # Group checkbox fields for better UX
        self._add_field_groups()

    def _add_field_groups(self):
        """Add CSS classes and attributes to group related fields"""

        # Resolution checkboxes
        resolution_fields = [
            'resolution_512x512', 'resolution_512x768', 'resolution_512x1024',
            'resolution_768x512', 'resolution_768x768', 'resolution_768x1024',
            'resolution_1024x512', 'resolution_1024x768', 'resolution_1024x1024',
            'resolution_1280x720', 'resolution_1920x1080', 'resolution_2560x1440',
            'resolution_3840x2160'
        ]

        for field in resolution_fields:
            if field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': 'rounded text-blue-600 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600'
                })

    def clean_model_id(self):
        """Validate model_id format"""
        model_id = self.cleaned_data.get('model_id', '').strip()
        if not model_id:
            raise forms.ValidationError('ID модели обязателен')

        # Basic format validation (provider:id@version or similar)
        if ':' not in model_id:
            raise forms.ValidationError('ID модели должен содержать ":" (например: runware:101@1)')

        return model_id

    def save(self, commit=True):
        """Save form and populate optional_fields from checkboxes"""
        instance = super().save(commit=False)

        # Build optional_fields configuration from form data
        optional_fields = {}

        # Get checkbox values from POST data
        if hasattr(self, 'data'):
            # Basic fields
            optional_fields['resolution'] = 'resolution_enabled' in self.data
            optional_fields['steps'] = 'steps_enabled' in self.data
            optional_fields['cfg_scale'] = 'cfg_scale_enabled' in self.data
            optional_fields['scheduler'] = 'scheduler_enabled' in self.data
            optional_fields['seed'] = 'seed_enabled' in self.data
            optional_fields['negative_prompt'] = 'negative_prompt_enabled' in self.data
            optional_fields['reference_images'] = 'reference_images_enabled' in self.data
            optional_fields['number_results'] = 'number_results_enabled' in self.data

            # UI elements (always visible)
            optional_fields['prompt'] = 'prompt_enabled' in self.data
            optional_fields['auto_translate'] = 'auto_translate_enabled' in self.data
            optional_fields['prompt_generator'] = 'prompt_generator_enabled' in self.data

        instance.optional_fields = optional_fields

        if commit:
            instance.save()

        return instance

    def clean(self):
        """Additional validation"""
        cleaned_data = super().clean()

        # Validate resolution limits
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

        # Validate steps limits
        min_steps = cleaned_data.get('min_steps')
        max_steps = cleaned_data.get('max_steps')

        if min_steps is not None and max_steps is not None and min_steps > 0 and max_steps > 0:
            if min_steps > max_steps:
                raise forms.ValidationError('Минимум шагов не может быть больше максимума')

        # Validate CFG scale limits
        min_cfg = cleaned_data.get('min_cfg_scale')
        max_cfg = cleaned_data.get('max_cfg_scale')

        if min_cfg is not None and max_cfg is not None and min_cfg > 0 and max_cfg > 0:
            if min_cfg > max_cfg:
                raise forms.ValidationError('Минимальный CFG scale не может быть больше максимального')

        return cleaned_data
