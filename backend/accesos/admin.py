from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import (
    AlertaSeguridad,
    CambioEstadoIncidente,
    CambioEstadoOrden,
    ComponenteZona,
    ControladorAcceso,
    CuentaSistema,
    Credencial,
    Edificio,
    HistorialAsignacion,
    HorarioPermitido,
    MovimientoCredencial,
    NivelAcceso,
    IncidenteTecnico,
    OrdenIntervencion,
    OperadorSistema,
    Presencia,
    PuntoAcceso,
    RegistroAcceso,
    ResolucionAlerta,
    SujetoAcceso,
)


class SgcaAdminSite(admin.AdminSite):
    site_header = 'SGCA-APL'
    site_title = 'SGCA-APL'
    index_title = 'Administración'

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        if app_label:
            return app_list

        modelos = {}
        auth = []
        for app in app_list:
            if app['app_label'] == 'auth':
                app['models'] = [
                    modelo for modelo in app['models'] if modelo['object_name'] != 'Group'
                ]
                if app['models']:
                    auth.append(app)
                continue
            for modelo in app['models']:
                modelos[modelo['object_name'].lower()] = modelo

        grupos = [
            ('Sitios', ['edificio', 'componentezona', 'puntoacceso', 'controladoracceso']),
            ('Personas', ['sujetoacceso', 'operadorsistema', 'cuentasistema', 'nivelacceso', 'horariopermitido']),
            ('Accesos', ['credencial', 'registroacceso']),
            ('Alertas', ['alertaseguridad', 'resolucionalerta']),
            ('Servicio técnico', ['incidentetecnico', 'ordenintervencion', 'historialasignacion', 'cambioestadoincidente', 'cambioestadoorden']),
            ('Archivo histórico', ['movimientocredencial', 'presencia']),
        ]
        ordenados = []
        for nombre, claves in grupos:
            models = [modelos[clave] for clave in claves if clave in modelos]
            if not models:
                continue
            ordenados.append({
                'name': nombre,
                'app_label': nombre.lower(),
                'app_url': models[0].get('admin_url') or '',
                'has_module_perms': True,
                'models': models,
            })
        return ordenados + auth


site = SgcaAdminSite(name='sgca')
site.register(User, UserAdmin)


class CredencialForm(forms.ModelForm):
    class Meta:
        model = Credencial
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'estado' in self.fields:
            estados = list(Credencial.ESTADOS_OPERATIVOS)
            if self.instance.pk and self.instance.estado in Credencial.ESTADOS_HISTORICOS:
                estados = [self.instance.estado]
            self.fields['estado'].choices = [(estado, estado) for estado in estados]


class ArchivoHistoricoAdmin(admin.ModelAdmin):
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CredencialInline(admin.TabularInline):
    model = Credencial
    form = CredencialForm
    fk_name = 'persona'
    fields = ('codigo_referencia', 'tipo', 'estado', 'fecha_vencimiento')
    extra = 0
    show_change_link = True


class HorarioInline(admin.TabularInline):
    model = HorarioPermitido
    fields = ('hora_inicio', 'hora_fin', 'dias_semana')
    extra = 0


class ResolucionInline(admin.StackedInline):
    model = ResolucionAlerta
    extra = 0
    max_num = 1
    can_delete = False
    readonly_fields = ('fecha_resolucion', 'observaciones', 'operador')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Edificio, site=site)
class EdificioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion')
    exclude = ('horas_permanencia_maxima',)
    search_fields = ('nombre', 'direccion')


@admin.register(ComponenteZona, site=site)
class ZonaAdmin(admin.ModelAdmin):
    list_display = ('nombre_zona', 'edificio', 'zona_padre', 'nivel_seguridad')
    list_filter = ('edificio', 'nivel_seguridad')
    search_fields = ('nombre_zona',)
    list_select_related = ('edificio', 'zona_padre')


@admin.register(PuntoAcceso, site=site)
class PuntoAccesoAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'zona', 'sentido', 'tipo')
    list_filter = ('sentido', 'tipo', 'zona__edificio')
    search_fields = ('descripcion', 'ubicacion_fisica')
    list_select_related = ('zona', 'zona__edificio')


@admin.register(ControladorAcceso, site=site)
class ControladorAdmin(admin.ModelAdmin):
    list_display = ('numero_serie', 'direccion_ip', 'edificio', 'punto_acceso', 'estado_conexion')
    list_filter = ('edificio', 'estado_conexion')
    search_fields = ('numero_serie', 'direccion_ip')
    list_select_related = ('edificio', 'punto_acceso')


@admin.register(SujetoAcceso, site=site)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('apellido', 'nombre', 'dni', 'edificio', 'nivel_acceso', 'estado')
    list_filter = ('edificio', 'estado', 'nivel_acceso')
    search_fields = ('nombre', 'apellido', 'dni', 'email')
    list_select_related = ('edificio', 'nivel_acceso')
    readonly_fields = ('fecha_alta',)
    inlines = (CredencialInline,)


@admin.register(OperadorSistema, site=site)
class OperadorAdmin(admin.ModelAdmin):
    list_display = ('username', 'apellido', 'nombre', 'turno_asignado')
    search_fields = ('username', 'nombre', 'apellido')
    readonly_fields = ('password_hash',)

    def get_fields(self, request, obj=None):
        campos = ['username', 'nombre', 'apellido', 'dni', 'email', 'telefono', 'turno_asignado']
        if obj:
            campos.append('password_hash')
        return campos

    def save_model(self, request, obj, form, change):
        if not obj.password_hash:
            obj.password_hash = ''
        super().save_model(request, obj, form, change)


@admin.register(CuentaSistema, site=site)
class CuentaSistemaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'persona', 'rol', 'activo')
    list_filter = ('rol', 'activo')
    search_fields = ('usuario__username', 'persona__nombre', 'persona__apellido')
    list_select_related = ('usuario', 'persona')


@admin.register(NivelAcceso, site=site)
class NivelAdmin(admin.ModelAdmin):
    list_display = ('nombre_nivel', 'descripcion')
    search_fields = ('nombre_nivel',)
    filter_horizontal = ('zonas',)
    inlines = (HorarioInline,)


@admin.register(HorarioPermitido, site=site)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ('nivel_acceso', 'hora_inicio', 'hora_fin', 'dias_semana')
    list_filter = ('nivel_acceso',)
    search_fields = ('nivel_acceso__nombre_nivel',)
    list_select_related = ('nivel_acceso',)


@admin.register(Credencial, site=site)
class CredencialAdmin(admin.ModelAdmin):
    form = CredencialForm
    readonly_fields = ('motivo_estado', 'fecha_entrega', 'reemplaza')
    list_display = ('codigo_referencia', 'persona', 'tipo', 'estado', 'fecha_vencimiento')
    list_filter = ('estado', 'tipo')
    search_fields = ('codigo_referencia', 'persona__nombre', 'persona__apellido')
    list_select_related = ('persona',)


@admin.register(MovimientoCredencial, site=site)
class MovimientoAdmin(ArchivoHistoricoAdmin):
    list_display = ('fecha', 'credencial', 'estado_origen', 'estado_destino', 'operador')
    list_filter = ('estado_destino',)
    search_fields = ('credencial__codigo_referencia', 'motivo')
    list_select_related = ('credencial', 'operador')
    readonly_fields = ('fecha',)
    date_hierarchy = 'fecha'


@admin.register(RegistroAcceso, site=site)
class RegistroAdmin(admin.ModelAdmin):
    list_display = ('fecha_hora', 'sentido', 'resultado', 'credencial', 'dispositivo')
    list_filter = ('resultado', 'sentido', 'dispositivo__edificio')
    search_fields = ('credencial__codigo_referencia', 'motivo_rechazo')
    list_select_related = ('credencial', 'dispositivo', 'dispositivo__edificio')
    readonly_fields = ('fecha_hora',)
    date_hierarchy = 'fecha_hora'


@admin.register(Presencia, site=site)
class PresenciaAdmin(ArchivoHistoricoAdmin):
    list_display = ('ingreso', 'sujeto', 'edificio', 'estado', 'egreso')
    list_filter = ('edificio', 'estado')
    search_fields = ('sujeto__nombre', 'sujeto__apellido')
    list_select_related = ('sujeto', 'edificio')
    date_hierarchy = 'ingreso'


@admin.register(AlertaSeguridad, site=site)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('fecha_hora', 'tipo_alerta', 'nivel_gravedad', 'estado_atencion', 'dispositivo')
    list_filter = ('estado_atencion', 'nivel_gravedad', 'dispositivo__edificio')
    search_fields = ('tipo_alerta',)
    list_select_related = ('dispositivo', 'dispositivo__edificio')
    readonly_fields = ('fecha_hora',)
    date_hierarchy = 'fecha_hora'
    inlines = (ResolucionInline,)


@admin.register(ResolucionAlerta, site=site)
class ResolucionAdmin(admin.ModelAdmin):
    list_display = ('fecha_resolucion', 'alerta', 'operador')
    search_fields = ('observaciones', 'alerta__tipo_alerta')
    list_select_related = ('alerta', 'operador')
    readonly_fields = ('fecha_resolucion',)
    date_hierarchy = 'fecha_resolucion'


@admin.register(IncidenteTecnico, site=site)
class IncidenteAdmin(ArchivoHistoricoAdmin):
    list_display = ('id', 'fecha_registro', 'edificio', 'categoria', 'prioridad', 'estado')
    list_filter = ('estado', 'prioridad', 'categoria', 'edificio')
    search_fields = ('descripcion',)
    list_select_related = ('edificio', 'dispositivo')


@admin.register(OrdenIntervencion, site=site)
class OrdenAdmin(ArchivoHistoricoAdmin):
    list_display = ('id', 'incidente', 'numero', 'tecnico', 'estado', 'fecha_asignacion')
    list_filter = ('estado', 'resultado')
    list_select_related = ('incidente', 'tecnico')


site.register(CambioEstadoIncidente, ArchivoHistoricoAdmin)
site.register(CambioEstadoOrden, ArchivoHistoricoAdmin)
site.register(HistorialAsignacion, ArchivoHistoricoAdmin)
