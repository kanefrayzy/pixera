from django.core.management.base import BaseCommand
from gallery.models_slider import SliderExample


class Command(BaseCommand):
    help = 'Загрузить данные из JSON файла в базу данных'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительная загрузка (перезапись существующих данных)',
        )

    def handle(self, *args, **options):
        self.stdout.write('Начинаем загрузку данных из JSON файла...')

        success, message = SliderExample.load_from_json()

        if success:
            self.stdout.write(
                self.style.SUCCESS(f'Загрузка завершена успешно: {message}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при загрузке: {message}')
            )
