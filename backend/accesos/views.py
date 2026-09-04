from datetime import timedelta

from django.contrib.auth.hashers import check_password
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import (
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
    ResolucionAlerta,
    SujetoAcceso,
)
from .motor_reglas import MotorValidacionAcceso
from .serializers import (
    AlertaSeguridadSerializer,
    ComponenteZonaSerializer,
    ControladorAccesoSerializer,
    CredencialSerializer,
    EdificioSerializer,
    HorarioPermitidoSerializer,
    NivelAccesoSerializer,
    PuntoAccesoSerializer,
    RegistroAccesoSerializer,
    SujetoAccesoSerializer,
)


def _marcar_controlador_en_linea(dispositivo):
    dispositivo.estado_conexion = 'En linea'
    dispositivo.fecha_ultimo_ping = timezone.now()
    dispositivo.save(update_fields=['estado_conexion', 'fecha_ultimo_ping'])


class SujetoAccesoViewSet(viewsets.ModelViewSet):
    queryset = SujetoAcceso.objects.select_related('nivel_acceso', 'edificio').prefetch_related(
        'credenciales',
    ).all()
    serializer_class = SujetoAccesoSerializer

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
                estado_llave = request.data.get('estado_llave')
                credencial = sujeto.credenciales.order_by('id').first()
                if credencial and (codigo or estado_llave):
                    if codigo:
                        credencial.codigo_referencia = codigo
                    if estado_llave:
                        credencial.estado = estado_llave
                    credencial.save()
                elif codigo and not credencial:
                    Credencial.objects.create(
                        codigo_referencia=codigo,
                        tipo='Magnetica',
                        fecha_vencimiento=timezone.now().date() + timedelta(days=365),
                        estado=estado_llave or 'Activa',
                        persona=sujeto,
                    )
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


class PuntoAccesoViewSet(viewsets.ModelViewSet):
    queryset = PuntoAcceso.objects.select_related('zona').all()
    serializer_class = PuntoAccesoSerializer


class RegistroAccesoViewSet(viewsets.ModelViewSet):
    queryset = RegistroAcceso.objects.select_related(
        'credencial__persona',
        'dispositivo__punto_acceso__zona',
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
        return qs


class AlertaSeguridadViewSet(viewsets.ModelViewSet):
    queryset = AlertaSeguridad.objects.select_related(
        'dispositivo__punto_acceso__zona',
        'resolucion',
    ).all()
    serializer_class = AlertaSeguridadSerializer

    @action(detail=True, methods=['post'])
    def resolver(self, request, pk=None):
        alerta = self.get_object()
        if alerta.estado_atencion == 'Resuelta':
            return Response(self.get_serializer(alerta).data)

        observaciones = request.data.get('observaciones') or 'Resuelta desde el panel operativo.'
        operador = None
        operador_id = request.data.get('operador')
        if operador_id:
            operador = OperadorSistema.objects.filter(pk=operador_id).first()

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


class EdificioViewSet(viewsets.ModelViewSet):
    queryset = Edificio.objects.all()
    serializer_class = EdificioSerializer


class NivelAccesoViewSet(viewsets.ModelViewSet):
    queryset = NivelAcceso.objects.prefetch_related('zonas', 'horarios').all()
    serializer_class = NivelAccesoSerializer


class ComponenteZonaViewSet(viewsets.ModelViewSet):
    queryset = ComponenteZona.objects.select_related('edificio', 'zona_padre').all()
    serializer_class = ComponenteZonaSerializer


class HorarioPermitidoViewSet(viewsets.ModelViewSet):
    queryset = HorarioPermitido.objects.select_related('nivel_acceso').all()
    serializer_class = HorarioPermitidoSerializer


class ControladorAccesoViewSet(viewsets.ModelViewSet):
    queryset = ControladorAcceso.objects.select_related(
        'punto_acceso__zona',
        'edificio',
    ).all()
    serializer_class = ControladorAccesoSerializer


class CredencialViewSet(viewsets.ModelViewSet):
    queryset = Credencial.objects.select_related('persona').all()
    serializer_class = CredencialSerializer


@api_view(['POST'])
def login_operador(request):
    username = request.data.get('username')
    password = request.data.get('password')
    operador = OperadorSistema.objects.filter(username=username).first()
    if not operador or not check_password(password, operador.password_hash):
        return Response({'error': 'Usuario o contraseña inválidos'}, status=401)
    return Response({
        'id': operador.pk,
        'username': operador.username,
        'nombre': f'{operador.nombre} {operador.apellido}',
        'turno_asignado': operador.turno_asignado,
    })


@api_view(['POST'])
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
def heartbeat_totem(request):
    ip_totem = request.data.get('ip_totem')
    dispositivo = ControladorAcceso.objects.filter(direccion_ip=ip_totem).first()
    if not dispositivo:
        return Response({'error': 'dispositivo no encontrado en el sistema'}, status=404)
    _marcar_controlador_en_linea(dispositivo)
    return Response({'status': 'ok', 'estado_conexion': dispositivo.estado_conexion})
