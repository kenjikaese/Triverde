"""URLs del modulo de recepcion.

El `router` registra el ViewSet de recepciones; `config/urls.py` fusiona los
registries de todas las apps en un unico DefaultRouter bajo `/api/v1/`.
Aqui `urlpatterns` lleva la ruta especial de sincronizacion (CU-33).
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("recepciones", views.RecepcionViewSet, basename="recepcion")

urlpatterns = [
    path("sincronizacion/", views.SincronizacionView.as_view(), name="sincronizacion"),
]
