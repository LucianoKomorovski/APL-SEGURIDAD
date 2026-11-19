from django.urls import include, path
from django.views.generic import RedirectView

from .deployment import health

from accesos.admin import site as admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('api/health/', health),
    path('api/', include('accesos.urls')),
    path('', RedirectView.as_view(url='api/')),
]
