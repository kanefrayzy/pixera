from django.core.management.base import BaseCommand
from pages.models import SiteSettings


class Command(BaseCommand):
    help = 'Управление плашкой 18+'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enable',
            action='store_true',
            help='Включить плашку 18+',
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='Отключить плашку 18+',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Показать текущий статус плашки',
        )

    def handle(self, *args, **options):
        settings = SiteSettings.get_settings()

        if options['enable']:
            settings.age_gate_enabled = True
            settings.save()
            self.stdout.write(
                self.style.SUCCESS('Плашка 18+ включена')
            )
        elif options['disable']:
            settings.age_gate_enabled = False
            settings.save()
            self.stdout.write(
                self.style.SUCCESS('Плашка 18+ отключена')
            )
        elif options['status']:
            status = "включена" if settings.age_gate_enabled else "отключена"
            self.stdout.write(f'Плашка 18+ {status}')
        else:
            self.stdout.write(
                'Используйте --enable, --disable или --status'
            )
