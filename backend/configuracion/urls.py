"""URLs del modulo de configuracion.

Solo define el `router` de la app; `config/urls.py` fusiona los registries de
todas las apps en un unico DefaultRouter bajo `/api/v1/`.
"""
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("parametros", views.ParametroConversionViewSet, basename="parametro")
router.register("tarifas", views.TarifaRecepcionViewSet, basename="tarifa")
router.register(
    "historial-parametros",
    views.HistorialCambioParametroViewSet,
    basename="historial-parametro",
)
router.register("recetas", views.RecetaMezclaViewSet, basename="receta")
router.register("costo-transporte", views.CostoTransporteViewSet, basename="costo-transporte")
router.register("costos-operativos", views.CostoOperativoViewSet, basename="costo-operativo")

urlpatterns = []
