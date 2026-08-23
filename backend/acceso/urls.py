"""URLs del modulo de acceso.

El `router` registra los ViewSets de esta app; `config/urls.py` fusiona los
registries de todas las apps en un unico DefaultRouter bajo `/api/v1/`.
Aqui `urlpatterns` solo lleva las rutas especiales (auth), que `config/urls.py`
tambien incluye bajo `/api/v1/`.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("usuarios", views.UsuarioViewSet, basename="usuario")
router.register("roles", views.RolViewSet, basename="rol")
router.register("auditoria", views.AuditoriaViewSet, basename="auditoria")

urlpatterns = [
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/perfil/", views.PerfilView.as_view(), name="auth-perfil"),
]
