from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from .models import (
    AlertaSeguridad,
    CambioEstadoIncidente,
    CambioEstadoOrden,
    ControladorAcceso,
    CuentaSistema,
    Edificio,
    HistorialAsignacion,
    IncidenteTecnico,
    OperadorSistema,
    OrdenIntervencion,
)


class ReglaIncidente(Exception):
    pass


def _texto(valor, nombre):
    valor = (valor or '').strip()
    if not valor:
        raise ReglaIncidente(f'{nombre} es obligatorio.')
    return valor


def _operador(cuenta):
    if not cuenta or cuenta.rol != 'Operador' or not cuenta.activo:
        raise ReglaIncidente('La acción requiere una cuenta de operador activa.')
    try:
        return OperadorSistema.objects.get(pk=cuenta.persona_id)
    except OperadorSistema.DoesNotExist as exc:
        raise ReglaIncidente('La cuenta no está vinculada con un operador.') from exc


def _tecnico(cuenta):
    if (
        not cuenta
        or cuenta.rol != 'Tecnico'
        or not cuenta.activo
        or not cuenta.usuario.is_active
    ):
        raise ReglaIncidente('El técnico asignado debe tener una cuenta activa.')
    return cuenta


def _cambiar_incidente(incidente, destino, actor, detalle=''):
    origen = incidente.estado
    incidente.estado = destino
    CambioEstadoIncidente.objects.create(
        incidente=incidente,
        estado_origen=origen,
        estado_destino=destino,
        actor=actor,
        detalle=detalle,
    )


def _cambiar_orden(orden, destino, actor, detalle=''):
    origen = orden.estado
    orden.estado = destino
    CambioEstadoOrden.objects.create(
        orden=orden,
        estado_origen=origen,
        estado_destino=destino,
        actor=actor,
        detalle=detalle,
    )


@transaction.atomic
def registrar_incidente(*, cuenta, edificio, descripcion, categoria, prioridad='Media',
                        dispositivo=None, alerta=None, incidente_anterior=None):
    operador = _operador(cuenta)
    if not isinstance(edificio, Edificio):
        raise ReglaIncidente('El edificio es obligatorio.')
    if categoria not in dict(IncidenteTecnico.CATEGORIAS):
        raise ReglaIncidente('Categoría inválida.')
    if prioridad not in dict(IncidenteTecnico.PRIORIDADES):
        raise ReglaIncidente('Prioridad inválida.')
    if dispositivo and dispositivo.edificio_id != edificio.pk:
        raise ReglaIncidente('El dispositivo no pertenece al edificio indicado.')
    if alerta:
        if alerta.dispositivo.edificio_id != edificio.pk:
            raise ReglaIncidente('La alerta no pertenece al edificio indicado.')
        if dispositivo and alerta.dispositivo_id != dispositivo.pk:
            raise ReglaIncidente('La alerta no corresponde al dispositivo indicado.')
        if IncidenteTecnico.objects.filter(alerta_origen=alerta).exists():
            raise ReglaIncidente('La alerta ya originó un incidente.')
    if incidente_anterior:
        if incidente_anterior.estado != 'Cerrado':
            raise ReglaIncidente('El incidente anterior debe estar cerrado.')
        if incidente_anterior.edificio_id != edificio.pk:
            raise ReglaIncidente('El incidente anterior debe pertenecer al mismo edificio.')

    try:
        incidente = IncidenteTecnico.objects.create(
            edificio=edificio,
            dispositivo=dispositivo,
            alerta_origen=alerta,
            incidente_anterior=incidente_anterior,
            descripcion=_texto(descripcion, 'La descripción'),
            categoria=categoria,
            prioridad=prioridad,
            registrado_por=operador,
        )
    except IntegrityError as exc:
        raise ReglaIncidente('No se pudo registrar: la alerta ya tiene un incidente.') from exc
    CambioEstadoIncidente.objects.create(
        incidente=incidente,
        estado_origen='',
        estado_destino='Registrado',
        actor=cuenta,
        detalle='Registro del incidente.',
    )
    return incidente


@transaction.atomic
def evaluar_incidente(*, incidente, cuenta):
    incidente = IncidenteTecnico.objects.select_for_update().get(pk=incidente.pk)
    operador = _operador(cuenta)
    if incidente.estado != 'Registrado':
        raise ReglaIncidente('Solo se puede evaluar un incidente registrado.')
    _cambiar_incidente(incidente, 'Evaluado', cuenta, 'Evaluación del operador.')
    incidente.evaluado_por = operador
    incidente.fecha_evaluacion = timezone.now()
    incidente.save(update_fields=['estado', 'evaluado_por', 'fecha_evaluacion', 'fecha_actualizacion'])
    return incidente


@transaction.atomic
def asignar_intervencion(*, incidente, tecnico, cuenta):
    incidente = IncidenteTecnico.objects.select_for_update().get(pk=incidente.pk)
    tecnico = _tecnico(tecnico)
    operador = _operador(cuenta)
    if incidente.estado != 'Evaluado':
        raise ReglaIncidente('El incidente debe estar evaluado para asignar una intervención.')
    if OrdenIntervencion.objects.select_for_update().filter(
        incidente=incidente, estado__in=OrdenIntervencion.ESTADOS_ACTIVOS
    ).exists():
        raise ReglaIncidente('El incidente ya tiene una orden activa.')
    numero = (OrdenIntervencion.objects.filter(incidente=incidente).aggregate(
        ultimo=Max('numero')
    )['ultimo'] or 0) + 1
    try:
        orden = OrdenIntervencion.objects.create(
            incidente=incidente,
            numero=numero,
            tecnico=tecnico,
            asignada_por=operador,
        )
    except IntegrityError as exc:
        raise ReglaIncidente('El incidente ya tiene una orden activa.') from exc
    HistorialAsignacion.objects.create(
        orden=orden, tecnico_nuevo=tecnico, operador=operador, motivo='Asignación inicial.'
    )
    CambioEstadoOrden.objects.create(
        orden=orden,
        estado_origen='',
        estado_destino='Asignada',
        actor=cuenta,
        detalle='Asignación inicial.',
    )
    _cambiar_incidente(incidente, 'En atencion', cuenta, f'Orden {numero} asignada.')
    incidente.save(update_fields=['estado', 'fecha_actualizacion'])
    return orden


@transaction.atomic
def iniciar_orden(*, orden, cuenta):
    orden = OrdenIntervencion.objects.select_for_update().select_related('incidente').get(pk=orden.pk)
    if cuenta.pk != orden.tecnico_id or cuenta.rol != 'Tecnico' or not cuenta.activo:
        raise ReglaIncidente('Solo el técnico asignado puede iniciar la orden.')
    if orden.estado != 'Asignada':
        raise ReglaIncidente('Solo se puede iniciar una orden asignada.')
    _cambiar_orden(orden, 'En curso', cuenta, 'Inicio del trabajo técnico.')
    orden.fecha_inicio = timezone.now()
    orden.save(update_fields=['estado', 'fecha_inicio'])
    return orden


@transaction.atomic
def informar_orden(*, orden, cuenta, diagnostico, trabajo_realizado, resultado):
    orden = OrdenIntervencion.objects.select_for_update().select_related('incidente').get(pk=orden.pk)
    if cuenta.pk != orden.tecnico_id or cuenta.rol != 'Tecnico' or not cuenta.activo:
        raise ReglaIncidente('Solo el técnico asignado puede informar la orden.')
    if orden.estado != 'En curso':
        raise ReglaIncidente('Solo se puede informar una orden en curso.')
    if resultado not in dict(OrdenIntervencion.RESULTADOS):
        raise ReglaIncidente('Resultado técnico inválido.')
    diagnostico = _texto(diagnostico, 'El diagnóstico')
    trabajo_realizado = _texto(trabajo_realizado, 'El trabajo realizado')
    orden.diagnostico = diagnostico
    orden.trabajo_realizado = trabajo_realizado
    orden.resultado = resultado
    orden.fecha_informe = timezone.now()
    _cambiar_orden(orden, 'Informada', cuenta, f'Resultado: {resultado}.')
    orden.save(update_fields=[
        'estado', 'diagnostico', 'trabajo_realizado', 'resultado', 'fecha_informe'
    ])
    incidente = IncidenteTecnico.objects.select_for_update().get(pk=orden.incidente_id)
    if incidente.estado != 'En atencion':
        raise ReglaIncidente('El incidente no está en atención.')
    _cambiar_incidente(
        incidente, 'Pendiente verificacion', cuenta, f'Orden {orden.numero} informada.'
    )
    incidente.save(update_fields=['estado', 'fecha_actualizacion'])
    return orden


@transaction.atomic
def verificar_orden(*, orden, cuenta, aceptada, observaciones):
    orden = OrdenIntervencion.objects.select_for_update().select_related('incidente').get(pk=orden.pk)
    operador = _operador(cuenta)
    if orden.estado != 'Informada':
        raise ReglaIncidente('Solo se puede verificar una orden informada.')
    if not isinstance(aceptada, bool):
        raise ReglaIncidente('Debe indicar si la verificación fue aceptada o rechazada.')
    if aceptada and orden.resultado != 'solucionado':
        raise ReglaIncidente(
            'Solo puede aceptarse una orden cuyo resultado sea solucionado.'
        )
    observaciones = _texto(observaciones, 'Las observaciones de verificación')
    orden.verificacion_aceptada = aceptada
    orden.observaciones_verificacion = observaciones
    orden.verificada_por = operador
    orden.fecha_verificacion = timezone.now()
    _cambiar_orden(
        orden,
        'Verificada',
        cuenta,
        'Verificación aceptada.' if aceptada else 'Verificación rechazada.',
    )
    orden.save(update_fields=[
        'estado', 'verificacion_aceptada', 'observaciones_verificacion',
        'verificada_por', 'fecha_verificacion',
    ])
    incidente = IncidenteTecnico.objects.select_for_update().get(pk=orden.incidente_id)
    if incidente.estado != 'Pendiente verificacion':
        raise ReglaIncidente('El incidente no está pendiente de verificación.')
    if not aceptada:
        _cambiar_incidente(
            incidente, 'Evaluado', cuenta, f'Verificación rechazada para la orden {orden.numero}.'
        )
        incidente.save(update_fields=['estado', 'fecha_actualizacion'])
    return orden


@transaction.atomic
def cerrar_incidente(*, incidente, cuenta):
    incidente = IncidenteTecnico.objects.select_for_update().get(pk=incidente.pk)
    operador = _operador(cuenta)
    if incidente.estado != 'Pendiente verificacion':
        raise ReglaIncidente('El incidente debe estar pendiente de verificación.')
    ultima = incidente.ordenes.order_by('-numero').first()
    if not ultima or ultima.estado != 'Verificada' or ultima.verificacion_aceptada is not True:
        raise ReglaIncidente('El cierre requiere una verificación satisfactoria del operador.')
    if ultima.resultado != 'solucionado':
        raise ReglaIncidente('Solo puede cerrarse una intervención informada como solucionada.')
    _cambiar_incidente(incidente, 'Cerrado', cuenta, f'Cierre tras verificar la orden {ultima.numero}.')
    incidente.cerrado_por = operador
    incidente.fecha_cierre = timezone.now()
    incidente.save(update_fields=['estado', 'cerrado_por', 'fecha_cierre', 'fecha_actualizacion'])
    return incidente


@transaction.atomic
def descartar_incidente(*, incidente, cuenta, motivo):
    incidente = IncidenteTecnico.objects.select_for_update().get(pk=incidente.pk)
    operador = _operador(cuenta)
    motivo = _texto(motivo, 'El motivo de descarte')
    if incidente.estado not in ('Registrado', 'Evaluado'):
        raise ReglaIncidente('Solo se puede descartar un incidente registrado o evaluado.')
    _cambiar_incidente(incidente, 'Descartado', cuenta, motivo)
    incidente.motivo_descarte = motivo
    incidente.descartado_por = operador
    incidente.fecha_descarte = timezone.now()
    incidente.save(update_fields=[
        'estado', 'motivo_descarte', 'descartado_por', 'fecha_descarte', 'fecha_actualizacion'
    ])
    return incidente


@transaction.atomic
def cancelar_orden(*, orden, cuenta, motivo):
    orden = OrdenIntervencion.objects.select_for_update().select_related('incidente').get(pk=orden.pk)
    operador = _operador(cuenta)
    motivo = _texto(motivo, 'El motivo de cancelación')
    if orden.estado not in ('Asignada', 'En curso'):
        raise ReglaIncidente('Solo se puede cancelar una orden asignada o en curso.')
    _cambiar_orden(orden, 'Cancelada', cuenta, motivo)
    orden.motivo_cancelacion = motivo
    orden.cancelada_por = operador
    orden.fecha_cancelacion = timezone.now()
    orden.save(update_fields=[
        'estado', 'motivo_cancelacion', 'cancelada_por', 'fecha_cancelacion'
    ])
    incidente = IncidenteTecnico.objects.select_for_update().get(pk=orden.incidente_id)
    _cambiar_incidente(incidente, 'Evaluado', cuenta, f'Orden {orden.numero} cancelada.')
    incidente.save(update_fields=['estado', 'fecha_actualizacion'])
    return orden


@transaction.atomic
def reasignar_orden(*, orden, tecnico, cuenta, motivo):
    orden = OrdenIntervencion.objects.select_for_update().get(pk=orden.pk)
    tecnico = _tecnico(tecnico)
    operador = _operador(cuenta)
    motivo = _texto(motivo, 'El motivo de reasignación')
    if orden.estado not in ('Asignada', 'En curso'):
        raise ReglaIncidente('Una orden informada o finalizada no puede reasignarse.')
    if orden.tecnico_id == tecnico.pk:
        raise ReglaIncidente('Debe seleccionar un técnico diferente.')
    anterior = orden.tecnico
    orden.tecnico = tecnico
    if orden.estado == 'En curso':
        _cambiar_orden(orden, 'Asignada', cuenta, motivo)
        orden.fecha_inicio = None
    orden.save(update_fields=['tecnico', 'estado', 'fecha_inicio'])
    HistorialAsignacion.objects.create(
        orden=orden,
        tecnico_anterior=anterior,
        tecnico_nuevo=tecnico,
        operador=operador,
        motivo=motivo,
    )
    return orden
