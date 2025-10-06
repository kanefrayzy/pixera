from django.contrib import admin
from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """
    Админ-панель для настроек сайта
    """
    list_display = ['__str__', 'age_gate_enabled', 'site_maintenance', 'updated_at']

    fieldsets = (
        ('Плашка 18+', {
            'fields': ('age_gate_enabled', 'age_gate_title', 'age_gate_text'),
            'description': 'Настройки плашки подтверждения возраста'
        }),
        ('Общие настройки', {
            'fields': ('site_maintenance',),
            'classes': ('collapse',)
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def has_add_permission(self, request):
        # Разрешаем создание только если записей нет
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Запрещаем удаление настроек
        return False

    def changelist_view(self, request, extra_context=None):
        # Если настроек нет, создаем их автоматически
        if not SiteSettings.objects.exists():
            SiteSettings.objects.create()
        return super().changelist_view(request, extra_context)

