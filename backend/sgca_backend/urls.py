from django.urls import include, path
from django.views.generic import RedirectView

from accesos.admin import site as admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('api/', include('accesos.urls')),
    path('', RedirectView.as_view(url='api/')),
]
