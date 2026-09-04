from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AlertaSeguridadViewSet,
    ComponenteZonaViewSet,
    ControladorAccesoViewSet,
    CredencialViewSet,
    EdificioViewSet,
    HorarioPermitidoViewSet,
    NivelAccesoViewSet,
    PuntoAccesoViewSet,
    RegistroAccesoViewSet,
    SujetoAccesoViewSet,
    heartbeat_totem,
    login_operador,
    procesar_evento_hardware,
    procesar_lectura_totem,
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

urlpatterns = [
    path('auth/login/', login_operador, name='login-operador'),
    path('totem/lectura/', procesar_lectura_totem, name='totem-lectura'),
    path('totem/evento/', procesar_evento_hardware, name='totem-evento'),
    path('totem/heartbeat/', heartbeat_totem, name='totem-heartbeat'),
    path('', include(router.urls)),
]
