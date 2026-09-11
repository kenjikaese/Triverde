"""Rutas publicas del modulo 6 bajo `/api/v1/`."""
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("mezcla-objetivo", views.MezclaObjetivoViewSet, basename="mezcla-objetivo")
router.register("alertas", views.AlertaViewSet, basename="alerta")

urlpatterns = []
