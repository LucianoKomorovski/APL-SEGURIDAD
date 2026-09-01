from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SujetoAccesoViewSet, PuntoAccesoViewSet, RegistroAccesoViewSet, AlertaSeguridadViewSet, procesar_lectura_totem, EdificioViewSet

router = DefaultRouter()
router.register(r'sujetos', SujetoAccesoViewSet)
router.register(r'puntos-acceso', PuntoAccesoViewSet)
router.register(r'registros', RegistroAccesoViewSet)
router.register(r'alertas', AlertaSeguridadViewSet)
router.register(r'edificios', EdificioViewSet)

urlpatterns = [
    # 1. Ponemos nuestra ruta personalizada PRIMERO
    path('totem/lectura/', procesar_lectura_totem, name='totem-lectura'),
    
    # 2. Y después las rutas automáticas del router
    path('', include(router.urls)),
]