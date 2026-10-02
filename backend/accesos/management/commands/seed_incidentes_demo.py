from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accesos.incidentes import asignar_intervencion, evaluar_incidente, registrar_incidente
from accesos.models import (
    AlertaSeguridad,
    ControladorAcceso,
    CuentaSistema,
    IncidenteTecnico,
)


class Command(BaseCommand):
    help = 'Agrega incidentes y una orden demo sin modificar registros existentes.'

    @transaction.atomic
    def handle(self, *args, **options):
        operador = CuentaSistema.objects.select_related('persona').filter(
            rol='Operador', activo=True, usuario__is_active=True
        ).first()
        tecnico = CuentaSistema.objects.filter(
            rol='Tecnico', activo=True, usuario__is_active=True
        ).first()
        dispositivo = ControladorAcceso.objects.select_related('edificio').filter(
            edificio__isnull=False
        ).first()
        if not operador or not tecnico or not dispositivo:
            raise CommandError('Ejecutá seed_demo antes de cargar los incidentes demo.')

        descripcion_alerta = 'Falla de comunicación detectada desde una alerta demo.'
        if not IncidenteTecnico.objects.filter(descripcion=descripcion_alerta).exists():
            alerta = AlertaSeguridad.objects.filter(
                dispositivo__edificio=dispositivo.edificio,
                incidente_tecnico__isnull=True,
            ).first()
            if not alerta:
                alerta = AlertaSeguridad.objects.create(
                    tipo_alerta='controladora sin comunicación',
                    nivel_gravedad='Alta',
                    estado_atencion='Pendiente',
                    dispositivo=dispositivo,
                )
            registrar_incidente(
                cuenta=operador,
                edificio=dispositivo.edificio,
                dispositivo=alerta.dispositivo,
                alerta=alerta,
                descripcion=descripcion_alerta,
                categoria='Conectividad',
                prioridad='Alta',
            )

        descripcion_manual = 'Lector con respuesta intermitente reportado por el cliente.'
        if not IncidenteTecnico.objects.filter(descripcion=descripcion_manual).exists():
            incidente = registrar_incidente(
                cuenta=operador,
                edificio=dispositivo.edificio,
                dispositivo=dispositivo,
                descripcion=descripcion_manual,
                categoria='Hardware',
                prioridad='Media',
            )
            incidente = evaluar_incidente(incidente=incidente, cuenta=operador)
            asignar_intervencion(
                incidente=incidente, tecnico=tecnico, cuenta=operador
            )

        self.stdout.write(self.style.SUCCESS(
            'Demo técnica lista: un incidente derivado de alerta y una orden asignada.'
        ))
