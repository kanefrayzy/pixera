from __future__ import annotations

from django import forms
from .models import Category, PhotoComment

BANNED = {
    "nsfw", "nude", "nudity", "porn", "sex", "explicit", "xxx", "erotic",
}

def _sfw_check(text: str) -> None:
    low = (text or "").lower()
    if any(b in low for b in BANNED):
        raise forms.ValidationError("SFW only: обнаружены запрещённые слова.")


class ShareFromJobForm(forms.Form):
    title = forms.CharField(
        max_length=140, required=False,
        widget=forms.TextInput(attrs={
            "class": "input", "placeholder": "Короткий заголовок (до 140)"
        }),
        label="Заголовок",
    )
    caption = forms.CharField(
        max_length=240, required=False,
        widget=forms.TextInput(attrs={
            "class": "input", "placeholder": "Небольшая подпись (до 240)"
        }),
        label="Подпись",
    )
    # Разрешим выбрать одну или несколько — админ может заранее говорить «одна»,
    # но M2M в модели — значит позволим мультивыбор.
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "input", "size": "5"}),
        label="Категории",
    )

    def clean_title(self):
        t = self.cleaned_data.get("title", "").strip()
        if t:
            _sfw_check(t)
        return t

    def clean_caption(self):
        c = self.cleaned_data.get("caption", "").strip()
        if c:
            _sfw_check(c)
        return c


class PhotoCommentForm(forms.ModelForm):
    class Meta:
        model = PhotoComment
        fields = ("text",)
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "textarea",
                "rows": 3,
                "placeholder": "Напишите комментарий…",
            })
        }
        labels = {"text": "Комментарий"}

    def clean_text(self):
        tx = (self.cleaned_data.get("text") or "").strip()
        if not tx:
            raise forms.ValidationError("Комментарий не может быть пустым.")
        _sfw_check(tx)
        return tx
