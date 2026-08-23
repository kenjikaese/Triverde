"""URLs del modulo de mantenedores.

Solo define el `router` de la app; `config/urls.py` fusiona los registries de
todas las apps en un unico DefaultRouter bajo `/api/v1/`.
"""
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("clientes", views.ClienteViewSet, basename="cliente")
router.register("transportistas", views.TransportistaViewSet, basename="transportista")
router.register("vehiculos", views.VehiculoViewSet, basename="vehiculo")
router.register("materiales", views.MaterialViewSet, basename="material")
router.register("productos", views.ProductoViewSet, basename="producto")

urlpatterns = []
