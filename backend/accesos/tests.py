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


def _punto_y_controlador(zona, edificio, descripcion, ip, serie, sentido='Entrada'):
    punto = PuntoAcceso.objects.create(
        descripcion=descripcion,
        ubicacion_fisica=descripcion,
        zona=zona,
        sentido=sentido,
        tipo='Totem',
        tiene_camara=True,
    )
    return ControladorAcceso.objects.create(
        direccion_ip=ip,
        numero_serie=serie,
        punto_acceso=punto,
        edificio=edificio,
    )


class MotorReglasTests(TestCase):
    def setUp(self):
        self.pellegrini = Edificio.objects.create(
            nombre='Consorcio Pellegrini',
            direccion='Rosario',
        )
        self.oficinas = Edificio.objects.create(
            nombre='Oficinas Macrocentro',
            direccion='Rosario',
        )
        self.raiz_pel = ComponenteZona.objects.create(
            nombre_zona='Consorcio Pellegrini',
            edificio=self.pellegrini,
        )
        self.ingreso = ComponenteZona.objects.create(
            nombre_zona='Ingreso peatonal',
            zona_padre=self.raiz_pel,
            edificio=self.pellegrini,
        )
        self.cochera = ComponenteZona.objects.create(
            nombre_zona='Cochera',
            zona_padre=self.raiz_pel,
            edificio=self.pellegrini,
        )
        self.ingreso_of = ComponenteZona.objects.create(
            nombre_zona='Ingreso oficinas',
            edificio=self.oficinas,
        )

        self.nivel_residente = NivelAcceso.objects.create(nombre_nivel='Residente Pellegrini')
        self.nivel_residente.zonas.add(self.ingreso)
        HorarioPermitido.objects.create(
            hora_inicio=time(8, 0),
            hora_fin=time(18, 0),
            dias_semana='0,1,2,3,4',
            nivel_acceso=self.nivel_residente,
        )

        self.nivel_encargado = NivelAcceso.objects.create(nombre_nivel='Encargado Pellegrini')
        self.nivel_encargado.zonas.add(self.raiz_pel)

        self.nivel_oficinas = NivelAcceso.objects.create(nombre_nivel='Empleado oficinas')
        self.nivel_oficinas.zonas.add(self.ingreso_of)

        self.ctrl_ingreso = _punto_y_controlador(
            self.ingreso, self.pellegrini, 'Tótem ingreso', '199.1.1.0', 'PEL-ING-01', 'Entrada',
        )
        self.ctrl_salida = _punto_y_controlador(
            self.ingreso, self.pellegrini, 'Tótem salida', '10.0.0.31', 'PEL-SAL-01', 'Salida',
        )
        self.ctrl_cochera = _punto_y_controlador(
            self.cochera, self.pellegrini, 'Barrera cochera', '10.0.0.30', 'PEL-COC-01', 'Entrada',
        )
        self.ctrl_oficinas = _punto_y_controlador(
            self.ingreso_of, self.oficinas, 'Tótem oficinas', '10.0.0.20', 'OF-ING-01',
        )

        self.residente = SujetoAcceso.objects.create(
            nombre='María',
            apellido='Gómez',
            dni=111,
            email='maria@test.local',
            nivel_acceso=self.nivel_residente,
            edificio=self.pellegrini,
        )
        self.tag_res = Credencial.objects.create(
            codigo_referencia='TAG-PEL',
            fecha_vencimiento=date.today() + timedelta(days=30),
            persona=self.residente,
        )
        self.encargado = SujetoAcceso.objects.create(
            nombre='Carlos',
            apellido='Encargado',
            dni=222,
            email='carlos@test.local',
            nivel_acceso=self.nivel_encargado,
            edificio=self.pellegrini,
        )
        Credencial.objects.create(
            codigo_referencia='TAG-ENC',
            fecha_vencimiento=date.today() + timedelta(days=30),
            persona=self.encargado,
        )
        self.empleado_of = SujetoAcceso.objects.create(
            nombre='Laura',
            apellido='Benítez',
            dni=333,
            email='laura@test.local',
            nivel_acceso=self.nivel_oficinas,
            edificio=self.oficinas,
        )
        Credencial.objects.create(
            codigo_referencia='TAG-OF',
            fecha_vencimiento=date.today() + timedelta(days=30),
            persona=self.empleado_of,
        )
        self.nivel_tecnico = NivelAcceso.objects.create(nombre_nivel='Técnico de servicio')
        self.nivel_tecnico.zonas.add(self.raiz_pel, self.ingreso_of)
        self.tecnico = SujetoAcceso.objects.create(
            nombre='Sofía',
            apellido='Ruiz',
            dni=555,
            email='sofia@test.local',
            nivel_acceso=self.nivel_tecnico,
            edificio=None,
        )
        Credencial.objects.create(
            codigo_referencia='TAG-TEC',
            fecha_vencimiento=date.today() + timedelta(days=30),
            persona=self.tecnico,
        )
        self.motor = MotorValidacionAcceso()
        self.lunes_10 = datetime(2026, 9, 7, 10, 0, tzinfo=TZ)
        self.domingo_10 = datetime(2026, 9, 6, 10, 0, tzinfo=TZ)

    def test_residente_entra_a_su_edificio(self):
        r = self.motor.evaluar('TAG-PEL', '199.1.1.0', ahora=self.lunes_10)
        self.assertTrue(r.concedido)
        self.assertEqual(r.accion, 'ABRIR_PUERTA')

    def test_residente_no_entra_a_otro_edificio(self):
        r = self.motor.evaluar('TAG-PEL', '10.0.0.20', ahora=self.lunes_10)
        self.assertFalse(r.concedido)
        self.assertEqual(r.motivo, 'edificio no autorizado')

    def test_residente_no_entra_a_cochera(self):
        r = self.motor.evaluar('TAG-PEL', '10.0.0.30', ahora=self.lunes_10)
        self.assertFalse(r.concedido)
        self.assertIn('zona no permitida', r.motivo)

    def test_encargado_entra_a_cochera_por_composite(self):
        self.assertTrue(zona_esta_permitida(self.cochera, self.nivel_encargado))
        r = self.motor.evaluar('TAG-ENC', '10.0.0.30', ahora=self.lunes_10)
        self.assertTrue(r.concedido)

    def test_tecnico_sin_edificio_entra_en_ambos_sitios(self):
        en_pellegrini = self.motor.evaluar('TAG-TEC', '199.1.1.0', ahora=self.lunes_10)
        en_oficinas = self.motor.evaluar('TAG-TEC', '10.0.0.20', ahora=self.lunes_10)
        self.assertTrue(en_pellegrini.concedido)
        self.assertTrue(en_oficinas.concedido)

    def test_residente_fuera_de_horario(self):
        r = self.motor.evaluar('TAG-PEL', '199.1.1.0', ahora=self.domingo_10)
        self.assertFalse(r.concedido)
        self.assertEqual(r.motivo, 'fuera de horario permitido')

    def test_tarjeta_inexistente(self):
        r = self.motor.evaluar('NO-EXISTE', '199.1.1.0', ahora=self.lunes_10)
        self.assertFalse(r.concedido)
        self.assertEqual(r.motivo, 'tarjeta inexistente')

    def test_tarjeta_bloqueada(self):
        self.tag_res.estado = 'Bloqueada'
        self.tag_res.save()
        r = self.motor.evaluar('TAG-PEL', '199.1.1.0', ahora=self.lunes_10)
        self.assertEqual(r.motivo, 'tarjeta bloqueada')

    def test_dispositivo_desconocido(self):
        r = self.motor.evaluar('TAG-PEL', '1.2.3.4', ahora=self.lunes_10)
        self.assertEqual(r.motivo, 'dispositivo no encontrado')
        self.assertIsNone(r.dispositivo)


class TotemApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        MotorReglasTests.setUp(self)
        self.operador = OperadorSistema.objects.create(
            nombre='Lucía',
            apellido='Op',
            dni=444,
            email='op@test.local',
            username='operador',
            password_hash=make_password('apl2026'),
            turno_asignado='Tarde',
        )

    def test_lectura_concedida_persiste_registro(self):
        with timezone.override(TZ):
            respuesta = self.client.post(
                '/api/totem/lectura/',
                {'codigo_rfid': 'TAG-ENC', 'ip_totem': '199.1.1.0'},
                format='json',
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['accion'], 'ABRIR_PUERTA')
        self.assertEqual(RegistroAcceso.objects.filter(resultado='concedido').count(), 1)
        movimiento = RegistroAcceso.objects.get()
        self.assertEqual(movimiento.sentido, 'Entrada')

    def test_lectura_de_salida(self):
        respuesta = self.client.post(
            '/api/totem/lectura/',
            {'codigo_rfid': 'TAG-ENC', 'ip_totem': '10.0.0.31'},
            format='json',
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['sentido'], 'Salida')
        self.assertEqual(RegistroAcceso.objects.get().sentido, 'Salida')

    def test_lectura_en_edificio_ajeno_genera_alerta(self):
        respuesta = self.client.post(
            '/api/totem/lectura/',
            {'codigo_rfid': 'TAG-PEL', 'ip_totem': '10.0.0.20'},
            format='json',
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta.data['motivo'], 'edificio no autorizado')
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
            dispositivo=self.ctrl_ingreso,
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

    def test_abm_llave_bloquear_cambiar_codigo_y_borrar_cliente(self):
        sujeto_id = self.residente.pk
        llave_id = self.tag_res.pk
        cambio = self.client.patch(
            f'/api/sujetos/{sujeto_id}/',
            {
                'codigo_referencia': 'TAG-PEL-NUEVO',
                'estado_llave': 'Bloqueada',
                'edificio': self.pellegrini.pk,
                'nivel_acceso': self.nivel_residente.pk,
            },
            format='json',
        )
        self.assertEqual(cambio.status_code, 200)
        self.tag_res.refresh_from_db()
        self.assertEqual(self.tag_res.codigo_referencia, 'TAG-PEL-NUEVO')
        self.assertEqual(self.tag_res.estado, 'Bloqueada')

        baja_llave = self.client.delete(f'/api/credenciales/{llave_id}/')
        self.assertEqual(baja_llave.status_code, 204)
        self.assertFalse(Credencial.objects.filter(pk=llave_id).exists())

        baja_cliente = self.client.delete(f'/api/sujetos/{sujeto_id}/')
        self.assertEqual(baja_cliente.status_code, 204)
        self.assertFalse(SujetoAcceso.objects.filter(pk=sujeto_id).exists())
