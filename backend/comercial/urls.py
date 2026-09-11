"""URLs del modulo comercial.

Define el `router` de la app (que `config/urls.py` fusiona en el router unico
de `/api/v1/`) y la ruta de la cuenta corriente, que no es un ViewSet porque
el saldo es calculado y no tiene un objeto propio detras.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("cotizaciones", views.CotizacionViewSet, basename="cotizacion")
router.register("ventas", views.VentaViewSet, basename="venta")
router.register("cobros", views.CobroViewSet, basename="cobro")
router.register(
    "documentos-tributarios",
    views.DocumentoTributarioViewSet,
    basename="documento-tributario",
)

urlpatterns = [
    path(
        "cuenta-corriente/<int:cliente_id>/",
        views.CuentaCorrienteView.as_view(),
        name="cuenta-corriente",
    ),
]
