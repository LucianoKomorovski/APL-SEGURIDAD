from datetime import date, time, timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone

from accesos.models import (
    ComponenteZona,
    ControladorAcceso,
    Credencial,
    Edificio,
    HorarioPermitido,
    NivelAcceso,
    OperadorSistema,
    PuntoAcceso,
    SujetoAcceso,
)


class Command(BaseCommand):
    help = 'Carga un predio demo tipo APL Rosario para probar el motor de reglas.'

    def handle(self, *args, **options):
        edificio, _ = Edificio.objects.update_or_create(
            nombre='Sede APL Rosario',
            defaults={'direccion': 'Rosario, Santa Fe'},
        )

        predio, _ = ComponenteZona.objects.update_or_create(
            nombre_zona='Predio APL',
            defaults={
                'nivel_seguridad': 'Baja',
                'zona_padre': None,
                'edificio': edificio,
            },
        )
        hall, _ = ComponenteZona.objects.update_or_create(
            nombre_zona='Hall de ingreso',
            defaults={
                'nivel_seguridad': 'Media',
                'zona_padre': predio,
                'edificio': edificio,
            },
        )
        monitoreo, _ = ComponenteZona.objects.update_or_create(
            nombre_zona='Sala de monitoreo',
            defaults={
                'nivel_seguridad': 'Alta',
                'zona_padre': predio,
                'edificio': edificio,
            },
        )
        tecnica, _ = ComponenteZona.objects.update_or_create(
            nombre_zona='Taller técnico',
            defaults={
                'nivel_seguridad': 'Media',
                'zona_padre': predio,
                'edificio': edificio,
            },
        )

        visitante, _ = NivelAcceso.objects.update_or_create(
            nombre_nivel='Visitante',
            defaults={'descripcion': 'Solo hall de ingreso en horario laboral.'},
        )
        visitante.zonas.set([hall])

        operador_nivel, _ = NivelAcceso.objects.update_or_create(
            nombre_nivel='Operador de monitoreo',
            defaults={'descripcion': 'Hall y sala de monitoreo, 24/7.'},
        )
        operador_nivel.zonas.set([hall, monitoreo])

        tecnico_nivel, _ = NivelAcceso.objects.update_or_create(
            nombre_nivel='Técnico instalador',
            defaults={'descripcion': 'Hall y taller. Sin sala de monitoreo.'},
        )
        tecnico_nivel.zonas.set([hall, tecnica])

        admin_nivel, _ = NivelAcceso.objects.update_or_create(
            nombre_nivel='Administrador de predio',
            defaults={'descripcion': 'Acceso al predio completo (Composite).'},
        )
        admin_nivel.zonas.set([predio])

        HorarioPermitido.objects.filter(nivel_acceso=visitante).delete()
        HorarioPermitido.objects.create(
            hora_inicio=time(8, 0),
            hora_fin=time(18, 0),
            dias_semana='0,1,2,3,4',
            nivel_acceso=visitante,
        )

        punto_hall, _ = PuntoAcceso.objects.update_or_create(
            descripcion='Molinete hall',
            defaults={'ubicacion_fisica': 'Ingreso principal', 'zona': hall},
        )
        punto_monitoreo, _ = PuntoAcceso.objects.update_or_create(
            descripcion='Puerta sala de monitoreo',
            defaults={'ubicacion_fisica': 'Interior hall', 'zona': monitoreo},
        )
        punto_taller, _ = PuntoAcceso.objects.update_or_create(
            descripcion='Puerta taller',
            defaults={'ubicacion_fisica': 'Fondo del predio', 'zona': tecnica},
        )

        ControladorAcceso.objects.update_or_create(
            numero_serie='APL-HALL-01',
            defaults={
                'direccion_ip': '199.1.1.0',
                'estado_conexion': 'Desconectado',
                'punto_acceso': punto_hall,
                'edificio': edificio,
            },
        )
        ControladorAcceso.objects.update_or_create(
            numero_serie='APL-MON-01',
            defaults={
                'direccion_ip': '10.0.0.20',
                'estado_conexion': 'Desconectado',
                'punto_acceso': punto_monitoreo,
                'edificio': edificio,
            },
        )
        ControladorAcceso.objects.update_or_create(
            numero_serie='APL-TEC-01',
            defaults={
                'direccion_ip': '10.0.0.30',
                'estado_conexion': 'Desconectado',
                'punto_acceso': punto_taller,
                'edificio': edificio,
            },
        )

        operador, created_op = OperadorSistema.objects.update_or_create(
            username='operador',
            defaults={
                'nombre': 'Lucía',
                'apellido': 'Monitoreo',
                'dni': 30111222,
                'email': 'operador@apl-demo.local',
                'telefono': '3415550000',
                'turno_asignado': 'Tarde',
                'password_hash': make_password('apl2026'),
            },
        )
        if not created_op:
            operador.password_hash = make_password('apl2026')
            operador.save(update_fields=['password_hash'])

        vencimiento = timezone.now().date() + timedelta(days=365)
        personas = [
            {
                'dni': 40111001,
                'defaults': {
                    'nombre': 'Marcos',
                    'apellido': 'Operador',
                    'email': 'marcos.op@apl-demo.local',
                    'legajo_empleado': 'OP-01',
                    'nivel_acceso': operador_nivel,
                    'edificio': edificio,
                },
                'tag': 'TAG-OP-01',
            },
            {
                'dni': 40111002,
                'defaults': {
                    'nombre': 'Sofía',
                    'apellido': 'Técnica',
                    'email': 'sofia.tec@apl-demo.local',
                    'legajo_empleado': 'TEC-01',
                    'nivel_acceso': tecnico_nivel,
                    'edificio': edificio,
                },
                'tag': 'TAG-TEC-01',
            },
            {
                'dni': 40111003,
                'defaults': {
                    'nombre': 'Pedro',
                    'apellido': 'Visitante',
                    'email': 'pedro.vis@apl-demo.local',
                    'legajo_empleado': 'VIS-01',
                    'nivel_acceso': visitante,
                    'edificio': edificio,
                },
                'tag': 'TAG-VIS-01',
            },
            {
                'dni': 40111004,
                'defaults': {
                    'nombre': 'Ana',
                    'apellido': 'Administración',
                    'email': 'ana.adm@apl-demo.local',
                    'legajo_empleado': 'ADM-01',
                    'nivel_acceso': admin_nivel,
                    'edificio': edificio,
                },
                'tag': 'TAG-ADM-01',
            },
        ]

        for item in personas:
            sujeto, _ = SujetoAcceso.objects.update_or_create(
                dni=item['dni'],
                defaults=item['defaults'],
            )
            Credencial.objects.update_or_create(
                codigo_referencia=item['tag'],
                defaults={
                    'tipo': 'RFID',
                    'fecha_vencimiento': vencimiento,
                    'estado': 'Activa',
                    'persona': sujeto,
                },
            )

        bloqueado, _ = SujetoAcceso.objects.update_or_create(
            dni=40111005,
            defaults={
                'nombre': 'Luis',
                'apellido': 'Bloqueado',
                'email': 'luis.bloq@apl-demo.local',
                'legajo_empleado': 'BLOQ-01',
                'nivel_acceso': visitante,
                'edificio': edificio,
            },
        )
        Credencial.objects.update_or_create(
            codigo_referencia='TAG-BLOQ-01',
            defaults={
                'tipo': 'RFID',
                'fecha_vencimiento': vencimiento,
                'estado': 'Bloqueada',
                'persona': bloqueado,
            },
        )

        vencido, _ = SujetoAcceso.objects.update_or_create(
            dni=40111006,
            defaults={
                'nombre': 'Clara',
                'apellido': 'Vencida',
                'email': 'clara.ven@apl-demo.local',
                'legajo_empleado': 'VEN-01',
                'nivel_acceso': visitante,
                'edificio': edificio,
            },
        )
        Credencial.objects.update_or_create(
            codigo_referencia='TAG-VENC-01',
            defaults={
                'tipo': 'RFID',
                'fecha_vencimiento': date(2020, 1, 1),
                'estado': 'Activa',
                'persona': vencido,
            },
        )

        self.stdout.write(self.style.SUCCESS(
            'Demo lista. Panel: usuario operador / apl2026. '
            'Tags: TAG-OP-01, TAG-TEC-01, TAG-VIS-01, TAG-ADM-01, TAG-BLOQ-01, TAG-VENC-01. '
            'Tótem hall: 199.1.1.0 — monitoreo: 10.0.0.20 — taller: 10.0.0.30'
        ))
