from django import forms
from django.core.exceptions import ValidationError
from .models_slider import SliderExample


class SliderExampleForm(forms.ModelForm):
    """Форма для редактирования примеров слайдера"""

    class Meta:
        model = SliderExample
        fields = [
            'title', 'prompt', 'image', 'description', 'alt',
            'steps', 'cfg', 'ratio', 'seed', 'order', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите заголовок примера'
            }),
            'prompt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Введите промт для генерации изображения'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Краткое описание примера'
            }),
            'alt': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Alt текст для изображения'
            }),
            'steps': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 100
            }),
            'cfg': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 0.1,
                'min': 1.0,
                'max': 20.0
            }),
            'ratio': forms.Select(attrs={
                'class': 'form-control'
            }),
            'seed': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'auto или число'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }

    def clean_seed(self):
        seed = self.cleaned_data.get('seed', '').strip()
        if seed.lower() == 'auto':
            return 'auto'

        # Проверяем, что это число
        try:
            int(seed)
            return seed
        except ValueError:
            raise ValidationError('Seed должен быть числом или "auto"')

    def clean_cfg(self):
        cfg = self.cleaned_data.get('cfg')
        if cfg and (cfg < 1.0 or cfg > 20.0):
            raise ValidationError('CFG Scale должен быть от 1.0 до 20.0')
        return cfg

    def clean_steps(self):
        steps = self.cleaned_data.get('steps')
        if steps and (steps < 1 or steps > 100):
            raise ValidationError('Количество шагов должно быть от 1 до 100')
        return steps


class BulkImportForm(forms.Form):
    """Форма для массового импорта из JSON"""

    confirm = forms.BooleanField(
        required=True,
        label="Подтверждаю импорт данных из JSON файла",
        help_text="Это действие обновит существующие записи"
    )


class BulkExportForm(forms.Form):
    """Форма для экспорта в JSON"""

    confirm = forms.BooleanField(
        required=True,
        label="Подтверждаю экспорт данных в JSON файл",
        help_text="Это действие перезапишет существующий JSON файл"
    )

    create_backup = forms.BooleanField(
        required=False,
        initial=True,
        label="Создать резервную копию",
        help_text="Создать backup файл перед перезаписью"
    )


class SliderExampleFilterForm(forms.Form):
    """Форма фильтрации примеров"""

    title = forms.CharField(
        required=False,
        label='Название или описание',
        widget=forms.TextInput(attrs={
            'class': 'field',
            'placeholder': 'Поиск по заголовку'
        })
    )

    is_active = forms.ChoiceField(
        required=False,
        label='Статус',
        choices=[
            ('', 'Все'),
            ('1', 'Активные'),
            ('0', 'Неактивные'),
        ],
        widget=forms.Select(attrs={
            'class': 'field'
        })
    )

    ratio = forms.ChoiceField(
        required=False,
        label='Соотношение сторон',
        choices=[('', 'Все соотношения')] + SliderExample._meta.get_field('ratio').choices,
        widget=forms.Select(attrs={
            'class': 'field'
        })
    )
