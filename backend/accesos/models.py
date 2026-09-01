from django.db import models

from django.db import models

class Edificio(models.Model):
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.nombre} {self.direccion}"

# 1. LA CLASE ABSTRACTA Y EL VÍNCULO A CREDENCIALES
class Persona(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.IntegerField(unique=True)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class NivelAcceso(models.Model):
    nombre_nivel = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_nivel

# 2. RENOMBRADO A SUJETO ACCESO
class SujetoAcceso(Persona):
    legajo_empleado = models.CharField(max_length=50, unique=True, blank=True, null=True)
    estado = models.CharField(max_length=20, default='Activo')
    fecha_alta = models.DateTimeField(auto_now_add=True)
    nivel_acceso = models.ForeignKey(NivelAcceso, on_delete=models.SET_NULL, null=True, related_name='sujetos')
    edificio = models.ForeignKey(Edificio, on_delete=models.SET_NULL, null=True , blank=True , related_name='sujetos')

# AGREGADO: El Operador del Sistema (que también hereda de Persona)
class OperadorSistema(Persona):
    username = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=255)
    turno_asignado = models.CharField(max_length=50)

class HorarioPermitido(models.Model):
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    dias_semana = models.CharField(max_length=50)
    # Lista de horarios dentro de NivelAcceso:
    nivel_acceso = models.ForeignKey(NivelAcceso, on_delete=models.CASCADE, related_name='horarios')

class ComponenteZona(models.Model):
    nombre_zona = models.CharField(max_length=100)
    nivel_seguridad = models.CharField(max_length=50)
    # Lista de zonas dentro de NivelAcceso:
    nivel_acceso = models.ForeignKey(NivelAcceso, on_delete=models.CASCADE, related_name='zonas_permitidas')
    zona_padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subzonas')

    def __str__(self):
        return self.nombre_zona

class PuntoAcceso(models.Model):
    descripcion = models.CharField(max_length=100)
    ubicacion_fisica = models.CharField(max_length=150)
    # Lista de puntos dentro de Zona:
    zona = models.ForeignKey(ComponenteZona, on_delete=models.CASCADE, related_name='puntos_acceso')

    def __str__(self):
        return self.descripcion

class ControladorAcceso(models.Model):
    direccion_ip = models.GenericIPAddressField()
    numero_serie = models.CharField(max_length=100, unique=True)
    estado_conexion = models.CharField(max_length=50)
    fecha_ultimo_ping = models.DateTimeField(auto_now=True)
    # Lista de controladores dentro de PuntoAcceso:
    punto_acceso = models.ForeignKey(PuntoAcceso, on_delete=models.CASCADE, related_name='controladores')
    edificio = models.ForeignKey(Edificio , on_delete=models.CASCADE , null=True , blank= True , related_name= 'controladores')

class Credencial(models.Model):
    ESTADOS = [('Activa', 'Activa'), ('Bloqueada', 'Bloqueada'), ('Vencida', 'Vencida')]
    codigo_referencia = models.CharField(max_length=100, unique=True)
    tipo = models.CharField(max_length=50)
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Activa')
    # CORRECCIÓN DEL PROFESOR: La credencial ahora apunta a Persona
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='credenciales')

class RegistroAcceso(models.Model):
    fecha_hora = models.DateTimeField(auto_now_add=True)
    resultado = models.CharField(max_length=20)
    motivo_rechazo = models.CharField(max_length=200, blank=True, null=True)
    dispositivo = models.ForeignKey(ControladorAcceso, on_delete=models.SET_NULL, null=True, related_name='registros')
    credencial = models.ForeignKey(Credencial, on_delete=models.SET_NULL, null=True, related_name='registros')

class AlertaSeguridad(models.Model):
    tipo_alerta = models.CharField(max_length=100)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    nivel_gravedad = models.CharField(max_length=50)
    estado_atencion = models.CharField(max_length=50, default='Generada')
    dispositivo = models.ForeignKey(ControladorAcceso, on_delete=models.CASCADE, related_name='alertas')

class ResolucionAlerta(models.Model):
    fecha_resolucion = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField()
    # Relación 0..1 a 1: Usamos OneToOneField
    alerta = models.OneToOneField(AlertaSeguridad, on_delete=models.CASCADE, related_name='resolucion')
    operador = models.ForeignKey(OperadorSistema, on_delete=models.SET_NULL, null=True, related_name='resoluciones')


