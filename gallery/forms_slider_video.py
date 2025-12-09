from django import forms
from django.core.exceptions import ValidationError
from .models_slider_video import VideoSliderExample


class VideoSliderExampleForm(forms.ModelForm):
    """Форма для редактирования видео-примеров слайдера (аналог SliderExampleForm, но с видео)."""

    class Meta:
        model = VideoSliderExample
        fields = [
            "title",
            "prompt",
            "video_file",
            "thumbnail",
            "description",
            "steps",
            "cfg",
            "seed",
            "order",
            "is_active",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Введите заголовок примера"}),
            "prompt": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Введите промт для генерации видео",
                }
            ),
            "video_file": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": "video/*",
                }
            ),
            "thumbnail": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "description": forms.TextInput(attrs={"class": "form-control", "placeholder": "Краткое описание примера"}),
            "steps": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 100}),
            "cfg": forms.NumberInput(attrs={"class": "form-control", "step": 0.1, "min": 1.0, "max": 20.0}),
            "seed": forms.TextInput(attrs={"class": "form-control", "placeholder": "auto или число"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_seed(self):
        seed = (self.cleaned_data.get("seed") or "").strip()
        if seed.lower() == "auto":
            return "auto"
        try:
            int(seed)
            return seed
        except Exception:
            raise ValidationError('Seed должен быть числом или "auto"')

    def clean_cfg(self):
        cfg = self.cleaned_data.get("cfg")
        if cfg and (cfg < 1.0 or cfg > 20.0):
            raise ValidationError("CFG Scale должен быть от 1.0 до 20.0")
        return cfg

    def clean_steps(self):
        steps = self.cleaned_data.get("steps")
        if steps and (steps < 1 or steps > 100):
            raise ValidationError("Количество шагов должно быть от 1 до 100")
        return steps

    def clean(self):
        cleaned = super().clean()
        # Требуем загрузку видео-файла (по запросу: "просто загрузку файла видео")
        video_file = cleaned.get("video_file") or getattr(self.instance, "video_file", None)
        if not video_file:
            raise ValidationError("Загрузите видео-файл (MP4 или поддерживаемый формат). Файл будет автоматически сжат.")
        return cleaned

    def save(self, commit=True):
        """Автоматическая генерация json_id (как в SliderExampleForm)."""
        instance = super().save(commit=False)
        if instance.pk is None and instance.json_id is None:
            from django.db.models import Max
            from django.db import transaction

            with transaction.atomic():
                max_id = VideoSliderExample.objects.select_for_update().aggregate(Max("json_id"))["json_id__max"]
                instance.json_id = (max_id + 1) if max_id is not None else 0

        if commit:
            instance.save()
        return instance


class VideoBulkImportForm(forms.Form):
    """Массовый импорт из JSON (для видео)."""

    confirm = forms.BooleanField(
        required=True,
        label="Подтверждаю импорт данных из JSON файла (видео)",
        help_text="Это действие обновит существующие записи видео-примеров",
    )


class VideoBulkExportForm(forms.Form):
    """Экспорт в JSON (для видео)."""

    confirm = forms.BooleanField(
        required=True,
        label="Подтверждаю экспорт данных в JSON файл (видео)",
        help_text="Это действие перезапишет JSON файл для видео",
    )
    create_backup = forms.BooleanField(
        required=False,
        initial=True,
        label="Создать резервную копию",
        help_text="Создать backup файл перед перезаписью",
    )


class VideoSliderExampleFilterForm(forms.Form):
    """Форма фильтрации видео-примеров."""

    title = forms.CharField(
        required=False,
        label="Название или описание",
        widget=forms.TextInput(attrs={"class": "field", "placeholder": "Поиск по заголовку"}),
    )

    is_active = forms.ChoiceField(
        required=False,
        label="Статус",
        choices=[
            ("", "Все"),
            ("1", "Активные"),
            ("0", "Неактивные"),
        ],
        widget=forms.Select(attrs={"class": "field"}),
    )
