from django.db import models
from django.core.cache import cache


class SiteSettings(models.Model):
    """
    Настройки сайта - singleton модель (всегда только одна запись)
    """
    # Плашка 18+
    age_gate_enabled = models.BooleanField(
        default=True,
        verbose_name="Показывать плашку 18+",
        help_text="Включить/отключить плашку подтверждения возраста"
    )
    age_gate_title = models.CharField(
        max_length=200,
        default="Вам есть 18 лет?",
        verbose_name="Заголовок плашки 18+",
        help_text="Заголовок, отображаемый на плашке возраста"
    )
    age_gate_text = models.TextField(
        default="Доступ к сайту разрешён только пользователям старше 18 лет. Подтвердите возраст для продолжения работы.",
        verbose_name="Текст плашки 18+",
        help_text="Описание на плашке возраста"
    )

    # Другие настройки можно добавить здесь в будущем
    site_maintenance = models.BooleanField(
        default=False,
        verbose_name="Режим обслуживания",
        help_text="Включить режим технического обслуживания"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Настройки сайта"
        verbose_name_plural = "Настройки сайта"

    def __str__(self):
        return "Настройки сайта"

    def save(self, *args, **kwargs):
        # Обеспечиваем существование только одной записи
        if not self.pk and SiteSettings.objects.exists():
            # Если запись уже существует, обновляем её вместо создания новой
            existing = SiteSettings.objects.first()
            existing.age_gate_enabled = self.age_gate_enabled
            existing.age_gate_title = self.age_gate_title
            existing.age_gate_text = self.age_gate_text
            existing.site_maintenance = self.site_maintenance
            existing.save()
            return existing

        # Очищаем кэш при сохранении
        cache.delete('site_settings')
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """
        Получить настройки с кэшированием
        """
        settings = cache.get('site_settings')
        if settings is None:
            settings, created = cls.objects.get_or_create(
                pk=1,
                defaults={
                    'age_gate_enabled': True,
                    'age_gate_title': 'Вам есть 18 лет?',
                    'age_gate_text': 'Доступ к сайту разрешён только пользователям старше 18 лет. Подтвердите возраст для продолжения работы.',
                    'site_maintenance': False,
                }
            )
            cache.set('site_settings', settings, 60 * 60)  # кэшируем на час
        return settings

