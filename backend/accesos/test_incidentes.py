from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from rest_framework.test import APIClient

from accesos.models import (
    AlertaSeguridad,
    ComponenteZona,
    ControladorAcceso,
    CuentaSistema,
    Edificio,
    IncidenteTecnico,
    OperadorSistema,
    OrdenIntervencion,
    Persona,
    PuntoAcceso,
)


class IncidentesApiTests(TestCase):
    def setUp(self):
        self.edificio = Edificio.objects.create(nombre='Edificio A', direccion='Rosario')
        self.otro_edificio = Edificio.objects.create(nombre='Edificio B', direccion='Rosario')
        self.controlador = self._controlador(self.edificio, 'A-01', '10.20.0.1')
        self.otro_controlador = self._controlador(
            self.otro_edificio, 'B-01', '10.20.0.2'
        )
        self.alerta = AlertaSeguridad.objects.create(
            tipo_alerta='controladora desconectada',
            nivel_gravedad='Alta',
            estado_atencion='Pendiente',
            dispositivo=self.controlador,
        )
        self.alerta_otro_edificio = AlertaSeguridad.objects.create(
            tipo_alerta='puerta forzada',
            nivel_gravedad='Critica',
            dispositivo=self.otro_controlador,
        )

        self.operador = OperadorSistema.objects.create(
            nombre='Olivia', apellido='Operadora', dni=71001,
            email='operador-inc@test.local', username='op-inc',
            password_hash='', turno_asignado='Mañana',
        )
        self.usuario_operador = User.objects.create_user('op-inc', password='clave')
        self.cuenta_operador = CuentaSistema.objects.create(
            usuario=self.usuario_operador, persona=self.operador, rol='Operador'
        )
        self.cuenta_tecnico = self._tecnico('tec-uno', 72001)
        self.cuenta_otro_tecnico = self._tecnico('tec-dos', 72002)

        self.cliente_operador = APIClient()
        self.cliente_operador.force_login(self.usuario_operador)
        self.cliente_tecnico = APIClient()
        self.cliente_tecnico.force_login(self.cuenta_tecnico.usuario)
        self.cliente_otro_tecnico = APIClient()
        self.cliente_otro_tecnico.force_login(self.cuenta_otro_tecnico.usuario)

    def _controlador(self, edificio, serie, ip):
        zona = ComponenteZona.objects.create(
            nombre_zona=f'Zona {serie}', edificio=edificio
        )
        punto = PuntoAcceso.objects.create(
            descripcion=f'Punto {serie}', ubicacion_fisica='Hall', zona=zona
        )
        return ControladorAcceso.objects.create(
            numero_serie=serie, direccion_ip=ip, punto_acceso=punto, edificio=edificio
        )

    def _tecnico(self, username, dni):
        persona = Persona.objects.create(
            nombre='Técnico', apellido=username, dni=dni,
            email=f'{username}@test.local',
        )
        usuario = User.objects.create_user(username, password='clave')
        return CuentaSistema.objects.create(
            usuario=usuario, persona=persona, rol='Tecnico'
        )

    def _registrar(self, **extras):
        datos = {
            'edificio': self.edificio.pk,
            'dispositivo': self.controlador.pk,
            'descripcion': 'Lector intermitente',
            'categoria': 'Hardware',
            'prioridad': 'Alta',
        }
        datos.update(extras)
        return self.cliente_operador.post('/api/incidentes/', datos, format='json')

    def _evaluar_y_asignar(self, tecnico=None, **extras):
        respuesta = self._registrar(**extras)
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        incidente_id = respuesta.data['id']
        self.assertEqual(
            self.cliente_operador.post(
                f'/api/incidentes/{incidente_id}/evaluar/', {}, format='json'
            ).status_code,
            200,
        )
        respuesta = self.cliente_operador.post(
            f'/api/incidentes/{incidente_id}/asignar/',
            {'tecnico': (tecnico or self.cuenta_tecnico).pk},
            format='json',
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        return IncidenteTecnico.objects.get(pk=incidente_id), OrdenIntervencion.objects.get(
            pk=respuesta.data['id']
        )

    def _informar(self, orden, resultado='solucionado'):
        self.assertEqual(
            self.cliente_tecnico.post(
                f'/api/ordenes/{orden.pk}/iniciar/', {}, format='json'
            ).status_code,
            200,
        )
        return self.cliente_tecnico.post(
            f'/api/ordenes/{orden.pk}/informar/',
            {
                'diagnostico': 'Fuente dañada',
                'trabajo_realizado': 'Se reemplazó la fuente',
                'resultado': resultado,
            },
            format='json',
        )

    def test_permisos_anonimos_roles_y_propiedad(self):
        anonimo = APIClient()
        self.assertEqual(anonimo.get('/api/incidentes/').status_code, 401)
        self.assertEqual(anonimo.get('/api/ordenes/').status_code, 401)
        self.assertEqual(self.cliente_tecnico.get('/api/incidentes/').status_code, 403)
        self.assertEqual(self.cliente_tecnico.get('/api/alertas/').status_code, 403)
        self.assertEqual(self.cliente_tecnico.get('/api/tecnicos/').status_code, 403)

        _, orden = self._evaluar_y_asignar()
        propias = self.cliente_tecnico.get('/api/ordenes/')
        self.assertEqual(propias.status_code, 200)
        self.assertEqual([item['id'] for item in propias.data], [orden.pk])
        self.assertEqual(self.cliente_otro_tecnico.get('/api/ordenes/').data, [])
        self.assertEqual(
            self.cliente_otro_tecnico.post(
                f'/api/ordenes/{orden.pk}/iniciar/', {}, format='json'
            ).status_code,
            404,
        )
        self.assertEqual(
            self.cliente_operador.post(
                f'/api/ordenes/{orden.pk}/iniciar/', {}, format='json'
            ).status_code,
            403,
        )

    def test_coherencia_de_edificio_y_alerta_unica(self):
        respuesta = self._registrar(dispositivo=self.otro_controlador.pk)
        self.assertEqual(respuesta.status_code, 400)
        respuesta = self._registrar(alerta_origen=self.alerta_otro_edificio.pk)
        self.assertEqual(respuesta.status_code, 400)
        respuesta = self._registrar(alerta_origen=self.alerta.pk)
        self.assertEqual(respuesta.status_code, 201)
        duplicado = self._registrar(
            alerta_origen=self.alerta.pk, descripcion='Duplicado de alerta'
        )
        self.assertEqual(duplicado.status_code, 400)
        self.alerta.refresh_from_db()
        self.assertEqual(self.alerta.estado_atencion, 'Pendiente')

    def test_transiciones_invalidas_y_motivos_obligatorios(self):
        incidente = self._registrar().data
        self.assertEqual(
            self.cliente_operador.post(
                f"/api/incidentes/{incidente['id']}/asignar/",
                {'tecnico': self.cuenta_tecnico.pk}, format='json'
            ).status_code,
            400,
        )
        self.assertEqual(
            self.cliente_operador.post(
                f"/api/incidentes/{incidente['id']}/descartar/",
                {'motivo': ''}, format='json'
            ).status_code,
            400,
        )
        self.assertEqual(
            self.cliente_operador.post(
                f"/api/incidentes/{incidente['id']}/cerrar/", {}, format='json'
            ).status_code,
            400,
        )
        evaluado = self.cliente_operador.post(
            f"/api/incidentes/{incidente['id']}/evaluar/", {}, format='json'
        )
        self.assertEqual(evaluado.status_code, 200)
        self.cuenta_tecnico.activo = False
        self.cuenta_tecnico.save(update_fields=['activo'])
        self.assertEqual(
            self.cliente_operador.post(
                f"/api/incidentes/{incidente['id']}/asignar/",
                {'tecnico': self.cuenta_tecnico.pk}, format='json'
            ).status_code,
            400,
        )
        self.cuenta_tecnico.activo = True
        self.cuenta_tecnico.save(update_fields=['activo'])
        _, orden = self._evaluar_y_asignar(descripcion='Otro incidente')
        informe_anticipado = self.cliente_tecnico.post(
            f'/api/ordenes/{orden.pk}/informar/',
            {'diagnostico': 'x', 'trabajo_realizado': 'y', 'resultado': 'solucionado'},
            format='json',
        )
        self.assertEqual(informe_anticipado.status_code, 400)
        self.assertEqual(
            self.cliente_operador.post(
                f'/api/ordenes/{orden.pk}/cancelar/', {'motivo': ''}, format='json'
            ).status_code,
            400,
        )
        self.cliente_tecnico.post(f'/api/ordenes/{orden.pk}/iniciar/', {}, format='json')
        incompleto = self.cliente_tecnico.post(
            f'/api/ordenes/{orden.pk}/informar/',
            {'diagnostico': '', 'trabajo_realizado': '', 'resultado': 'solucionado'},
            format='json',
        )
        self.assertEqual(incompleto.status_code, 400)

    def test_intervencion_satisfactoria_y_cierre_independiente(self):
        incidente, orden = self._evaluar_y_asignar(alerta_origen=self.alerta.pk)
        self.assertEqual(self._informar(orden).status_code, 200)
        verificacion = self.cliente_operador.post(
            f'/api/ordenes/{orden.pk}/verificar/',
            {'aceptada': True, 'observaciones': 'Prueba funcional correcta'},
            format='json',
        )
        self.assertEqual(verificacion.status_code, 200, verificacion.data)
        incidente.refresh_from_db()
        self.alerta.refresh_from_db()
        self.assertEqual(incidente.estado, 'Pendiente verificacion')
        self.assertEqual(self.alerta.estado_atencion, 'Pendiente')

        cierre = self.cliente_operador.post(
            f'/api/incidentes/{incidente.pk}/cerrar/', {}, format='json'
        )
        self.assertEqual(cierre.status_code, 200, cierre.data)
        incidente.refresh_from_db()
        self.alerta.refresh_from_db()
        self.assertEqual(incidente.estado, 'Cerrado')
        self.assertEqual(self.alerta.estado_atencion, 'Pendiente')
        self.assertGreaterEqual(incidente.cambios_estado.count(), 5)
        self.assertEqual(orden.cambios_estado.count(), 4)

    def test_rechazo_habilita_segunda_intervencion(self):
        incidente, primera = self._evaluar_y_asignar()
        self.assertEqual(
            self._informar(primera, 'parcialmente solucionado').status_code, 200
        )
        self.assertEqual(
            self.cliente_operador.post(
                f'/api/ordenes/{primera.pk}/reasignar/',
                {'tecnico': self.cuenta_otro_tecnico.pk, 'motivo': 'Demasiado tarde'},
                format='json',
            ).status_code,
            400,
        )
        aceptacion_invalida = self.cliente_operador.post(
            f'/api/ordenes/{primera.pk}/verificar/',
            {'aceptada': True, 'observaciones': 'Quedó parcial'}, format='json'
        )
        self.assertEqual(aceptacion_invalida.status_code, 400)
        rechazo = self.cliente_operador.post(
            f'/api/ordenes/{primera.pk}/verificar/',
            {'aceptada': False, 'observaciones': 'Persisten fallas'}, format='json'
        )
        self.assertEqual(rechazo.status_code, 200, rechazo.data)
        primera.refresh_from_db()
        incidente.refresh_from_db()
        self.assertEqual(primera.estado, 'Verificada')
        self.assertFalse(primera.verificacion_aceptada)
        self.assertEqual(incidente.estado, 'Evaluado')

        segunda = self.cliente_operador.post(
            f'/api/incidentes/{incidente.pk}/asignar/',
            {'tecnico': self.cuenta_otro_tecnico.pk}, format='json'
        )
        self.assertEqual(segunda.status_code, 201, segunda.data)
        self.assertEqual(segunda.data['numero'], 2)
        self.assertEqual(incidente.ordenes.count(), 2)

        with self.assertRaises(IntegrityError), transaction.atomic():
            OrdenIntervencion.objects.create(
                incidente=incidente,
                numero=3,
                tecnico=self.cuenta_tecnico,
                asignada_por=self.operador,
            )

    def test_reasignacion_cancelacion_e_historial(self):
        incidente, orden = self._evaluar_y_asignar()
        sin_motivo = self.cliente_operador.post(
            f'/api/ordenes/{orden.pk}/reasignar/',
            {'tecnico': self.cuenta_otro_tecnico.pk, 'motivo': ''}, format='json'
        )
        self.assertEqual(sin_motivo.status_code, 400)
        respuesta = self.cliente_operador.post(
            f'/api/ordenes/{orden.pk}/reasignar/',
            {'tecnico': self.cuenta_otro_tecnico.pk, 'motivo': 'Cambio de guardia'},
            format='json',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        orden.refresh_from_db()
        self.assertEqual(orden.tecnico, self.cuenta_otro_tecnico)
        self.assertEqual(orden.historial_asignaciones.count(), 2)
        self.assertEqual(
            orden.historial_asignaciones.last().motivo, 'Cambio de guardia'
        )
        cancelacion = self.cliente_operador.post(
            f'/api/ordenes/{orden.pk}/cancelar/',
            {'motivo': 'Cliente reprogramó la visita'}, format='json'
        )
        self.assertEqual(cancelacion.status_code, 200, cancelacion.data)
        incidente.refresh_from_db()
        self.assertEqual(incidente.estado, 'Evaluado')
        self.assertEqual(
            self.cliente_operador.post(
                f'/api/ordenes/{orden.pk}/reasignar/',
                {'tecnico': self.cuenta_tecnico.pk, 'motivo': 'Intento inválido'},
                format='json',
            ).status_code,
            400,
        )

    def test_incidente_posterior_exige_antecedente_cerrado_y_protege_historia(self):
        incidente, orden = self._evaluar_y_asignar()
        invalido = self._registrar(
            descripcion='Reincidencia prematura', incidente_anterior=incidente.pk
        )
        self.assertEqual(invalido.status_code, 400)
        self.assertEqual(self._informar(orden).status_code, 200)
        self.cliente_operador.post(
            f'/api/ordenes/{orden.pk}/verificar/',
            {'aceptada': True, 'observaciones': 'Correcto'}, format='json'
        )
        self.cliente_operador.post(
            f'/api/incidentes/{incidente.pk}/cerrar/', {}, format='json'
        )
        posterior = self._registrar(
            descripcion='Falla posterior', incidente_anterior=incidente.pk
        )
        self.assertEqual(posterior.status_code, 201, posterior.data)
        with self.assertRaises(ProtectedError):
            self.cuenta_tecnico.delete()


class IncidentesDemoTests(TestCase):
    def test_seed_incidentes_es_idempotente(self):
        salida = StringIO()
        call_command('seed_demo', stdout=salida)
        call_command('seed_incidentes_demo', stdout=salida)
        cantidades = (IncidenteTecnico.objects.count(), OrdenIntervencion.objects.count())
        call_command('seed_incidentes_demo', stdout=salida)
        self.assertEqual(
            cantidades,
            (IncidenteTecnico.objects.count(), OrdenIntervencion.objects.count()),
        )
