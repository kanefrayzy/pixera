# FILE: blog/urls.py
from django.urls import path, register_converter
from . import views

app_name = "blog"

# ── Unicode-slug: любые «словные» символы юникода + дефис
class UnicodeSlugConverter:
    # \w в Django-конвертерах — это юникодные буквенно-цифровые + "_"
    # Добавляем "-" вручную. Плюс защищаемся от пустой строки.
    regex = r'[-\w]+'

    def to_python(self, value: str) -> str:
        return value

    def to_url(self, value: str) -> str:
        return value

register_converter(UnicodeSlugConverter, "uslug")

urlpatterns = [
    # список
    path("", views.index, name="index"),

    # создание — важно объявлять до slug-маршрута
    path("new/", views.PostCreateView.as_view(), name="create"),

    # детальная / редактирование / удаление — Unicode-slug
    path("<uslug:slug>/", views.detail, name="detail"),
    path("<uslug:slug>/edit/", views.PostUpdateView.as_view(), name="edit"),
    path("<uslug:slug>/delete/", views.PostDeleteView.as_view(), name="delete"),
]
