from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accesos.models import (
    AlertaSeguridad,
    ComponenteZona,
    ControladorAcceso,
    Credencial,
    Edificio,
    HorarioPermitido,
    NivelAcceso,
    OperadorSistema,
    PuntoAcceso,
    RegistroAcceso,
    SujetoAcceso,
)
from accesos.motor_reglas import MotorValidacionAcceso, zona_esta_permitida


TZ = ZoneInfo('America/Argentina/Buenos_Aires')


class MotorReglasTests(TestCase):
    def setUp(self):
        self.edificio = Edificio.objects.create(
            nombre='Sede APL Rosario',
            direccion='Rosario',
        )
        self.predio = ComponenteZona.objects.create(
            nombre_zona='Predio',
            edificio=self.edificio,
        )
        self.hall = ComponenteZona.objects.create(
            nombre_zona='Hall',
            zona_padre=self.predio,
            edificio=self.edificio,
        )
        self.monitoreo = ComponenteZona.objects.create(
            nombre_zona='Monitoreo',
            zona_padre=self.predio,
            edificio=self.edificio,
        )

        self.nivel_hall = NivelAcceso.objects.create(nombre_nivel='Visitante')
        self.nivel_hall.zonas.add(self.hall)
        HorarioPermitido.objects.create(
            hora_inicio=time(8, 0),
            hora_fin=time(18, 0),
            dias_semana='0,1,2,3,4',
            nivel_acceso=self.nivel_hall,
        )

        self.nivel_predio = NivelAcceso.objects.create(nombre_nivel='Admin')
        self.nivel_predio.zonas.add(self.predio)

        punto_hall = PuntoAcceso.objects.create(
            descripcion='Molinete',
            ubicacion_fisica='Ingreso',
            zona=self.hall,
        )
        punto_mon = PuntoAcceso.objects.create(
            descripcion='Puerta monitoreo',
            ubicacion_fisica='Interior',
            zona=self.monitoreo,
        )
        self.ctrl_hall = ControladorAcceso.objects.create(
            direccion_ip='199.1.1.0',
            numero_serie='HALL-1',
            punto_acceso=punto_hall,
            edificio=self.edificio,
        )
        self.ctrl_mon = ControladorAcceso.objects.create(
            direccion_ip='10.0.0.20',
            numero_serie='MON-1',
            punto_acceso=punto_mon,
            edificio=self.edificio,
        )

        self.visitante = SujetoAcceso.objects.create(
            nombre='Pedro',
            apellido='Visitante',
            dni=111,
            email='pedro@test.local',
            nivel_acceso=self.nivel_hall,
            edificio=self.edificio,
        )
        self.tag_vis = Credencial.objects.create(
            codigo_referencia='TAG-VIS',
            fecha_vencimiento=date.today() + timedelta(days=30),
            persona=self.visitante,
        )
        self.admin = SujetoAcceso.objects.create(
            nombre='Ana',
            apellido='Admin',
            dni=222,
            email='ana@test.local',
            nivel_acceso=self.nivel_predio,
            edificio=self.edificio,
        )
        self.tag_adm = Credencial.objects.create(
            codigo_referencia='TAG-ADM',
            fecha_vencimiento=date.today() + timedelta(days=30),
            persona=self.admin,
        )
        self.motor = MotorValidacionAcceso()
        self.lunes_10 = datetime(2026, 9, 7, 10, 0, tzinfo=TZ)
        self.domingo_10 = datetime(2026, 9, 6, 10, 0, tzinfo=TZ)

    def test_visitante_entra_al_hall_en_horario(self):
        r = self.motor.evaluar('TAG-VIS', '199.1.1.0', ahora=self.lunes_10)
        self.assertTrue(r.concedido)
        self.assertEqual(r.accion, 'ABRIR_PUERTA')

    def test_visitante_entra_a_subzona_del_hall(self):
        oficina = ComponenteZona.objects.create(
            nombre_zona='Recepción',
            zona_padre=self.hall,
            edificio=self.edificio,
        )
        punto = PuntoAcceso.objects.create(
            descripcion='Puerta recepción',
            ubicacion_fisica='Hall',
            zona=oficina,
        )
        ControladorAcceso.objects.create(
            direccion_ip='10.0.0.40',
            numero_serie='REC-1',
            punto_acceso=punto,
            edificio=self.edificio,
        )
        r = self.motor.evaluar('TAG-VIS', '10.0.0.40', ahora=self.lunes_10)
        self.assertTrue(r.concedido)

    def test_visitante_no_entra_a_monitoreo(self):
        r = self.motor.evaluar('TAG-VIS', '10.0.0.20', ahora=self.lunes_10)
        self.assertFalse(r.concedido)
        self.assertIn('zona no permitida', r.motivo)

    def test_admin_entra_a_monitoreo_por_composite(self):
        self.assertTrue(zona_esta_permitida(self.monitoreo, self.nivel_predio))
        r = self.motor.evaluar('TAG-ADM', '10.0.0.20', ahora=self.lunes_10)
        self.assertTrue(r.concedido)

    def test_visitante_fuera_de_horario(self):
        r = self.motor.evaluar('TAG-VIS', '199.1.1.0', ahora=self.domingo_10)
        self.assertFalse(r.concedido)
        self.assertEqual(r.motivo, 'fuera de horario permitido')

    def test_tarjeta_inexistente(self):
        r = self.motor.evaluar('NO-EXISTE', '199.1.1.0', ahora=self.lunes_10)
        self.assertFalse(r.concedido)
        self.assertEqual(r.motivo, 'tarjeta inexistente')

    def test_tarjeta_bloqueada(self):
        self.tag_vis.estado = 'Bloqueada'
        self.tag_vis.save()
        r = self.motor.evaluar('TAG-VIS', '199.1.1.0', ahora=self.lunes_10)
        self.assertEqual(r.motivo, 'tarjeta bloqueada')

    def test_dispositivo_desconocido(self):
        r = self.motor.evaluar('TAG-VIS', '1.2.3.4', ahora=self.lunes_10)
        self.assertEqual(r.motivo, 'dispositivo no encontrado')
        self.assertIsNone(r.dispositivo)


class TotemApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        MotorReglasTests.setUp(self)
        self.operador = OperadorSistema.objects.create(
            nombre='Lucía',
            apellido='Op',
            dni=333,
            email='op@test.local',
            username='operador',
            password_hash=make_password('apl2026'),
            turno_asignado='Tarde',
        )

    def test_lectura_concedida_persiste_registro(self):
        with timezone.override(TZ):
            respuesta = self.client.post(
                '/api/totem/lectura/',
                {'codigo_rfid': 'TAG-ADM', 'ip_totem': '199.1.1.0'},
                format='json',
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['accion'], 'ABRIR_PUERTA')
        self.assertEqual(RegistroAcceso.objects.filter(resultado='concedido').count(), 1)

    def test_lectura_denegada_genera_alerta(self):
        respuesta = self.client.post(
            '/api/totem/lectura/',
            {'codigo_rfid': 'FALSA', 'ip_totem': '199.1.1.0'},
            format='json',
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(AlertaSeguridad.objects.count(), 1)
        self.assertEqual(RegistroAcceso.objects.filter(resultado='rechazado').count(), 1)

    def test_puerta_forzada(self):
        respuesta = self.client.post(
            '/api/totem/evento/',
            {'ip_totem': '199.1.1.0', 'tipo': 'PUERTA_FORZADA'},
            format='json',
        )
        self.assertEqual(respuesta.status_code, 200)
        alerta = AlertaSeguridad.objects.get()
        self.assertEqual(alerta.tipo_alerta, 'puerta forzada')
        self.assertEqual(alerta.nivel_gravedad, 'Critica')

    def test_resolver_alerta_crea_resolucion(self):
        alerta = AlertaSeguridad.objects.create(
            tipo_alerta='puerta forzada',
            nivel_gravedad='Critica',
            dispositivo=self.ctrl_hall,
        )
        respuesta = self.client.post(
            f'/api/alertas/{alerta.id}/resolver/',
            {'observaciones': 'Revisado en sitio', 'operador': self.operador.pk},
            format='json',
        )
        self.assertEqual(respuesta.status_code, 200)
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado_atencion, 'Resuelta')
        self.assertEqual(alerta.resolucion.observaciones, 'Revisado en sitio')

    def test_login_operador(self):
        ok = self.client.post(
            '/api/auth/login/',
            {'username': 'operador', 'password': 'apl2026'},
            format='json',
        )
        self.assertEqual(ok.status_code, 200)
        fail = self.client.post(
            '/api/auth/login/',
            {'username': 'operador', 'password': 'mala'},
            format='json',
        )
        self.assertEqual(fail.status_code, 401)
