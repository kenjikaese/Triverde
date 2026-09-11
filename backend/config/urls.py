"""URLs raiz del backend de Triverde.

La capa API (DRF) vive bajo `/api/v1/`: cada app registra sus ViewSets en su
propio `router` (`<app>/urls.py`) y aqui se fusionan los registries en un unico
`DefaultRouter` para que `/api/v1/` liste todos los endpoints. Las rutas
especiales (auth y sincronizacion) se incluyen desde sus apps.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from acceso.urls import router as acceso_router
from comercial.urls import router as comercial_router
from configuracion.urls import router as configuracion_router
from inventario.urls import router as inventario_router
from mantenedores.urls import router as mantenedores_router
from recepcion.urls import router as recepcion_router
from proyecciones.urls import router as proyecciones_router

router = DefaultRouter()
for app_router in (
    acceso_router,
    comercial_router,
    configuracion_router,
    mantenedores_router,
    recepcion_router,
    inventario_router,
    proyecciones_router,
):
    router.registry.extend(app_router.registry)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(router.urls)),
    path("api/v1/", include("acceso.urls")),
    path("api/v1/", include("comercial.urls")),
    path("api/v1/", include("recepcion.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
