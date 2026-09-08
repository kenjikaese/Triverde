"""URLs del modulo de inventario, pilas y procesos.

Solo define el `router` de la app; `config/urls.py` fusiona los registries de
todas las apps en un unico DefaultRouter bajo `/api/v1/`.
"""
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("inventario", views.InventarioViewSet, basename="inventario")
router.register("pilas", views.PilaViewSet, basename="pila")
router.register("procesos-pila", views.ProcesoPilaViewSet, basename="procesopila")

urlpatterns = []
