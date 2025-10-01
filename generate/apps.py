from django.apps import AppConfig


class GenerateConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "generate"
    verbose_name = "Генерация"
    # ВАЖНО: никаких signals здесь не подключаем (ready() пустой),
    # чтобы исключить возможные циклы/рекурсию у staff.
