from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from accesos.views import procesar_lectura_totem

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # NUESTRA RUTA PROTEGIDA (El Tótem)
    path('api/totem/lectura/', procesar_lectura_totem, name='totem-lectura'),
    
    # Las rutas automáticas
    path('api/', include('accesos.urls')),
    
    # Redirección de la raíz
    path('', RedirectView.as_view(url='api/')), 
]