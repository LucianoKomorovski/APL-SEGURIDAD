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


def _totem(edificio, zona, descripcion, serie, ip, sentido, tipo='Totem', camara=True, ubicacion='Puerta'):
    punto, _ = PuntoAcceso.objects.update_or_create(
        descripcion=descripcion,
        defaults={
            'ubicacion_fisica': ubicacion,
            'zona': zona,
            'sentido': sentido,
            'tipo': tipo,
            'tiene_camara': camara,
        },
    )
    ControladorAcceso.objects.update_or_create(
        numero_serie=serie,
        defaults={
            'direccion_ip': ip,
            'estado_conexion': 'Desconectado',
            'punto_acceso': punto,
            'edificio': edificio,
        },
    )
    return punto


def _edificio_con_ingreso(nombre, direccion, serie, ip, zona_raiz='Ingreso principal'):
    edificio, _ = Edificio.objects.update_or_create(
        nombre=nombre,
        defaults={'direccion': direccion},
    )
    raiz, _ = ComponenteZona.objects.update_or_create(
        nombre_zona=nombre,
        edificio=edificio,
        zona_padre=None,
        defaults={'nivel_seguridad': 'Media'},
    )
    ingreso, _ = ComponenteZona.objects.update_or_create(
        nombre_zona=zona_raiz,
        edificio=edificio,
        zona_padre=raiz,
        defaults={'nivel_seguridad': 'Media'},
    )
    _totem(
        edificio,
        ingreso,
        f'Tótem entrada {nombre}',
        serie,
        ip,
        'Entrada',
        ubicacion='Hall — guardia + cámara',
    )
    return edificio, raiz, ingreso


class Command(BaseCommand):
    help = (
        'Carga tres edificios clientes (consorcio, oficinas, depósito) '
        'con llaveros RFID para probar el panel multi-edificio.'
    )

    def handle(self, *args, **options):
        # Datos viejos del demo "sede APL / taller técnico": eso no es el dominio.
        Edificio.objects.filter(nombre='Sede APL Rosario').delete()
        ComponenteZona.objects.filter(
            nombre_zona__in=['Taller técnico', 'Sala de monitoreo', 'Predio APL', 'Hall de ingreso'],
        ).delete()
        NivelAcceso.objects.filter(
            nombre_nivel__in=[
                'Visitante',
                'Operador de monitoreo',
                'Técnico instalador',
                'Administrador de predio',
            ],
        ).delete()
        Credencial.objects.filter(
            codigo_referencia__in=['TAG-OP-01', 'TAG-ADM-01', 'TAG-VIS-01'],
        ).delete()

        pellegrini, raiz_pel, ingreso_pel = _edificio_con_ingreso(
            'Consorcio Pellegrini',
            'Av. Pellegrini 1200, Rosario',
            'PEL-ING-01',
            '199.1.1.0',
            'Ingreso peatonal',
        )
        oficinas, raiz_of, ingreso_of = _edificio_con_ingreso(
            'Oficinas Macrocentro',
            'San Lorenzo 800, Rosario',
            'OF-ING-01',
            '10.0.0.20',
        )
        deposito, raiz_dep, ingreso_dep = _edificio_con_ingreso(
            'Depósito Fisherton',
            'Av. de Circunvalación 4500, Rosario',
            'DEP-ING-01',
            '10.0.0.40',
        )

        _totem(
            pellegrini,
            ingreso_pel,
            'Tótem salida Consorcio Pellegrini',
            'PEL-SAL-01',
            '10.0.0.31',
            'Salida',
            ubicacion='Hall — guardia + cámara',
        )
        _totem(
            oficinas,
            ingreso_of,
            'Tótem salida Oficinas Macrocentro',
            'OF-SAL-01',
            '10.0.0.21',
            'Salida',
            ubicacion='Hall — guardia + cámara',
        )

        cochera, _ = ComponenteZona.objects.update_or_create(
            nombre_zona='Cochera',
            edificio=pellegrini,
            zona_padre=raiz_pel,
            defaults={'nivel_seguridad': 'Media'},
        )
        punto_cochera, _ = PuntoAcceso.objects.update_or_create(
            descripcion='Barrera cochera Pellegrini',
            defaults={
                'ubicacion_fisica': 'Subsuelo',
                'zona': cochera,
                'sentido': 'Entrada',
                'tipo': 'Lector',
                'tiene_camara': False,
            },
        )
        ControladorAcceso.objects.update_or_create(
            numero_serie='PEL-COC-01',
            defaults={
                'direccion_ip': '10.0.0.30',
                'estado_conexion': 'Desconectado',
                'punto_acceso': punto_cochera,
                'edificio': pellegrini,
            },
        )

        residente, _ = NivelAcceso.objects.update_or_create(
            nombre_nivel='Residente Pellegrini',
            defaults={'descripcion': 'Solo ingreso peatonal de su consorcio.'},
        )
        residente.zonas.set([ingreso_pel])

        encargado, _ = NivelAcceso.objects.update_or_create(
            nombre_nivel='Encargado Pellegrini',
            defaults={'descripcion': 'Todo el consorcio (ingreso y cochera).'},
        )
        encargado.zonas.set([raiz_pel])

        empleado_of, _ = NivelAcceso.objects.update_or_create(
            nombre_nivel='Empleado oficinas',
            defaults={'descripcion': 'Ingreso del edificio de oficinas.'},
        )
        empleado_of.zonas.set([ingreso_of])

        tecnico, _ = NivelAcceso.objects.update_or_create(
            nombre_nivel='Técnico de servicio',
            defaults={
                'descripcion': 'Personal APL que da servicio en todos los edificios clientes.',
            },
        )
        tecnico.zonas.set([raiz_pel, raiz_of, raiz_dep])

        visitante, _ = NivelAcceso.objects.update_or_create(
            nombre_nivel='Visitante Pellegrini',
            defaults={'descripcion': 'Ingreso peatonal, lunes a viernes 08-18.'},
        )
        visitante.zonas.set([ingreso_pel])
        HorarioPermitido.objects.filter(nivel_acceso=visitante).delete()
        HorarioPermitido.objects.create(
            hora_inicio=time(8, 0),
            hora_fin=time(18, 0),
            dias_semana='0,1,2,3,4',
            nivel_acceso=visitante,
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
        clientes = [
            {
                'dni': 40111001,
                'defaults': {
                    'nombre': 'María',
                    'apellido': 'Gómez',
                    'email': 'maria.gomez@pellegrini-demo.local',
                    'legajo_empleado': 'PEL-01',
                    'nivel_acceso': residente,
                    'edificio': pellegrini,
                },
                'tag': 'TAG-PEL-01',
            },
            {
                'dni': 40111002,
                'defaults': {
                    'nombre': 'Sofía',
                    'apellido': 'Ruiz',
                    'email': 'sofia.ruiz@apl-demo.local',
                    'legajo_empleado': 'TEC-01',
                    'nivel_acceso': tecnico,
                    'edificio': None,
                },
                'tag': 'TAG-TEC-01',
            },
            {
                'dni': 40111003,
                'defaults': {
                    'nombre': 'Pedro',
                    'apellido': 'Visitante',
                    'email': 'pedro.vis@pellegrini-demo.local',
                    'legajo_empleado': 'VIS-01',
                    'nivel_acceso': visitante,
                    'edificio': pellegrini,
                },
                'tag': 'TAG-VIS-01',
            },
            {
                'dni': 40111004,
                'defaults': {
                    'nombre': 'Carlos',
                    'apellido': 'Encargado',
                    'email': 'carlos.enc@pellegrini-demo.local',
                    'legajo_empleado': 'ENC-01',
                    'nivel_acceso': encargado,
                    'edificio': pellegrini,
                },
                'tag': 'TAG-ENC-01',
            },
            {
                'dni': 40111007,
                'defaults': {
                    'nombre': 'Laura',
                    'apellido': 'Benítez',
                    'email': 'laura.benitez@oficinas-demo.local',
                    'legajo_empleado': 'OF-01',
                    'nivel_acceso': empleado_of,
                    'edificio': oficinas,
                },
                'tag': 'TAG-OF-01',
            },
        ]

        for item in clientes:
            sujeto, _ = SujetoAcceso.objects.update_or_create(
                dni=item['dni'],
                defaults=item['defaults'],
            )
            Credencial.objects.update_or_create(
                codigo_referencia=item['tag'],
                defaults={
                    'tipo': 'Magnetica',
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
                'email': 'luis.bloq@pellegrini-demo.local',
                'legajo_empleado': 'BLOQ-01',
                'nivel_acceso': residente,
                'edificio': pellegrini,
            },
        )
        Credencial.objects.update_or_create(
            codigo_referencia='TAG-BLOQ-01',
            defaults={
                'tipo': 'Magnetica',
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
                'email': 'clara.ven@pellegrini-demo.local',
                'legajo_empleado': 'VEN-01',
                'nivel_acceso': residente,
                'edificio': pellegrini,
            },
        )
        Credencial.objects.update_or_create(
            codigo_referencia='TAG-VENC-01',
            defaults={
                'tipo': 'Magnetica',
                'fecha_vencimiento': date(2020, 1, 1),
                'estado': 'Activa',
                'persona': vencido,
            },
        )

        self.stdout.write(self.style.SUCCESS(
            'Demo multi-edificio lista. Panel: operador / apl2026. '
            'Pellegrini entrada 199.1.1.0 / salida 10.0.0.31 | '
            'Oficinas entrada 10.0.0.20 / salida 10.0.0.21 | '
            'Depósito 10.0.0.40. '
            'Llaves: TAG-PEL-01, TAG-OF-01, TAG-ENC-01, TAG-TEC-01, TAG-VIS-01, '
            'TAG-BLOQ-01, TAG-VENC-01.'
        ))
