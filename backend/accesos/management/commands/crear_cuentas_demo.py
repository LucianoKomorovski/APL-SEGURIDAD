from accesos.management.demo_passwords import demo_passwords
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accesos.models import CuentaSistema, OperadorSistema, SujetoAcceso


class Command(BaseCommand):
    help = 'Crea o actualiza las cuentas demo de operador y técnico.'

    @transaction.atomic
    def handle(self, *args, **options):
        operador = OperadorSistema.objects.filter(username='operador').first()
        tecnico = SujetoAcceso.objects.filter(legajo_empleado='TEC-01').first()
        if not operador or not tecnico:
            raise CommandError('Ejecutá seed_demo primero para crear las personas demo.')

        operator_password, tech_password = demo_passwords()
        self._crear('operador', operador, 'Operador', operator_password)
        self._crear('tecnico', tecnico, 'Tecnico', tech_password)
        self.stdout.write(self.style.SUCCESS(
            'Cuentas actualizadas; contraseñas no mostradas.'
        ))

    def _crear(self, username, persona, rol, password):
        usuario, _ = User.objects.get_or_create(username=username)
        usuario.first_name = persona.nombre
        usuario.last_name = persona.apellido
        usuario.email = persona.email
        usuario.is_active = True
        usuario.set_password(password)
        usuario.save()
        CuentaSistema.objects.update_or_create(
            persona=persona,
            defaults={'usuario': usuario, 'rol': rol, 'activo': True},
        )
