from rest_framework.routers import DefaultRouter

from .views import ProyeccionViewSet

router = DefaultRouter()
router.register(r"proyecciones", ProyeccionViewSet, basename="proyeccion")
