from django.db import models


class Edificio(models.Model):
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} {self.direccion}"


class Persona(models.Model):
    """Identidad común. SujetoAcceso y OperadorSistema heredan por MTI."""

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
    zonas = models.ManyToManyField(
        'ComponenteZona',
        blank=True,
        related_name='niveles',
    )

    class Meta:
        ordering = ['nombre_nivel']

    def __str__(self):
        return self.nombre_nivel


class SujetoAcceso(Persona):
    legajo_empleado = models.CharField(max_length=50, unique=True, blank=True, null=True)
    estado = models.CharField(max_length=20, default='Activo')
    fecha_alta = models.DateTimeField(auto_now_add=True)
    nivel_acceso = models.ForeignKey(
        NivelAcceso,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sujetos',
    )
    edificio = models.ForeignKey(
        Edificio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sujetos',
    )


class OperadorSistema(Persona):
    username = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=255)
    turno_asignado = models.CharField(max_length=50)


class HorarioPermitido(models.Model):
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    dias_semana = models.CharField(
        max_length=50,
        help_text='Días permitidos: 0=lunes … 6=domingo, separados por coma.',
    )
    nivel_acceso = models.ForeignKey(
        NivelAcceso,
        on_delete=models.CASCADE,
        related_name='horarios',
    )

    def __str__(self):
        return f"{self.nivel_acceso} {self.hora_inicio}-{self.hora_fin}"


class ComponenteZona(models.Model):
    """Nodo Composite: una zona puede agrupar subzonas o ser hoja."""

    nombre_zona = models.CharField(max_length=100)
    nivel_seguridad = models.CharField(max_length=50, default='Media')
    zona_padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subzonas',
    )
    edificio = models.ForeignKey(
        Edificio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='zonas',
    )

    class Meta:
        ordering = ['nombre_zona']

    def __str__(self):
        return self.nombre_zona


class PuntoAcceso(models.Model):
    descripcion = models.CharField(max_length=100)
    ubicacion_fisica = models.CharField(max_length=150)
    zona = models.ForeignKey(
        ComponenteZona,
        on_delete=models.CASCADE,
        related_name='puntos_acceso',
    )

    def __str__(self):
        return self.descripcion


class ControladorAcceso(models.Model):
    direccion_ip = models.GenericIPAddressField()
    numero_serie = models.CharField(max_length=100, unique=True)
    estado_conexion = models.CharField(max_length=50, default='Desconectado')
    fecha_ultimo_ping = models.DateTimeField(null=True, blank=True)
    punto_acceso = models.ForeignKey(
        PuntoAcceso,
        on_delete=models.CASCADE,
        related_name='controladores',
    )
    edificio = models.ForeignKey(
        Edificio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='controladores',
    )

    class Meta:
        ordering = ['numero_serie']

    def __str__(self):
        return f"{self.numero_serie} ({self.direccion_ip})"


class Credencial(models.Model):
    ESTADOS = [('Activa', 'Activa'), ('Bloqueada', 'Bloqueada'), ('Vencida', 'Vencida')]
    codigo_referencia = models.CharField(max_length=100, unique=True)
    tipo = models.CharField(max_length=50, default='RFID')
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Activa')
    persona = models.ForeignKey(
        Persona,
        on_delete=models.CASCADE,
        related_name='credenciales',
    )

    def __str__(self):
        return self.codigo_referencia


class RegistroAcceso(models.Model):
    fecha_hora = models.DateTimeField(auto_now_add=True)
    resultado = models.CharField(max_length=20)
    motivo_rechazo = models.CharField(max_length=200, blank=True, null=True)
    dispositivo = models.ForeignKey(
        ControladorAcceso,
        on_delete=models.SET_NULL,
        null=True,
        related_name='registros',
    )
    credencial = models.ForeignKey(
        Credencial,
        on_delete=models.SET_NULL,
        null=True,
        related_name='registros',
    )

    class Meta:
        ordering = ['-fecha_hora']


class AlertaSeguridad(models.Model):
    tipo_alerta = models.CharField(max_length=100)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    nivel_gravedad = models.CharField(max_length=50)
    estado_atencion = models.CharField(max_length=50, default='Pendiente')
    dispositivo = models.ForeignKey(
        ControladorAcceso,
        on_delete=models.CASCADE,
        related_name='alertas',
    )

    class Meta:
        ordering = ['-fecha_hora']


class ResolucionAlerta(models.Model):
    fecha_resolucion = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField()
    alerta = models.OneToOneField(
        AlertaSeguridad,
        on_delete=models.CASCADE,
        related_name='resolucion',
    )
    operador = models.ForeignKey(
        OperadorSistema,
        on_delete=models.SET_NULL,
        null=True,
        related_name='resoluciones',
    )
