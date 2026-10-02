from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Edificio(models.Model):
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255)
    horas_permanencia_maxima = models.PositiveIntegerField(default=12)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'edificio'
        verbose_name_plural = 'edificios'

    def __str__(self):
        return f"{self.nombre} {self.direccion}"


class Persona(models.Model):
    """Identidad común. SujetoAcceso y OperadorSistema heredan por MTI."""

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.IntegerField(unique=True)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = 'persona'
        verbose_name_plural = 'personas'

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
        verbose_name = 'nivel de acceso'
        verbose_name_plural = 'niveles de acceso'

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

    class Meta:
        verbose_name = 'cliente'
        verbose_name_plural = 'clientes'


class OperadorSistema(Persona):
    username = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=255)
    turno_asignado = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'operador'
        verbose_name_plural = 'operadores'


class CuentaSistema(models.Model):
    ROLES = [
        ('Operador', 'Operador'),
        ('Tecnico', 'Técnico'),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cuenta_sgca',
    )
    persona = models.OneToOneField(
        Persona,
        on_delete=models.PROTECT,
        related_name='cuenta_sistema',
    )
    rol = models.CharField(max_length=20, choices=ROLES)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'cuenta del sistema'
        verbose_name_plural = 'cuentas del sistema'

    def clean(self):
        super().clean()
        if (
            self.rol == 'Operador'
            and self.persona_id
            and not OperadorSistema.objects.filter(pk=self.persona_id).exists()
        ):
            raise ValidationError({'persona': 'El rol Operador requiere una persona operadora.'})

    def __str__(self):
        return f'{self.usuario.username} ({self.get_rol_display()})'


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

    class Meta:
        verbose_name = 'horario'
        verbose_name_plural = 'horarios'

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
        verbose_name = 'zona'
        verbose_name_plural = 'zonas'

    def __str__(self):
        return self.nombre_zona


class PuntoAcceso(models.Model):
    TIPOS = [('Totem', 'Tótem con cámara'), ('Lector', 'Lector de puerta')]
    SENTIDOS = [('Entrada', 'Entrada'), ('Salida', 'Salida')]

    descripcion = models.CharField(max_length=100)
    ubicacion_fisica = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='Totem')
    sentido = models.CharField(max_length=20, choices=SENTIDOS, default='Entrada')
    tiene_camara = models.BooleanField(default=True)
    zona = models.ForeignKey(
        ComponenteZona,
        on_delete=models.CASCADE,
        related_name='puntos_acceso',
    )

    class Meta:
        verbose_name = 'punto de acceso'
        verbose_name_plural = 'puntos de acceso'

    def __str__(self):
        return f"{self.descripcion} ({self.sentido})"


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
        verbose_name = 'controladora'
        verbose_name_plural = 'controladoras'

    def __str__(self):
        return f"{self.numero_serie} ({self.direccion_ip})"


class Credencial(models.Model):
    # Los estados retirados permanecen para interpretar registros históricos.
    ESTADOS_OPERATIVOS = ('Activa', 'Bloqueada', 'Vencida')
    ESTADOS_HISTORICOS = ('Emitida', 'Repuesta')
    ESTADOS = [
        ('Emitida', 'Emitida'),
        ('Activa', 'Activa'),
        ('Bloqueada', 'Bloqueada'),
        ('Vencida', 'Vencida'),
        ('Repuesta', 'Repuesta'),
    ]
    TIPOS = [
        ('Peatonal', 'Peatonal'),
        ('Cochera', 'Cochera'),
        ('Magnetica', 'Magnetica'),
    ]
    codigo_referencia = models.CharField(max_length=100, unique=True)
    tipo = models.CharField(max_length=50, choices=TIPOS, default='Magnetica')
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Activa')
    motivo_estado = models.CharField(max_length=200, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    reemplaza = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='repuestas',
    )
    persona = models.ForeignKey(
        Persona,
        on_delete=models.CASCADE,
        related_name='credenciales',
    )

    class Meta:
        verbose_name = 'llave'
        verbose_name_plural = 'llaves'

    @classmethod
    def validar_estado_operativo(cls, estado, anterior=None):
        if anterior in cls.ESTADOS_HISTORICOS:
            if estado != anterior:
                raise ValidationError('Una credencial histórica no puede cambiar de estado.')
        elif estado not in cls.ESTADOS_OPERATIVOS:
            raise ValidationError('Solo se permiten los estados Activa, Bloqueada y Vencida.')

    def clean(self):
        super().clean()
        anterior = type(self).objects.filter(pk=self.pk).values_list('estado', flat=True).first()
        try:
            self.validar_estado_operativo(self.estado, anterior)
        except ValidationError as exc:
            raise ValidationError({'estado': exc.messages}) from exc

    def __str__(self):
        return self.codigo_referencia


class MovimientoCredencial(models.Model):
    """Historial conservado de la iteración retirada; sin nuevas transiciones."""
    credencial = models.ForeignKey(
        Credencial,
        on_delete=models.CASCADE,
        related_name='movimientos',
    )
    estado_origen = models.CharField(max_length=20, blank=True)
    estado_destino = models.CharField(max_length=20)
    motivo = models.CharField(max_length=200, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    operador = models.ForeignKey(
        OperadorSistema,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_credencial',
    )

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'movimiento de llave'
        verbose_name_plural = 'movimientos de llave'

    def __str__(self):
        return f"{self.credencial} {self.estado_origen} → {self.estado_destino}"


class RegistroAcceso(models.Model):
    fecha_hora = models.DateTimeField(auto_now_add=True)
    resultado = models.CharField(max_length=20)
    sentido = models.CharField(max_length=20, default='Entrada')
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
        verbose_name = 'registro'
        verbose_name_plural = 'registros'


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
        verbose_name = 'alerta'
        verbose_name_plural = 'alertas'


class Presencia(models.Model):
    """Archivo histórico; ya no representa la presencia actual en el edificio."""

    ESTADOS = [
        ('Dentro', 'Dentro'),
        ('Permanencia excedida', 'Permanencia excedida'),
        ('Fuera', 'Fuera'),
    ]

    sujeto = models.ForeignKey(
        SujetoAcceso,
        on_delete=models.CASCADE,
        related_name='presencias',
    )
    edificio = models.ForeignKey(
        Edificio,
        on_delete=models.CASCADE,
        related_name='presencias',
    )
    estado = models.CharField(max_length=30, choices=ESTADOS, default='Dentro')
    credencial = models.ForeignKey(
        Credencial,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='presencias',
    )
    registro_entrada = models.ForeignKey(
        RegistroAcceso,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='presencias_entrada',
    )
    registro_salida = models.ForeignKey(
        RegistroAcceso,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='presencias_salida',
    )
    ingreso = models.DateTimeField()
    egreso = models.DateTimeField(null=True, blank=True)
    alerta_emitida = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'presencia'
        verbose_name_plural = 'presencias'
        ordering = ['-ingreso']
        constraints = [
            models.UniqueConstraint(
                fields=['sujeto', 'edificio'],
                condition=models.Q(egreso__isnull=True),
                name='una_presencia_abierta_por_sujeto_edificio',
            ),
        ]

    def __str__(self):
        return f"{self.sujeto} en {self.edificio} ({self.estado})"


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

    class Meta:
        verbose_name = 'resolución'
        verbose_name_plural = 'resoluciones'


class IncidenteTecnico(models.Model):
    CATEGORIAS = [
        ('Hardware', 'Hardware'),
        ('Conectividad', 'Conectividad'),
        ('Energia', 'Energía'),
        ('Otro', 'Otro'),
    ]
    PRIORIDADES = [
        ('Baja', 'Baja'),
        ('Media', 'Media'),
        ('Alta', 'Alta'),
        ('Critica', 'Crítica'),
    ]
    ESTADOS = [
        ('Registrado', 'Registrado'),
        ('Evaluado', 'Evaluado'),
        ('En atencion', 'En atención'),
        ('Pendiente verificacion', 'Pendiente de verificación'),
        ('Cerrado', 'Cerrado'),
        ('Descartado', 'Descartado'),
    ]

    edificio = models.ForeignKey(
        Edificio, on_delete=models.PROTECT, related_name='incidentes_tecnicos'
    )
    dispositivo = models.ForeignKey(
        ControladorAcceso,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='incidentes_tecnicos',
    )
    alerta_origen = models.OneToOneField(
        AlertaSeguridad,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='incidente_tecnico',
    )
    incidente_anterior = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='incidentes_posteriores',
    )
    descripcion = models.TextField()
    categoria = models.CharField(max_length=30, choices=CATEGORIAS)
    prioridad = models.CharField(max_length=20, choices=PRIORIDADES, default='Media')
    estado = models.CharField(max_length=30, choices=ESTADOS, default='Registrado')
    registrado_por = models.ForeignKey(
        OperadorSistema, on_delete=models.PROTECT, related_name='incidentes_registrados'
    )
    evaluado_por = models.ForeignKey(
        OperadorSistema,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='incidentes_evaluados',
    )
    cerrado_por = models.ForeignKey(
        OperadorSistema,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='incidentes_cerrados',
    )
    descartado_por = models.ForeignKey(
        OperadorSistema,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='incidentes_descartados',
    )
    motivo_descarte = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_evaluacion = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    fecha_descarte = models.DateTimeField(null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'incidente técnico'
        verbose_name_plural = 'incidentes técnicos'
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(estado='Descartado') | ~models.Q(motivo_descarte=''),
                name='incidente_descartado_con_motivo',
            ),
        ]

    def __str__(self):
        return f'Incidente {self.pk or "nuevo"} · {self.edificio}'


class OrdenIntervencion(models.Model):
    ESTADOS = [
        ('Asignada', 'Asignada'),
        ('En curso', 'En curso'),
        ('Informada', 'Informada'),
        ('Verificada', 'Verificada'),
        ('Cancelada', 'Cancelada'),
    ]
    RESULTADOS = [
        ('solucionado', 'Solucionado'),
        ('parcialmente solucionado', 'Parcialmente solucionado'),
        ('no solucionado', 'No solucionado'),
    ]
    ESTADOS_ACTIVOS = ('Asignada', 'En curso', 'Informada')

    incidente = models.ForeignKey(
        IncidenteTecnico, on_delete=models.PROTECT, related_name='ordenes'
    )
    numero = models.PositiveIntegerField()
    tecnico = models.ForeignKey(
        CuentaSistema, on_delete=models.PROTECT, related_name='ordenes_asignadas'
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Asignada')
    asignada_por = models.ForeignKey(
        OperadorSistema, on_delete=models.PROTECT, related_name='ordenes_asignadas'
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_informe = models.DateTimeField(null=True, blank=True)
    diagnostico = models.TextField(blank=True)
    trabajo_realizado = models.TextField(blank=True)
    resultado = models.CharField(max_length=30, choices=RESULTADOS, blank=True)
    fecha_verificacion = models.DateTimeField(null=True, blank=True)
    verificacion_aceptada = models.BooleanField(null=True, blank=True)
    observaciones_verificacion = models.TextField(blank=True)
    verificada_por = models.ForeignKey(
        OperadorSistema,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ordenes_verificadas',
    )
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)
    motivo_cancelacion = models.TextField(blank=True)
    cancelada_por = models.ForeignKey(
        OperadorSistema,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ordenes_canceladas',
    )

    class Meta:
        ordering = ['-fecha_asignacion']
        verbose_name = 'orden de intervención'
        verbose_name_plural = 'órdenes de intervención'
        constraints = [
            models.UniqueConstraint(
                fields=['incidente', 'numero'], name='numero_orden_unico_por_incidente'
            ),
            models.UniqueConstraint(
                fields=['incidente'],
                condition=models.Q(estado__in=('Asignada', 'En curso', 'Informada')),
                name='una_orden_activa_por_incidente',
            ),
            models.CheckConstraint(
                condition=~models.Q(estado='Cancelada') | ~models.Q(motivo_cancelacion=''),
                name='orden_cancelada_con_motivo',
            ),
        ]

    def __str__(self):
        return f'Orden {self.incidente_id}.{self.numero}'


class CambioEstadoIncidente(models.Model):
    incidente = models.ForeignKey(
        IncidenteTecnico, on_delete=models.PROTECT, related_name='cambios_estado'
    )
    estado_origen = models.CharField(max_length=30, blank=True)
    estado_destino = models.CharField(max_length=30)
    actor = models.ForeignKey(
        CuentaSistema, on_delete=models.PROTECT, related_name='cambios_incidente'
    )
    detalle = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha']
        verbose_name = 'cambio de estado de incidente'
        verbose_name_plural = 'cambios de estado de incidentes'


class CambioEstadoOrden(models.Model):
    orden = models.ForeignKey(
        OrdenIntervencion, on_delete=models.PROTECT, related_name='cambios_estado'
    )
    estado_origen = models.CharField(max_length=20, blank=True)
    estado_destino = models.CharField(max_length=20)
    actor = models.ForeignKey(
        CuentaSistema, on_delete=models.PROTECT, related_name='cambios_orden'
    )
    detalle = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha']
        verbose_name = 'cambio de estado de orden'
        verbose_name_plural = 'cambios de estado de órdenes'


class HistorialAsignacion(models.Model):
    orden = models.ForeignKey(
        OrdenIntervencion, on_delete=models.PROTECT, related_name='historial_asignaciones'
    )
    tecnico_anterior = models.ForeignKey(
        CuentaSistema,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='asignaciones_anteriores',
    )
    tecnico_nuevo = models.ForeignKey(
        CuentaSistema, on_delete=models.PROTECT, related_name='asignaciones_nuevas'
    )
    operador = models.ForeignKey(
        OperadorSistema, on_delete=models.PROTECT, related_name='reasignaciones_realizadas'
    )
    motivo = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha']
        verbose_name = 'historial de asignación'
        verbose_name_plural = 'historiales de asignación'
