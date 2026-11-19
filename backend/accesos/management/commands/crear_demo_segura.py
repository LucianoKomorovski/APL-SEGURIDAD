import os
from getpass import getpass
from unittest.mock import patch

from django.apps import apps
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction


class Command(BaseCommand):
    help = 'Carga explícitamente una demo en una base vacía, con contraseñas nuevas ocultas.'

    def add_arguments(self, parser):
        parser.add_argument('--confirm-empty', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirm_empty']:
            raise CommandError('Requiere --confirm-empty y una base sin usuarios ni datos APL.')
        models = list(apps.get_app_config('accesos').get_models())
        models += list(apps.get_app_config('auth').get_models())
        if any(model.objects.exists() for model in models if model._meta.model_name != 'permission'):
            raise CommandError('Destino no vacío. No se modifica ni sobrescribe la base.')
        passwords = {}
        for key, role in [('APL_DEMO_OPERATOR_PASSWORD', 'operador'), ('APL_DEMO_TECH_PASSWORD', 'técnico')]:
            password = getpass(f'Contraseña nueva de {role}: ')
            if not password or password != getpass('Repetir contraseña: '):
                raise CommandError('Las contraseñas no coinciden o están vacías.')
            passwords[key] = password
        with patch.dict(os.environ, passwords):
            call_command('seed_demo', stdout=self.stdout)
            call_command('seed_incidentes_demo', stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS('Demo creada. No se guardaron contraseñas en archivos ni logs.'))
