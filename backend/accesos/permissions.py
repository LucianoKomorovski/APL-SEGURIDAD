from rest_framework.permissions import BasePermission

from .models import OperadorSistema


def cuenta_activa(user):
    if not user or not user.is_authenticated or not user.is_active:
        return None
    try:
        cuenta = user.cuenta_sgca
    except AttributeError:
        return None
    return cuenta if cuenta.activo else None


class EsOperador(BasePermission):
    message = 'Esta operación requiere una cuenta de operador.'

    def has_permission(self, request, view):
        cuenta = cuenta_activa(request.user)
        return bool(
            cuenta
            and cuenta.rol == 'Operador'
            and OperadorSistema.objects.filter(pk=cuenta.persona_id).exists()
        )


class EsUsuarioSGCA(BasePermission):
    message = 'Se requiere una cuenta activa de SGCA-APL.'

    def has_permission(self, request, view):
        return cuenta_activa(request.user) is not None


class EsTecnico(BasePermission):
    message = 'Esta operación requiere una cuenta de técnico.'

    def has_permission(self, request, view):
        cuenta = cuenta_activa(request.user)
        return bool(cuenta and cuenta.rol == 'Tecnico')
