"""Rutas publicas del modulo 6 bajo `/api/v1/`.

`config/urls.py` fusiona el ``router`` de cada app en un unico DefaultRouter,
por lo que aqui basta con registrar los ViewSets sobre ``router``.
"""
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("mezcla-objetivo", views.MezclaObjetivoViewSet, basename="mezcla-objetivo")
router.register("alertas", views.AlertaViewSet, basename="alerta")

urlpatterns = router.urls
