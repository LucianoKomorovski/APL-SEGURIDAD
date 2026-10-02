from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AlertaSeguridadViewSet,
    ComponenteZonaViewSet,
    ControladorAccesoViewSet,
    CredencialViewSet,
    EdificioViewSet,
    HorarioPermitidoViewSet,
    IncidenteTecnicoViewSet,
    NivelAccesoViewSet,
    OrdenIntervencionViewSet,
    PuntoAccesoViewSet,
    RegistroAccesoViewSet,
    SujetoAccesoViewSet,
    TecnicoViewSet,
    csrf_cookie,
    heartbeat_totem,
    login_sistema,
    logout_sistema,
    procesar_evento_hardware,
    procesar_lectura_totem,
    usuario_actual,
)

router = DefaultRouter()
router.register(r'sujetos', SujetoAccesoViewSet)
router.register(r'puntos-acceso', PuntoAccesoViewSet)
router.register(r'registros', RegistroAccesoViewSet)
router.register(r'alertas', AlertaSeguridadViewSet)
router.register(r'edificios', EdificioViewSet)
router.register(r'niveles', NivelAccesoViewSet)
router.register(r'zonas', ComponenteZonaViewSet)
router.register(r'horarios', HorarioPermitidoViewSet)
router.register(r'controladores', ControladorAccesoViewSet)
router.register(r'credenciales', CredencialViewSet)
router.register(r'tecnicos', TecnicoViewSet)
router.register(r'incidentes', IncidenteTecnicoViewSet)
router.register(r'ordenes', OrdenIntervencionViewSet)

urlpatterns = [
    path('auth/csrf/', csrf_cookie, name='auth-csrf'),
    path('auth/login/', login_sistema, name='auth-login'),
    path('auth/logout/', logout_sistema, name='auth-logout'),
    path('auth/me/', usuario_actual, name='auth-me'),
    path('totem/lectura/', procesar_lectura_totem, name='totem-lectura'),
    path('totem/evento/', procesar_evento_hardware, name='totem-evento'),
    path('totem/heartbeat/', heartbeat_totem, name='totem-heartbeat'),
    path('', include(router.urls)),
]
