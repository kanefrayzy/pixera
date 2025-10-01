# blog/forms.py
from __future__ import annotations

from django import forms
from django.utils.text import slugify

from .models import Post, Tag


class PostForm(forms.ModelForm):
    """
    Форма создания/редактирования поста.
    Админ вводит теги одной строкой: `тег1, тег2, ...`.
    """

    tags_csv = forms.CharField(
        label="Теги",
        required=False,
        help_text="Перечислите через запятую: например, «раздеватор, нейросеть, руководство».",
        widget=forms.TextInput(
            attrs={"class": "input", "placeholder": "теги через запятую"}
        ),
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "cover",
            "excerpt",
            "body",
            # SEO
            "meta_title",
            "meta_description",
            "og_title",
            "og_description",
            "og_image",
            # публикация
            "is_published",
            "published_at",
            # виртуальное поле тегов (CSV)
            "tags_csv",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "input", "placeholder": "Заголовок"}
            ),
            "excerpt": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "rows": 3,
                    "placeholder": "Краткое описание",
                }
            ),
            "body": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "rows": 12,
                    "placeholder": "Текст статьи (можно HTML)",
                }
            ),
            "meta_title": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Meta title (если пусто — берём заголовок)",
                }
            ),
            "meta_description": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "rows": 3,
                    "placeholder": "Короткое SEO-описание",
                }
            ),
            "og_title": forms.TextInput(
                attrs={"class": "input", "placeholder": "OG title"}
            ),
            "og_description": forms.Textarea(
                attrs={"class": "textarea", "rows": 3, "placeholder": "OG description"}
            ),
            "published_at": forms.DateTimeInput(
                attrs={"class": "input", "type": "datetime-local"}
            ),
        }

    # Префилл CSV из m2m
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            names = [t.name for t in self.instance.tags.all()]
            self.fields["tags_csv"].initial = ", ".join(names)

    def clean(self):
        data = super().clean()
        # Мягкие фоллбеки — SEO можно не заполнять
        title = (data.get("title") or "").strip()
        excerpt = (data.get("excerpt") or "").strip()

        if not data.get("meta_title"):
            data["meta_title"] = title[:180]
        if not data.get("meta_description"):
            data["meta_description"] = excerpt[:300]
        return data

    def _parse_tags(self) -> list[Tag]:
        """
        Превращаем CSV "тег1, тег2" -> список/создание Tag.
        """
        raw = (self.cleaned_data.get("tags_csv") or "").replace(";", ",")
        names = [n.strip() for n in raw.split(",") if n.strip()]
        tags: list[Tag] = []
        for name in names:
            # аккуратный slug (разрешаем unicode)
            slug = slugify(name, allow_unicode=True) or name.lower().replace(" ", "-")
            tag, created = Tag.objects.get_or_create(slug=slug, defaults={"name": name})
            if not created and tag.name != name:
                tag.name = name
                tag.save(update_fields=["name"])
            tags.append(tag)
        return tags

    def save(self, commit: bool = True) -> Post:
        """
        Сохраняем пост и синхронизируем m2m-теги.
        """
        obj: Post = super().save(commit=commit)

        tags = self._parse_tags()
        if commit:
            obj.tags.set(tags)
        else:
            # если вызов с commit=False — отложенный m2m-сет
            self._pending_tags = tags  # type: ignore[attr-defined]

        return obj
