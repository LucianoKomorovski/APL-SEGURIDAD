"""Motor de validación de accesos físicos (UC-01).

Separa la lógica de negocio de las vistas HTTP para poder testearla
sin hardware y reutilizarla desde el simulador o un controlador real.
"""

from dataclasses import dataclass
from datetime import datetime, time

from django.utils import timezone

from .models import ControladorAcceso, Credencial, NivelAcceso, SujetoAcceso


DIAS_NOMBRE_A_INDICE = {
    '0': 0, 'lunes': 0, 'lun': 0, 'monday': 0,
    '1': 1, 'martes': 1, 'mar': 1, 'tuesday': 1,
    '2': 2, 'miercoles': 2, 'miércoles': 2, 'mie': 2, 'mié': 2, 'wednesday': 2,
    '3': 3, 'jueves': 3, 'jue': 3, 'thursday': 3,
    '4': 4, 'viernes': 4, 'vie': 4, 'friday': 4,
    '5': 5, 'sabado': 5, 'sábado': 5, 'sab': 5, 'sáb': 5, 'saturday': 5,
    '6': 6, 'domingo': 6, 'dom': 6, 'sunday': 6,
}

ACCION_ABRIR = 'ABRIR_PUERTA'
ACCION_BLOQUEAR = 'BLOQUEAR_PUERTA'


@dataclass
class ResultadoValidacion:
    concedido: bool
    accion: str
    motivo: str | None
    tipo_alerta: str | None
    nivel_gravedad: str | None
    dispositivo: ControladorAcceso | None
    credencial: Credencial | None


def parsear_dias_semana(valor: str) -> set[int]:
    if not valor:
        return set()
    dias = set()
    for parte in valor.replace(';', ',').split(','):
        clave = parte.strip().lower()
        if not clave:
            continue
        if clave in DIAS_NOMBRE_A_INDICE:
            dias.add(DIAS_NOMBRE_A_INDICE[clave])
    return dias


def hora_dentro_de_ventana(actual: time, inicio: time, fin: time) -> bool:
    if inicio <= fin:
        return inicio <= actual <= fin
    return actual >= inicio or actual <= fin


def ancestros_de_zona(zona):
    vistos = set()
    actual = zona
    while actual is not None and actual.pk not in vistos:
        yield actual
        vistos.add(actual.pk)
        actual = actual.zona_padre


def zona_esta_permitida(zona_punto, nivel: NivelAcceso) -> bool:
    ids_permitidos = set(nivel.zonas.values_list('pk', flat=True))
    if not ids_permitidos:
        return False
    return any(zona.pk in ids_permitidos for zona in ancestros_de_zona(zona_punto))


def _momento_local(momento: datetime) -> datetime:
    if timezone.is_aware(momento):
        return timezone.localtime(momento)
    return momento


def horario_esta_permitido(nivel: NivelAcceso, momento: datetime) -> bool:
    horarios = list(nivel.horarios.all())
    if not horarios:
        return True
    local = _momento_local(momento)
    dia = local.weekday()
    hora = local.time()
    for ventana in horarios:
        if dia not in parsear_dias_semana(ventana.dias_semana):
            continue
        if hora_dentro_de_ventana(hora, ventana.hora_inicio, ventana.hora_fin):
            return True
    return False


class MotorValidacionAcceso:
    def evaluar(self, codigo_rfid: str | None, ip_totem: str | None, ahora=None) -> ResultadoValidacion:
        ahora = _momento_local(ahora or timezone.now())
        dispositivo = ControladorAcceso.objects.filter(direccion_ip=ip_totem).select_related(
            'punto_acceso__zona',
            'edificio',
        ).first()

        if not dispositivo:
            return ResultadoValidacion(
                concedido=False,
                accion=ACCION_BLOQUEAR,
                motivo='dispositivo no encontrado',
                tipo_alerta=None,
                nivel_gravedad=None,
                dispositivo=None,
                credencial=None,
            )

        credencial = Credencial.objects.filter(codigo_referencia=codigo_rfid).select_related(
            'persona',
        ).first()

        if not credencial:
            return self._denegar(
                dispositivo,
                None,
                'tarjeta inexistente',
                'Alta',
            )

        if credencial.estado == 'Bloqueada':
            return self._denegar(dispositivo, credencial, 'tarjeta bloqueada', 'Alta')

        if credencial.estado == 'Vencida' or credencial.fecha_vencimiento < ahora.date():
            return self._denegar(dispositivo, credencial, 'tarjeta vencida', 'Media')

        if credencial.estado != 'Activa':
            return self._denegar(
                dispositivo,
                credencial,
                f'tarjeta {credencial.estado}',
                'Alta',
            )

        sujeto = SujetoAcceso.objects.filter(pk=credencial.persona_id).select_related(
            'nivel_acceso',
            'edificio',
        ).first()

        if not sujeto:
            return self._denegar(
                dispositivo,
                credencial,
                'la credencial no pertenece a un sujeto de acceso',
                'Alta',
            )

        if sujeto.estado != 'Activo':
            return self._denegar(dispositivo, credencial, 'sujeto inactivo', 'Alta')

        if (
            sujeto.edificio_id
            and dispositivo.edificio_id
            and sujeto.edificio_id != dispositivo.edificio_id
        ):
            return self._denegar(
                dispositivo,
                credencial,
                'edificio no autorizado',
                'Media',
            )

        nivel = sujeto.nivel_acceso
        if not nivel:
            return self._denegar(
                dispositivo,
                credencial,
                'sin nivel de acceso asignado',
                'Media',
            )

        zona_punto = dispositivo.punto_acceso.zona
        if not zona_esta_permitida(zona_punto, nivel):
            return self._denegar(
                dispositivo,
                credencial,
                f'zona no permitida ({zona_punto.nombre_zona})',
                'Media',
            )

        if not horario_esta_permitido(nivel, ahora):
            return self._denegar(
                dispositivo,
                credencial,
                'fuera de horario permitido',
                'Media',
            )

        return ResultadoValidacion(
            concedido=True,
            accion=ACCION_ABRIR,
            motivo=None,
            tipo_alerta=None,
            nivel_gravedad=None,
            dispositivo=dispositivo,
            credencial=credencial,
        )

    def _denegar(self, dispositivo, credencial, motivo, gravedad) -> ResultadoValidacion:
        return ResultadoValidacion(
            concedido=False,
            accion=ACCION_BLOQUEAR,
            motivo=motivo,
            tipo_alerta=f'acceso denegado: {motivo}',
            nivel_gravedad=gravedad,
            dispositivo=dispositivo,
            credencial=credencial,
        )
