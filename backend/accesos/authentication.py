from rest_framework.authentication import SessionAuthentication


class ApiSessionAuthentication(SessionAuthentication):
    """Sesión Django con respuesta 401 explícita para clientes de la API."""

    def authenticate_header(self, request):
        return 'Session'
