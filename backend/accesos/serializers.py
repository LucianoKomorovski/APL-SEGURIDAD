from rest_framework import serializers
from .models import SujetoAcceso, PuntoAcceso, RegistroAcceso, AlertaSeguridad, Edificio

class EdificioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edificio
        fields = '__all__'


class SujetoAccesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SujetoAcceso
        fields = '__all__' # Esto le dice que convierta todos los campos

class PuntoAccesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuntoAcceso
        fields = '__all__'

class RegistroAccesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroAcceso
        fields = '__all__'

class AlertaSeguridadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertaSeguridad
        fields = '__all__'