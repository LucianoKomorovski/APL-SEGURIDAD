import json
from datetime import timedelta

from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_POST
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    AlertaSeguridad,
    ComponenteZona,
    ControladorAcceso,
    Credencial,
    CuentaSistema,
    Edificio,
    HorarioPermitido,
    IncidenteTecnico,
    NivelAcceso,
    OperadorSistema,
    OrdenIntervencion,
    PuntoAcceso,
    RegistroAcceso,
    ResolucionAlerta,
    SujetoAcceso,
)
from .incidentes import (
    ReglaIncidente,
    asignar_intervencion,
    cancelar_orden,
    cerrar_incidente,
    descartar_incidente,
    evaluar_incidente,
    informar_orden,
    iniciar_orden,
    reasignar_orden,
    registrar_incidente,
    verificar_orden,
)
from .motor_reglas import MotorValidacionAcceso
from .permissions import EsOperador, EsTecnico, EsUsuarioSGCA, cuenta_activa
from .serializers import (
    AlertaSeguridadSerializer,
    ComponenteZonaSerializer,
    ControladorAccesoSerializer,
    CredencialSerializer,
    EdificioSerializer,
    HorarioPermitidoSerializer,
    IncidenteCrearSerializer,
    IncidenteTecnicoSerializer,
    NivelAccesoSerializer,
    OrdenIntervencionSerializer,
    PuntoAccesoSerializer,
    RegistroAccesoSerializer,
    SujetoAccesoSerializer,
    TecnicoSerializer,
)


def _marcar_controlador_en_linea(dispositivo):
    dispositivo.estado_conexion = 'En linea'
    dispositivo.fecha_ultimo_ping = timezone.now()
    dispositivo.save(update_fields=['estado_conexion', 'fecha_ultimo_ping'])


class OperadorModelViewSet(viewsets.ModelViewSet):
    permission_classes = [EsOperador]


class SujetoAccesoViewSet(OperadorModelViewSet):
    queryset = SujetoAcceso.objects.select_related('nivel_acceso', 'edificio').prefetch_related(
        'credenciales',
    ).all()
    serializer_class = SujetoAccesoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        edificio = _id_query(self.request, 'edificio')
        if edificio:
            qs = qs.filter(Q(edificio_id=edificio) | Q(edificio__isnull=True))
        return qs

    def _resolver_edificio_y_nivel(self, data):
        edificio_obj = None
        edificio_id = data.get('edificio')
        if edificio_id not in (None, '', 'null'):
            try:
                edificio_obj = Edificio.objects.get(pk=edificio_id)
            except (Edificio.DoesNotExist, ValueError, TypeError):
                return None, None, Response({"error": "Edificio no encontrado"}, status=400)

        nivel_obj = None
        nivel_id = data.get('nivel_acceso')
        if nivel_id not in (None, '', 'null'):
            try:
                nivel_obj = NivelAcceso.objects.get(pk=nivel_id)
            except (NivelAcceso.DoesNotExist, ValueError, TypeError):
                return None, None, Response({"error": "Nivel de acceso no encontrado"}, status=400)
        return edificio_obj, nivel_obj, None

    def create(self, request, *args, **kwargs):
        nombre = request.data.get('nombre')
        apellido = request.data.get('apellido')
        dni = request.data.get('dni')
        email = request.data.get('email')
        codigo_referencia = request.data.get('codigo_referencia')

        if not all([nombre, apellido, dni, email]):
            return Response(
                {"error": "Faltan datos obligatorios (nombre, apellido, dni, email)."},
                status=400,
            )

        edificio_obj, nivel_obj, error = self._resolver_edificio_y_nivel(request.data)
        if error:
            return error

        try:
            with transaction.atomic():
                sujeto = SujetoAcceso.objects.create(
                    nombre=nombre,
                    apellido=apellido,
                    dni=dni,
                    email=email,
                    telefono=request.data.get('telefono') or '',
                    legajo_empleado=request.data.get('legajo_empleado') or None,
                    edificio=edificio_obj,
                    nivel_acceso=nivel_obj,
                )

                if codigo_referencia:
                    Credencial.objects.create(
                        codigo_referencia=codigo_referencia,
                        tipo=request.data.get('tipo_credencial') or 'Magnetica',
                        fecha_vencimiento=timezone.now().date() + timedelta(days=365),
                        estado='Activa',
                        persona=sujeto,
                    )
        except IntegrityError as e:
            return Response(
                {"error": f"Datos duplicados o invalidos: {str(e)}"},
                status=400,
            )

        serializer = self.get_serializer(sujeto)
        return Response(serializer.data, status=201)

    def update(self, request, *args, **kwargs):
        sujeto = self.get_object()
        edificio_obj, nivel_obj, error = self._resolver_edificio_y_nivel(request.data)
        if error:
            return error
        try:
            with transaction.atomic():
                for campo in ('nombre', 'apellido', 'email', 'telefono', 'estado'):
                    if campo in request.data and request.data.get(campo) not in (None,):
                        setattr(sujeto, campo, request.data.get(campo))
                if 'dni' in request.data and request.data.get('dni') not in (None, ''):
                    sujeto.dni = request.data.get('dni')
                if 'edificio' in request.data:
                    sujeto.edificio = edificio_obj
                if 'nivel_acceso' in request.data:
                    sujeto.nivel_acceso = nivel_obj
                sujeto.save()

                codigo = request.data.get('codigo_referencia')
                estado = request.data.get('estado_llave')
                credencial = sujeto.credenciales.order_by('id').first()
                if credencial and (codigo or estado):
                    cambios = {}
                    if codigo:
                        cambios['codigo_referencia'] = codigo
                    if estado:
                        cambios['estado'] = estado
                    serializer = CredencialSerializer(credencial, data=cambios, partial=True)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                elif codigo and not credencial:
                    serializer = CredencialSerializer(data={
                        'codigo_referencia': codigo,
                        'tipo': request.data.get('tipo_credencial') or 'Magnetica',
                        'fecha_vencimiento': timezone.now().date() + timedelta(days=365),
                        'estado': estado or 'Activa',
                        'persona': sujeto.pk,
                    })
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
        except IntegrityError as e:
            return Response(
                {"error": f"Datos duplicados o invalidos: {str(e)}"},
                status=400,
            )

        sujeto.refresh_from_db()
        return Response(self.get_serializer(sujeto).data)

    @action(detail=True, methods=['post'], url_path='llaves')
    def agregar_llave(self, request, pk=None):
        sujeto = self.get_object()
        codigo = request.data.get('codigo_referencia')
        if not codigo:
            return Response({'error': 'Falta codigo_referencia'}, status=400)
        try:
            credencial = Credencial.objects.create(
                codigo_referencia=codigo,
                tipo=request.data.get('tipo_credencial') or 'Magnetica',
                fecha_vencimiento=timezone.now().date() + timedelta(days=365),
                estado='Activa',
                persona=sujeto,
            )
        except IntegrityError as e:
            return Response({'error': f'Llave duplicada: {e}'}, status=400)
        return Response(CredencialSerializer(credencial).data, status=201)


class PuntoAccesoViewSet(OperadorModelViewSet):
    queryset = PuntoAcceso.objects.select_related('zona').all()
    serializer_class = PuntoAccesoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        edificio = _id_query(self.request, 'edificio')
        if edificio:
            qs = qs.filter(zona__edificio_id=edificio)
        return qs


def _id_query(request, nombre):
    valor = request.query_params.get(nombre)
    if valor and str(valor).isdigit():
        return int(valor)
    return None


def _inicio_del_dia_local():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


class RegistroAccesoViewSet(OperadorModelViewSet):
    queryset = RegistroAcceso.objects.select_related(
        'credencial__persona',
        'dispositivo__punto_acceso__zona',
        'dispositivo__edificio',
    ).all()
    serializer_class = RegistroAccesoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        resultado = self.request.query_params.get('resultado')
        if resultado:
            qs = qs.filter(resultado=resultado)
        sentido = self.request.query_params.get('sentido')
        if sentido:
            qs = qs.filter(sentido=sentido)
        edificio = _id_query(self.request, 'edificio')
        if edificio:
            qs = qs.filter(dispositivo__edificio_id=edificio)
        if self.request.query_params.get('hoy') == '1':
            qs = qs.filter(fecha_hora__gte=_inicio_del_dia_local())
        return qs


class AlertaSeguridadViewSet(OperadorModelViewSet):
    queryset = AlertaSeguridad.objects.select_related(
        'dispositivo__punto_acceso__zona',
        'dispositivo__edificio',
        'resolucion',
        'incidente_tecnico',
    ).all()
    serializer_class = AlertaSeguridadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        edificio = _id_query(self.request, 'edificio')
        if edificio:
            qs = qs.filter(dispositivo__edificio_id=edificio)
        if self.request.query_params.get('abiertas') == '1':
            qs = qs.exclude(estado_atencion='Resuelta')
        return qs

    @action(detail=True, methods=['post'])
    def resolver(self, request, pk=None):
        alerta = self.get_object()
        if alerta.estado_atencion == 'Resuelta':
            return Response(self.get_serializer(alerta).data)

        observaciones = request.data.get('observaciones') or 'Resuelta desde el panel operativo.'
        operador = OperadorSistema.objects.get(pk=request.user.cuenta_sgca.persona_id)

        with transaction.atomic():
            alerta.estado_atencion = 'Resuelta'
            alerta.save(update_fields=['estado_atencion'])
            ResolucionAlerta.objects.update_or_create(
                alerta=alerta,
                defaults={
                    'observaciones': observaciones,
                    'operador': operador,
                },
            )

        alerta.refresh_from_db()
        return Response(self.get_serializer(alerta).data)


class EdificioViewSet(OperadorModelViewSet):
    queryset = Edificio.objects.all()
    serializer_class = EdificioSerializer


class NivelAccesoViewSet(OperadorModelViewSet):
    queryset = NivelAcceso.objects.prefetch_related('zonas', 'horarios').all()
    serializer_class = NivelAccesoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        edificio = _id_query(self.request, 'edificio')
        if edificio:
            qs = qs.filter(zonas__edificio_id=edificio).distinct()
        return qs


class ComponenteZonaViewSet(OperadorModelViewSet):
    queryset = ComponenteZona.objects.select_related('edificio', 'zona_padre').all()
    serializer_class = ComponenteZonaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        edificio = _id_query(self.request, 'edificio')
        if edificio:
            qs = qs.filter(edificio_id=edificio)
        return qs


class HorarioPermitidoViewSet(OperadorModelViewSet):
    queryset = HorarioPermitido.objects.select_related('nivel_acceso').all()
    serializer_class = HorarioPermitidoSerializer


class ControladorAccesoViewSet(OperadorModelViewSet):
    queryset = ControladorAcceso.objects.select_related(
        'punto_acceso__zona',
        'edificio',
    ).all()
    serializer_class = ControladorAccesoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        edificio = _id_query(self.request, 'edificio')
        if edificio:
            qs = qs.filter(edificio_id=edificio)
        return qs


class CredencialViewSet(OperadorModelViewSet):
    queryset = Credencial.objects.select_related('persona', 'reemplaza').prefetch_related(
        'movimientos',
    ).all()
    serializer_class = CredencialSerializer


def _respuesta_regla(funcion, **kwargs):
    try:
        return funcion(**kwargs), None
    except ReglaIncidente as exc:
        return None, Response({'error': str(exc)}, status=400)


class TecnicoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [EsOperador]
    serializer_class = TecnicoSerializer
    queryset = CuentaSistema.objects.select_related('usuario', 'persona').filter(
        rol='Tecnico', activo=True, usuario__is_active=True
    )


class IncidenteTecnicoViewSet(viewsets.GenericViewSet):
    permission_classes = [EsOperador]
    serializer_class = IncidenteTecnicoSerializer
    queryset = IncidenteTecnico.objects.select_related(
        'edificio', 'dispositivo', 'alerta_origen', 'registrado_por', 'incidente_anterior'
    ).prefetch_related(
        'cambios_estado__actor__persona',
        'ordenes__tecnico__persona',
        'ordenes__incidente__edificio',
        'ordenes__cambios_estado__actor__persona',
        'ordenes__historial_asignaciones__tecnico_anterior__persona',
        'ordenes__historial_asignaciones__tecnico_nuevo__persona',
    )

    def get_queryset(self):
        qs = super().get_queryset()
        edificio = _id_query(self.request, 'edificio')
        if edificio:
            qs = qs.filter(edificio_id=edificio)
        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    def list(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    def create(self, request):
        entrada = IncidenteCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        incidente, error = _respuesta_regla(
            registrar_incidente,
            cuenta=request.user.cuenta_sgca,
            edificio=datos['edificio'],
            descripcion=datos['descripcion'],
            categoria=datos['categoria'],
            prioridad=datos['prioridad'],
            dispositivo=datos.get('dispositivo'),
            alerta=datos.get('alerta_origen'),
            incidente_anterior=datos.get('incidente_anterior'),
        )
        if error:
            return error
        return Response(self.get_serializer(incidente).data, status=201)

    @action(detail=True, methods=['post'])
    def evaluar(self, request, pk=None):
        incidente, error = _respuesta_regla(
            evaluar_incidente,
            incidente=self.get_object(),
            cuenta=request.user.cuenta_sgca,
        )
        return error or Response(self.get_serializer(incidente).data)

    @action(detail=True, methods=['post'])
    def descartar(self, request, pk=None):
        incidente, error = _respuesta_regla(
            descartar_incidente,
            incidente=self.get_object(),
            cuenta=request.user.cuenta_sgca,
            motivo=request.data.get('motivo'),
        )
        return error or Response(self.get_serializer(incidente).data)

    @action(detail=True, methods=['post'])
    def asignar(self, request, pk=None):
        try:
            tecnico = CuentaSistema.objects.select_related('usuario').get(
                pk=request.data.get('tecnico')
            )
        except (CuentaSistema.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Técnico no encontrado.'}, status=400)
        orden, error = _respuesta_regla(
            asignar_intervencion,
            incidente=self.get_object(),
            tecnico=tecnico,
            cuenta=request.user.cuenta_sgca,
        )
        return error or Response(OrdenIntervencionSerializer(orden).data, status=201)

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        incidente, error = _respuesta_regla(
            cerrar_incidente,
            incidente=self.get_object(),
            cuenta=request.user.cuenta_sgca,
        )
        return error or Response(self.get_serializer(incidente).data)


class OrdenIntervencionViewSet(viewsets.GenericViewSet):
    permission_classes = [EsUsuarioSGCA]
    serializer_class = OrdenIntervencionSerializer
    queryset = OrdenIntervencion.objects.select_related(
        'incidente__edificio', 'tecnico__persona', 'asignada_por'
    ).prefetch_related(
        'cambios_estado__actor__persona',
        'historial_asignaciones__tecnico_anterior__persona',
        'historial_asignaciones__tecnico_nuevo__persona',
    )

    def get_queryset(self):
        qs = super().get_queryset()
        cuenta = cuenta_activa(self.request.user)
        if cuenta and cuenta.rol == 'Tecnico':
            qs = qs.filter(tecnico=cuenta)
        incidente = _id_query(self.request, 'incidente')
        if incidente:
            qs = qs.filter(incidente_id=incidente)
        return qs

    def list(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=['post'], permission_classes=[EsTecnico])
    def iniciar(self, request, pk=None):
        orden, error = _respuesta_regla(
            iniciar_orden, orden=self.get_object(), cuenta=request.user.cuenta_sgca
        )
        return error or Response(self.get_serializer(orden).data)

    @action(detail=True, methods=['post'], permission_classes=[EsTecnico])
    def informar(self, request, pk=None):
        orden, error = _respuesta_regla(
            informar_orden,
            orden=self.get_object(),
            cuenta=request.user.cuenta_sgca,
            diagnostico=request.data.get('diagnostico'),
            trabajo_realizado=request.data.get('trabajo_realizado'),
            resultado=request.data.get('resultado'),
        )
        return error or Response(self.get_serializer(orden).data)

    @action(detail=True, methods=['post'], permission_classes=[EsOperador])
    def verificar(self, request, pk=None):
        orden, error = _respuesta_regla(
            verificar_orden,
            orden=self.get_object(),
            cuenta=request.user.cuenta_sgca,
            aceptada=request.data.get('aceptada'),
            observaciones=request.data.get('observaciones'),
        )
        return error or Response(self.get_serializer(orden).data)

    @action(detail=True, methods=['post'], permission_classes=[EsOperador])
    def cancelar(self, request, pk=None):
        orden, error = _respuesta_regla(
            cancelar_orden,
            orden=self.get_object(),
            cuenta=request.user.cuenta_sgca,
            motivo=request.data.get('motivo'),
        )
        return error or Response(self.get_serializer(orden).data)

    @action(detail=True, methods=['post'], permission_classes=[EsOperador])
    def reasignar(self, request, pk=None):
        try:
            tecnico = CuentaSistema.objects.select_related('usuario').get(
                pk=request.data.get('tecnico')
            )
        except (CuentaSistema.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Técnico no encontrado.'}, status=400)
        orden, error = _respuesta_regla(
            reasignar_orden,
            orden=self.get_object(),
            tecnico=tecnico,
            cuenta=request.user.cuenta_sgca,
            motivo=request.data.get('motivo'),
        )
        return error or Response(self.get_serializer(orden).data)


def _datos_usuario(user):
    cuenta = cuenta_activa(user)
    if not cuenta:
        return None
    persona = cuenta.persona
    datos = {
        'id': cuenta.pk,
        'username': user.username,
        'nombre': f'{persona.nombre} {persona.apellido}',
        'rol': cuenta.rol,
    }
    if cuenta.rol == 'Operador':
        operador = OperadorSistema.objects.filter(pk=persona.pk).first()
        if not operador:
            return None
        datos['turno_asignado'] = operador.turno_asignado
    return datos


@ensure_csrf_cookie
@api_view(['GET'])
@permission_classes([AllowAny])
def csrf_cookie(request):
    return Response({'detail': 'CSRF cookie establecida.'})


@csrf_protect
@require_POST
def login_sistema(request):
    try:
        datos_login = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Solicitud JSON inválida.'}, status=400)
    user = authenticate(
        request,
        username=datos_login.get('username'),
        password=datos_login.get('password'),
    )
    if not user:
        return JsonResponse({'error': 'Usuario o contraseña inválidos'}, status=401)
    datos = _datos_usuario(user)
    if not datos:
        logout(request)
        return JsonResponse(
            {'error': 'La cuenta no tiene un rol habilitado en SGCA-APL.'},
            status=403,
        )
    login(request, user)
    return JsonResponse(datos)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usuario_actual(request):
    datos = _datos_usuario(request.user)
    if not datos:
        return Response({'error': 'La cuenta no tiene un rol habilitado en SGCA-APL.'}, status=403)
    return Response(datos)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_sistema(request):
    logout(request)
    return Response(status=204)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def procesar_lectura_totem(request):
    codigo = request.data.get('codigo_rfid')
    ip_totem = request.data.get('ip_totem')
    motor = MotorValidacionAcceso()

    try:
        resultado = motor.evaluar(codigo, ip_totem)
    except Exception as e:
        return Response(
            {'status': 'critical', 'accion': 'error_interno', 'error': str(e)},
            status=500,
        )

    if resultado.dispositivo is None:
        return Response({'error': 'dispositivo no encontrado en el sistema'}, status=404)

    _marcar_controlador_en_linea(resultado.dispositivo)

    punto = resultado.dispositivo.punto_acceso
    RegistroAcceso.objects.create(
        resultado='concedido' if resultado.concedido else 'rechazado',
        sentido=punto.sentido if punto else 'Entrada',
        motivo_rechazo=None if resultado.concedido else resultado.motivo,
        dispositivo=resultado.dispositivo,
        credencial=resultado.credencial,
    )

    if resultado.concedido:
        return Response({
            'status': 'ok',
            'accion': resultado.accion,
            'motivo': None,
            'sentido': punto.sentido if punto else 'Entrada',
        })

    AlertaSeguridad.objects.create(
        tipo_alerta=resultado.tipo_alerta,
        nivel_gravedad=resultado.nivel_gravedad,
        estado_atencion='Pendiente',
        dispositivo=resultado.dispositivo,
    )
    return Response(
        {
            'status': 'ERROR',
            'accion': resultado.accion,
            'motivo': resultado.motivo,
            'sentido': punto.sentido if punto else 'Entrada',
        },
        status=403,
    )


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def procesar_evento_hardware(request):
    ip_totem = request.data.get('ip_totem')
    tipo = (request.data.get('tipo') or '').upper()
    dispositivo = ControladorAcceso.objects.filter(direccion_ip=ip_totem).first()
    if not dispositivo:
        return Response({'error': 'dispositivo no encontrado en el sistema'}, status=404)

    eventos = {
        'PUERTA_FORZADA': ('puerta forzada', 'Critica', 'En linea'),
        'DESCONEXION': ('controlador desconectado', 'Alta', 'Desconectado'),
        'RECONEXION': ('controlador reconectado', 'Baja', 'En linea'),
    }
    if tipo not in eventos:
        return Response({'error': 'tipo de evento no soportado'}, status=400)

    tipo_alerta, gravedad, estado = eventos[tipo]
    dispositivo.estado_conexion = estado
    dispositivo.fecha_ultimo_ping = timezone.now()
    dispositivo.save(update_fields=['estado_conexion', 'fecha_ultimo_ping'])

    alerta = None
    if tipo != 'RECONEXION':
        alerta = AlertaSeguridad.objects.create(
            tipo_alerta=tipo_alerta,
            nivel_gravedad=gravedad,
            estado_atencion='Pendiente',
            dispositivo=dispositivo,
        )

    return Response({
        'status': 'ok',
        'tipo': tipo,
        'alerta_id': alerta.id if alerta else None,
        'estado_conexion': dispositivo.estado_conexion,
    })


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def heartbeat_totem(request):
    ip_totem = request.data.get('ip_totem')
    dispositivo = ControladorAcceso.objects.filter(direccion_ip=ip_totem).first()
    if not dispositivo:
        return Response({'error': 'dispositivo no encontrado en el sistema'}, status=404)
    _marcar_controlador_en_linea(dispositivo)
    return Response({'status': 'ok', 'estado_conexion': dispositivo.estado_conexion})
