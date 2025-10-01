from django import forms
from .models import Category


class ShareFromJobForm(forms.Form):
    title = forms.CharField(
        label="Заголовок",
        max_length=140,
        required=False,
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "Заголовок (опционально)"}),
    )
    caption = forms.CharField(
        label="Подпись",
        max_length=240,
        required=False,
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "Подпись (опционально)"}),
    )
    categories = forms.ModelMultipleChoiceField(
        label="Категории",
        required=False,
        queryset=Category.objects.none(),  # зададим в __init__
        widget=forms.SelectMultiple(attrs={"class": "input", "size": "6"}),
        help_text="Выберите одну или несколько категорий (создаёт админ).",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categories"].queryset = Category.objects.all()

    # Только «привести в порядок» строки
    def clean_title(self):
        return (self.cleaned_data.get("title") or "").strip()

    def clean_caption(self):
        return (self.cleaned_data.get("caption") or "").strip()


class PhotoCommentForm(forms.Form):
    text = forms.CharField(
        label="Комментарий",
        widget=forms.Textarea(attrs={"class": "textarea", "rows": 3, "placeholder": "Напишите комментарий…"}),
    )

    def clean_text(self):
        tx = (self.cleaned_data.get("text") or "").strip()
        if not tx:
            raise forms.ValidationError("Комментарий не может быть пустым.")
        return tx
