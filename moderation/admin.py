# moderation/admin.py
from django.contrib import admin
from django.apps import apps
from .models import ModerationFlag


@admin.register(ModerationFlag)
class ModerationFlagAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "public_photo", "is_blocked", "reason", "created_at")
    list_filter = ("is_blocked", "created_at")
    search_fields = ("reason", "job__id", "public_photo__id")

    # Будем выставлять поля динамически в get_form
    autocomplete_fields = ()
    raw_id_fields = ()

    def get_form(self, request, obj=None, **kwargs):
        """
        Если админка связанной модели зарегистрирована и имеет search_fields —
        используем autocomplete. Иначе — безопасный фолбэк на raw_id_fields.
        Работает при любом порядке загрузки приложений.
        """
        PublicPhoto = apps.get_model("gallery", "PublicPhoto")
        GenerationJob = apps.get_model("generate", "GenerationJob")

        def can_autocomplete(model):
            if not model:
                return False
            ma = admin.site._registry.get(model)  # зарегистрированная ModelAdmin
            return bool(ma and getattr(ma, "search_fields", None))

        auto, raw = [], []

        # public_photo → gallery.PublicPhoto
        if can_autocomplete(PublicPhoto):
            auto.append("public_photo")
        else:
            raw.append("public_photo")

        # job → generate.GenerationJob
        if can_autocomplete(GenerationJob):
            auto.append("job")
        else:
            raw.append("job")

        # применяем на лету
        self.autocomplete_fields = tuple(auto)
        self.raw_id_fields = tuple(raw)

        return super().get_form(request, obj, **kwargs)
