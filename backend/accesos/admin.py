from django.contrib import admin
from .models import NivelAcceso, SujetoAcceso, OperadorSistema, HorarioPermitido, ComponenteZona, PuntoAcceso, ControladorAcceso, Credencial, RegistroAcceso, AlertaSeguridad, ResolucionAlerta, Edificio

# Hacemos una lista con todos tus modelos
modelos = [NivelAcceso, SujetoAcceso, OperadorSistema, HorarioPermitido, ComponenteZona, PuntoAcceso, ControladorAcceso, Credencial, RegistroAcceso, AlertaSeguridad, ResolucionAlerta, Edificio]

# Los registramos todos juntos
for modelo in modelos:
    admin.site.register(modelo)
