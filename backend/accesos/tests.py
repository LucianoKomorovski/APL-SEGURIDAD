from datetime import date, datetime, time, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accesos.models import (
    AlertaSeguridad,
    ComponenteZona,
    ControladorAcceso,
    Credencial,
    CuentaSistema,
    Edificio,
    HorarioPermitido,
    NivelAcceso,
    OperadorSistema,
    Presencia,
    MovimientoCredencial,
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
        self.usuario_operador = User.objects.create_user(
            username='operador', password='apl2026', email=self.operador.email,
        )
        self.cuenta_operador = CuentaSistema.objects.create(
            usuario=self.usuario_operador,
            persona=self.operador,
            rol='Operador',
        )
        self.client.force_login(self.usuario_operador)

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
        self.client.logout()
        ok = self.client.post(
            '/api/auth/login/',
            {'username': 'operador', 'password': 'apl2026'},
            format='json',
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()['rol'], 'Operador')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)
        salida = self.client.post('/api/auth/logout/')
        self.assertEqual(salida.status_code, 204)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)
        fail = self.client.post(
            '/api/auth/login/',
            {'username': 'operador', 'password': 'mala'},
            format='json',
        )
        self.assertEqual(fail.status_code, 401)

    def test_csrf_es_obligatorio_en_login_y_logout(self):
        cliente = APIClient(enforce_csrf_checks=True)
        self.assertEqual(cliente.post('/api/auth/login/', {
            'username': 'operador', 'password': 'apl2026',
        }, format='json').status_code, 403)
        self.assertEqual(cliente.get('/api/auth/csrf/').status_code, 200)
        token = cliente.cookies['csrftoken'].value
        login_ok = cliente.post('/api/auth/login/', {
            'username': 'operador', 'password': 'apl2026',
        }, format='json', HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN='http://127.0.0.1:5173')
        self.assertEqual(login_ok.status_code, 200)
        self.assertEqual(cliente.post('/api/auth/logout/').status_code, 403)
        token = cliente.cookies['csrftoken'].value
        self.assertEqual(
            cliente.post('/api/auth/logout/', HTTP_X_CSRFTOKEN=token).status_code,
            204,
        )

    def test_anonimo_no_accede_a_la_administracion(self):
        self.client.logout()
        for path in [
            '/api/', '/api/sujetos/', '/api/credenciales/', '/api/edificios/',
            '/api/zonas/', '/api/niveles/', '/api/horarios/',
            '/api/puntos-acceso/', '/api/controladores/', '/api/registros/',
            '/api/alertas/',
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)

    def test_tecnico_solo_accede_a_su_sesion(self):
        usuario = User.objects.create_user(username='tecnico', password='apl2026')
        CuentaSistema.objects.create(usuario=usuario, persona=self.tecnico, rol='Tecnico')
        alerta = AlertaSeguridad.objects.create(
            tipo_alerta='puerta forzada', nivel_gravedad='Alta',
            dispositivo=self.ctrl_ingreso,
        )
        self.client.logout()
        acceso = self.client.post('/api/auth/login/', {
            'username': 'tecnico', 'password': 'apl2026',
        }, format='json')
        self.assertEqual(acceso.status_code, 200)
        self.assertEqual(acceso.json()['rol'], 'Tecnico')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)
        for path in ['/api/', '/api/sujetos/', '/api/credenciales/', '/api/alertas/', '/api/registros/']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)
        resolver = self.client.post(
            f'/api/alertas/{alerta.pk}/resolver/',
            {'observaciones': 'No autorizado'},
            format='json',
        )
        self.assertEqual(resolver.status_code, 403)
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado_atencion, 'Pendiente')

    def test_credencial_fisica_no_autentica_en_el_sistema(self):
        self.client.logout()
        self.assertTrue(Credencial.objects.filter(codigo_referencia='TAG-TEC').exists())
        self.assertEqual(self.client.get('/api/alertas/').status_code, 401)

    def test_sesion_invalida_se_rechaza_y_hardware_sigue_disponible(self):
        cliente = APIClient()
        cliente.cookies['sessionid'] = 'sesion-invalida'
        self.assertEqual(cliente.get('/api/auth/me/').status_code, 401)
        lectura = cliente.post('/api/totem/lectura/', {
            'codigo_rfid': 'TAG-ENC', 'ip_totem': '199.1.1.0',
        }, format='json')
        self.assertEqual(lectura.status_code, 200)
        self.assertEqual(lectura.data['accion'], 'ABRIR_PUERTA')

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

    def test_entradas_repetidas_no_crean_presencia_ni_alertas(self):
        for _ in range(2):
            respuesta = self.client.post('/api/totem/lectura/', {
                'codigo_rfid': 'TAG-ENC', 'ip_totem': '199.1.1.0',
            }, format='json')
            self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(RegistroAcceso.objects.filter(resultado='concedido').count(), 2)
        self.assertFalse(Presencia.objects.exists())
        self.assertFalse(AlertaSeguridad.objects.exists())

    def test_presencia_historica_no_se_actualiza_ni_genera_permanencia(self):
        presencia = Presencia.objects.create(
            sujeto=self.encargado, edificio=self.pellegrini,
            ingreso=timezone.now() - timedelta(days=3),
            credencial=Credencial.objects.get(codigo_referencia='TAG-ENC'),
        )
        antes = list(Presencia.objects.values())
        alerta = AlertaSeguridad.objects.create(
            tipo_alerta='permanencia excedida', nivel_gravedad='Media',
            dispositivo=self.ctrl_ingreso,
        )
        for ip in ['199.1.1.0', '10.0.0.31']:
            respuesta = self.client.post('/api/totem/lectura/', {
                'codigo_rfid': 'TAG-ENC', 'ip_totem': ip,
            }, format='json')
            self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.client.get('/api/presencias/?abiertas=1').status_code, 404)
        for url in ['/api/alertas/', '/api/registros/', '/api/edificios/']:
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(list(Presencia.objects.values()), antes)
        self.assertEqual(list(AlertaSeguridad.objects.values_list('pk', flat=True)), [alerta.pk])
        self.assertTrue(Presencia.objects.filter(pk=presencia.pk).exists())

    def test_credenciales_historicas_siguen_denegadas_y_no_se_reactivan(self):
        for estado, motivo in [('Emitida', 'credencial sin entregar'), ('Repuesta', 'credencial reemplazada')]:
            with self.subTest(estado=estado):
                self.tag_res.estado = estado
                self.tag_res.save(update_fields=['estado'])
                lectura = self.client.post('/api/totem/lectura/', {
                    'codigo_rfid': self.tag_res.codigo_referencia, 'ip_totem': '199.1.1.0',
                }, format='json')
                self.assertEqual(lectura.status_code, 403)
                self.assertEqual(lectura.data['motivo'], motivo)
                for destino in Credencial.ESTADOS_OPERATIVOS:
                    respuesta = self.client.patch(f'/api/credenciales/{self.tag_res.pk}/',
                                                 {'estado': destino}, format='json')
                    self.assertEqual(respuesta.status_code, 400)
                respuesta = self.client.patch(f'/api/sujetos/{self.residente.pk}/', {
                    'estado_llave': 'Activa', 'nombre': 'No debe guardarse',
                }, format='json')
                self.assertEqual(respuesta.status_code, 400)
                self.tag_res.refresh_from_db()
                self.residente.refresh_from_db()
                self.assertEqual(self.tag_res.estado, estado)
                self.assertNotEqual(self.residente.nombre, 'No debe guardarse')
                respuesta = self.client.put(f'/api/credenciales/{self.tag_res.pk}/', {
                    'codigo_referencia': self.tag_res.codigo_referencia,
                    'fecha_vencimiento': self.tag_res.fecha_vencimiento.isoformat(),
                    'persona': self.residente.pk, 'estado': 'Activa',
                }, format='json')
                self.assertEqual(respuesta.status_code, 400)

    def test_rutas_del_ciclo_retiradas(self):
        for accion in ['entregar', 'declarar-perdida', 'reponer', 'vencer']:
            respuesta = self.client.post(f'/api/credenciales/{self.tag_res.pk}/{accion}/',
                                         {'codigo_referencia': 'OTRA', 'motivo': 'Prueba'}, format='json')
            self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(MovimientoCredencial.objects.exists())

    def test_alta_y_bloqueo_basicos_sin_entrega(self):
        alta = self.client.post('/api/sujetos/', {
            'nombre': 'Nueva', 'apellido': 'Persona', 'dni': 999,
            'email': 'nueva@test.local', 'edificio': self.pellegrini.pk,
            'nivel_acceso': self.nivel_encargado.pk, 'codigo_referencia': 'TAG-NUEVA',
        }, format='json')
        self.assertEqual(alta.status_code, 201)
        llave = Credencial.objects.get(codigo_referencia='TAG-NUEVA')
        self.assertEqual(llave.estado, 'Activa')
        for estado, status in [('Bloqueada', 403), ('Activa', 200), ('Vencida', 403)]:
            cambio = self.client.patch(f'/api/credenciales/{llave.pk}/', {'estado': estado}, format='json')
            self.assertEqual(cambio.status_code, 200)
            lectura = self.client.post('/api/totem/lectura/', {
                'codigo_rfid': 'TAG-NUEVA', 'ip_totem': '199.1.1.0',
            }, format='json')
            self.assertEqual(lectura.status_code, status)
        extra = self.client.post(f'/api/sujetos/{alta.data["id"]}/llaves/',
                                 {'codigo_referencia': 'TAG-EXTRA'}, format='json')
        self.assertEqual(extra.status_code, 201)
        self.assertEqual(extra.data['estado'], 'Activa')
        self.assertFalse(MovimientoCredencial.objects.exists())

    def test_no_se_crean_estados_retirados_por_crud(self):
        for estado in Credencial.ESTADOS_HISTORICOS:
            datos = {'codigo_referencia': f'TAG-{estado}', 'persona': self.residente.pk,
                     'fecha_vencimiento': '2030-01-01', 'estado': estado}
            self.assertEqual(self.client.post('/api/credenciales/', datos, format='json').status_code, 400)
            self.assertEqual(self.client.patch(f'/api/credenciales/{self.tag_res.pk}/',
                                              {'estado': estado}, format='json').status_code, 400)

    def test_metadata_e_historial_del_ciclo_son_solo_lectura(self):
        self.tag_res.estado = 'Repuesta'
        self.tag_res.motivo_estado = 'Histórico'
        self.tag_res.save()
        movimiento = MovimientoCredencial.objects.create(
            credencial=self.tag_res, estado_origen='Activa', estado_destino='Repuesta',
        )
        respuesta = self.client.patch(f'/api/credenciales/{self.tag_res.pk}/', {
            'motivo_estado': 'Sobrescrito', 'fecha_entrega': timezone.now().isoformat(),
            'reemplaza': self.tag_res.pk, 'movimientos': [],
        }, format='json')
        self.assertEqual(respuesta.status_code, 200)
        self.tag_res.refresh_from_db()
        self.assertEqual(self.tag_res.motivo_estado, 'Histórico')
        self.assertIsNone(self.tag_res.fecha_entrega)
        self.assertIsNone(self.tag_res.reemplaza_id)
        self.assertEqual(respuesta.data['movimientos'][0]['id'], movimiento.pk)

    def test_admin_no_ofrece_entrega_ni_reactivacion_historica(self):
        from accesos.admin import CredencialForm, site
        self.tag_res.estado = 'Emitida'
        self.tag_res.save(update_fields=['estado'])
        form = CredencialForm(instance=self.tag_res)
        self.assertEqual(list(form.fields['estado'].choices), [('Emitida', 'Emitida')])
        datos = {'codigo_referencia': self.tag_res.codigo_referencia, 'tipo': self.tag_res.tipo,
                 'fecha_vencimiento': '2030-01-01', 'persona': self.residente.pk, 'estado': 'Activa'}
        form = CredencialForm(data=datos, instance=self.tag_res)
        self.assertFalse(form.is_valid())
        self.assertIn('estado', form.errors)
        self.assertEqual([value for value, _ in CredencialForm().fields['estado'].choices],
                         list(Credencial.ESTADOS_OPERATIVOS))
        for model in [Presencia, MovimientoCredencial]:
            archivo = site._registry[model]
            self.assertFalse(archivo.has_add_permission(None))
            self.assertFalse(archivo.has_change_permission(None))
            self.assertFalse(archivo.has_delete_permission(None))

    def test_filtros_utiles_y_alertas_se_conservan(self):
        for dispositivo in [self.ctrl_ingreso, ControladorAcceso.objects.get(direccion_ip='10.0.0.20')]:
            RegistroAcceso.objects.create(dispositivo=dispositivo, credencial=self.tag_res,
                                         resultado='concedido', sentido='Entrada')
            AlertaSeguridad.objects.create(dispositivo=dispositivo, tipo_alerta='puerta forzada',
                                          nivel_gravedad='Alta')
        registros = self.client.get(f'/api/registros/?edificio={self.pellegrini.pk}&hoy=1')
        self.assertEqual(len(registros.data), 1)
        alertas = self.client.get(f'/api/alertas/?edificio={self.pellegrini.pk}&abiertas=1')
        self.assertEqual(len(alertas.data), 1)
        self.assertEqual(alertas.data[0]['edificio_id'], self.pellegrini.pk)

    def test_fecha_vencida_y_sujeto_inactivo_siguen_denegados(self):
        self.tag_res.fecha_vencimiento = date(2020, 1, 1)
        self.tag_res.save()
        resultado = self.motor.evaluar(self.tag_res.codigo_referencia, '199.1.1.0', ahora=self.lunes_10)
        self.assertEqual(resultado.motivo, 'tarjeta vencida')
        self.tag_res.fecha_vencimiento = date(2030, 1, 1)
        self.tag_res.save()
        self.residente.estado = 'Inactivo'
        self.residente.save()
        resultado = self.motor.evaluar(self.tag_res.codigo_referencia, '199.1.1.0', ahora=self.lunes_10)
        self.assertEqual(resultado.motivo, 'sujeto inactivo')

    def test_seed_no_crea_ciclo_ni_reactiva_credenciales_existentes(self):
        call_command('seed_demo', stdout=StringIO())
        llave = Credencial.objects.get(codigo_referencia='TAG-PEL-01')
        llave.estado = 'Repuesta'
        llave.save(update_fields=['estado'])
        call_command('seed_demo', stdout=StringIO())
        llave.refresh_from_db()
        self.assertEqual(llave.estado, 'Repuesta')
        self.assertFalse(Credencial.objects.filter(estado='Emitida').exists())
        self.assertFalse(Presencia.objects.exists())
        self.assertFalse(MovimientoCredencial.objects.exists())
