from django.core.exceptions import ValidationError as ModelValidationError
from django.utils import timezone
from datetime import timedelta

from rest_framework import serializers

from .models import (
    AlertaSeguridad,
    CambioEstadoIncidente,
    CambioEstadoOrden,
    ComponenteZona,
    ControladorAcceso,
    Credencial,
    CuentaSistema,
    Edificio,
    HistorialAsignacion,
    MovimientoCredencial,
    HorarioPermitido,
    NivelAcceso,
    IncidenteTecnico,
    OrdenIntervencion,
    PuntoAcceso,
    RegistroAcceso,
    ResolucionAlerta,
    SujetoAcceso,
)


class EdificioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edificio
        fields = '__all__'
        read_only_fields = ['horas_permanencia_maxima']


class MovimientoCredencialSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoCredencial
        fields = '__all__'


class CredencialSerializer(serializers.ModelSerializer):
    persona_nombre = serializers.SerializerMethodField()
    reemplaza_codigo = serializers.SerializerMethodField()
    movimientos = MovimientoCredencialSerializer(many=True, read_only=True)

    class Meta:
        model = Credencial
        fields = [
            'id',
            'codigo_referencia',
            'tipo',
            'fecha_vencimiento',
            'estado',
            'motivo_estado',
            'fecha_entrega',
            'reemplaza',
            'persona',
            'persona_nombre',
            'reemplaza_codigo',
            'movimientos',
        ]
        read_only_fields = ['motivo_estado', 'fecha_entrega', 'reemplaza']

    def validate_estado(self, value):
        try:
            Credencial.validar_estado_operativo(value, self.instance.estado if self.instance else None)
        except ModelValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def get_persona_nombre(self, obj):
        persona = obj.persona
        return f"{persona.nombre} {persona.apellido}"

    def get_reemplaza_codigo(self, obj):
        return obj.reemplaza.codigo_referencia if obj.reemplaza_id else None


class HorarioPermitidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorarioPermitido
        fields = '__all__'


class ComponenteZonaSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)
    zona_padre_nombre = serializers.CharField(source='zona_padre.nombre_zona', read_only=True)

    class Meta:
        model = ComponenteZona
        fields = '__all__'


class PuntoAccesoSerializer(serializers.ModelSerializer):
    zona_nombre = serializers.CharField(source='zona.nombre_zona', read_only=True)

    class Meta:
        model = PuntoAcceso
        fields = '__all__'


class NivelAccesoSerializer(serializers.ModelSerializer):
    horarios = HorarioPermitidoSerializer(many=True, read_only=True)
    zonas_detalle = ComponenteZonaSerializer(source='zonas', many=True, read_only=True)

    class Meta:
        model = NivelAcceso
        fields = '__all__'


class SujetoAccesoSerializer(serializers.ModelSerializer):
    credenciales = CredencialSerializer(many=True, read_only=True)
    nivel_nombre = serializers.CharField(source='nivel_acceso.nombre_nivel', read_only=True)
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)

    class Meta:
        model = SujetoAcceso
        fields = '__all__'


class ControladorAccesoSerializer(serializers.ModelSerializer):
    punto_descripcion = serializers.CharField(source='punto_acceso.descripcion', read_only=True)
    zona_nombre = serializers.CharField(source='punto_acceso.zona.nombre_zona', read_only=True)
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)
    sentido = serializers.CharField(source='punto_acceso.sentido', read_only=True)
    tipo_punto = serializers.CharField(source='punto_acceso.tipo', read_only=True)
    tiene_camara = serializers.BooleanField(source='punto_acceso.tiene_camara', read_only=True)
    en_linea = serializers.SerializerMethodField()

    class Meta:
        model = ControladorAcceso
        fields = '__all__'

    def get_en_linea(self, obj):
        if obj.estado_conexion == 'Desconectado' or not obj.fecha_ultimo_ping:
            return False
        return timezone.now() - obj.fecha_ultimo_ping < timedelta(seconds=90)


class RegistroAccesoSerializer(serializers.ModelSerializer):
    codigo_rfid = serializers.SerializerMethodField()
    persona_nombre = serializers.SerializerMethodField()
    dispositivo_ip = serializers.SerializerMethodField()
    zona_nombre = serializers.SerializerMethodField()
    edificio_nombre = serializers.SerializerMethodField()

    class Meta:
        model = RegistroAcceso
        fields = '__all__'

    def get_codigo_rfid(self, obj):
        return obj.credencial.codigo_referencia if obj.credencial else None

    def get_persona_nombre(self, obj):
        if not obj.credencial:
            return None
        persona = obj.credencial.persona
        return f"{persona.nombre} {persona.apellido}"

    def get_dispositivo_ip(self, obj):
        return obj.dispositivo.direccion_ip if obj.dispositivo else None

    def get_zona_nombre(self, obj):
        if not obj.dispositivo:
            return None
        return obj.dispositivo.punto_acceso.zona.nombre_zona

    def get_edificio_nombre(self, obj):
        if not obj.dispositivo or not obj.dispositivo.edificio:
            return None
        return obj.dispositivo.edificio.nombre


class ResolucionAlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResolucionAlerta
        fields = '__all__'


class AlertaSeguridadSerializer(serializers.ModelSerializer):
    dispositivo_ip = serializers.CharField(source='dispositivo.direccion_ip', read_only=True)
    zona_nombre = serializers.CharField(
        source='dispositivo.punto_acceso.zona.nombre_zona',
        read_only=True,
        default=None,
    )
    edificio_id = serializers.SerializerMethodField()
    edificio_nombre = serializers.SerializerMethodField()
    incidente_tecnico_id = serializers.SerializerMethodField()
    resolucion = ResolucionAlertaSerializer(read_only=True)

    class Meta:
        model = AlertaSeguridad
        fields = '__all__'

    def get_edificio_id(self, obj):
        if not obj.dispositivo_id or not obj.dispositivo.edificio_id:
            return None
        return obj.dispositivo.edificio_id

    def get_edificio_nombre(self, obj):
        if not obj.dispositivo_id or not obj.dispositivo.edificio_id:
            return None
        return obj.dispositivo.edificio.nombre

    def get_incidente_tecnico_id(self, obj):
        try:
            return obj.incidente_tecnico.pk
        except IncidenteTecnico.DoesNotExist:
            return None


class TecnicoSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    username = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = CuentaSistema
        fields = ['id', 'username', 'nombre', 'activo']

    def get_nombre(self, obj):
        return f'{obj.persona.nombre} {obj.persona.apellido}'


class CambioEstadoIncidenteSerializer(serializers.ModelSerializer):
    actor_nombre = serializers.SerializerMethodField()

    class Meta:
        model = CambioEstadoIncidente
        fields = '__all__'

    def get_actor_nombre(self, obj):
        return f'{obj.actor.persona.nombre} {obj.actor.persona.apellido}'


class CambioEstadoOrdenSerializer(serializers.ModelSerializer):
    actor_nombre = serializers.SerializerMethodField()

    class Meta:
        model = CambioEstadoOrden
        fields = '__all__'

    def get_actor_nombre(self, obj):
        return f'{obj.actor.persona.nombre} {obj.actor.persona.apellido}'


class HistorialAsignacionSerializer(serializers.ModelSerializer):
    tecnico_anterior_nombre = serializers.SerializerMethodField()
    tecnico_nuevo_nombre = serializers.SerializerMethodField()
    operador_nombre = serializers.SerializerMethodField()

    class Meta:
        model = HistorialAsignacion
        fields = '__all__'

    def _nombre(self, cuenta):
        return f'{cuenta.persona.nombre} {cuenta.persona.apellido}' if cuenta else None

    def get_tecnico_anterior_nombre(self, obj):
        return self._nombre(obj.tecnico_anterior)

    def get_tecnico_nuevo_nombre(self, obj):
        return self._nombre(obj.tecnico_nuevo)

    def get_operador_nombre(self, obj):
        return f'{obj.operador.nombre} {obj.operador.apellido}'


class OrdenIntervencionSerializer(serializers.ModelSerializer):
    tecnico_nombre = serializers.SerializerMethodField()
    incidente_descripcion = serializers.CharField(source='incidente.descripcion', read_only=True)
    edificio_nombre = serializers.CharField(source='incidente.edificio.nombre', read_only=True)
    cambios_estado = CambioEstadoOrdenSerializer(many=True, read_only=True)
    historial_asignaciones = HistorialAsignacionSerializer(many=True, read_only=True)

    class Meta:
        model = OrdenIntervencion
        fields = '__all__'

    def get_tecnico_nombre(self, obj):
        return f'{obj.tecnico.persona.nombre} {obj.tecnico.persona.apellido}'


class IncidenteTecnicoSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)
    dispositivo_serie = serializers.CharField(
        source='dispositivo.numero_serie', read_only=True, default=None
    )
    alerta_tipo = serializers.CharField(
        source='alerta_origen.tipo_alerta', read_only=True, default=None
    )
    registrado_por_nombre = serializers.SerializerMethodField()
    ordenes = OrdenIntervencionSerializer(many=True, read_only=True)
    cambios_estado = CambioEstadoIncidenteSerializer(many=True, read_only=True)

    class Meta:
        model = IncidenteTecnico
        fields = '__all__'

    def get_registrado_por_nombre(self, obj):
        return f'{obj.registrado_por.nombre} {obj.registrado_por.apellido}'


class IncidenteCrearSerializer(serializers.Serializer):
    edificio = serializers.PrimaryKeyRelatedField(queryset=Edificio.objects.all())
    dispositivo = serializers.PrimaryKeyRelatedField(
        queryset=ControladorAcceso.objects.all(), required=False, allow_null=True
    )
    alerta_origen = serializers.PrimaryKeyRelatedField(
        queryset=AlertaSeguridad.objects.all(), required=False, allow_null=True
    )
    incidente_anterior = serializers.PrimaryKeyRelatedField(
        queryset=IncidenteTecnico.objects.all(), required=False, allow_null=True
    )
    descripcion = serializers.CharField()
    categoria = serializers.ChoiceField(choices=IncidenteTecnico.CATEGORIAS)
    prioridad = serializers.ChoiceField(
        choices=IncidenteTecnico.PRIORIDADES, default='Media'
    )
