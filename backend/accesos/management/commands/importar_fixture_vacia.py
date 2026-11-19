from pathlib import Path

from django.apps import apps
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection, transaction


class Command(BaseCommand):
    help = 'Importa un dumpdata Django únicamente en PostgreSQL vacío ya migrado.'

    def add_arguments(self, parser):
        parser.add_argument('fixture')
        parser.add_argument('--confirm-empty', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        if connection.vendor != 'postgresql' or not options['confirm_empty']:
            raise CommandError('Requiere PostgreSQL y --confirm-empty.')
        if not Path(options['fixture']).is_file():
            raise CommandError('No existe el fixture.')
        allowed = {'contenttypes.contenttype', 'auth.permission'}
        for model in apps.get_models():
            if model._meta.label_lower not in allowed and model.objects.exists():
                raise CommandError(f'Destino no vacío: {model._meta.label}. No se importó nada.')
        # loaddata valida FK al terminar y reinicia las secuencias de los modelos cargados.
        call_command('loaddata', options['fixture'], stdout=self.stdout)
