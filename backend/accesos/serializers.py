from django.utils import timezone
from datetime import timedelta

from rest_framework import serializers

from .models import (
    AlertaSeguridad,
    ComponenteZona,
    ControladorAcceso,
    Credencial,
    Edificio,
    HorarioPermitido,
    NivelAcceso,
    PuntoAcceso,
    RegistroAcceso,
    ResolucionAlerta,
    SujetoAcceso,
)


class EdificioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edificio
        fields = '__all__'


class CredencialSerializer(serializers.ModelSerializer):
    persona_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Credencial
        fields = '__all__'

    def get_persona_nombre(self, obj):
        persona = obj.persona
        return f"{persona.nombre} {persona.apellido}"


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
    resolucion = ResolucionAlertaSerializer(read_only=True)

    class Meta:
        model = AlertaSeguridad
        fields = '__all__'
