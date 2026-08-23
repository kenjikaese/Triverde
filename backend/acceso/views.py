"""Vistas del modulo de acceso: autenticacion por token, usuarios y auditoria.

`C_Autenticacion` no es un ViewSet CRUD: son tres APIViews (login, logout,
perfil). `C_Usuarios` y `C_Auditoria` son ViewSets.
"""
from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.auditoria import registrar_auditoria
from common.permissions import IsAdministrador
from common.views import BajaLogicaMixin, FiltroEstadoMixin

from .models import BitacoraAuditoria, Rol, Usuario
from .serializers import (
    BitacoraAuditoriaSerializer,
    LoginSerializer,
    RolSerializer,
    UsuarioSerializer,
)


class LoginView(APIView):
    """POST: intercambia username+password por un token de DRF."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        usuario = serializer.validated_data["usuario"]
        token, _ = Token.objects.get_or_create(user=usuario)
        return Response(
            {
                "token": token.key,
                "usuario": {
                    "id": usuario.id,
                    "username": usuario.username,
                    "nombre_completo": usuario.nombre_completo,
                    "rol": usuario.rol_id,
                    "rol_nombre": usuario.rol.nombre,
                },
            }
        )


class LogoutView(APIView):
    """POST: invalida el token con el que se viene autenticando."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.auth:
            request.auth.delete()
        return Response({"detalle": "Sesion cerrada."})


class PerfilView(APIView):
    """GET: devuelve el usuario autenticado."""

    def get(self, request, *args, **kwargs):
        return Response(UsuarioSerializer(request.user).data)


class UsuarioViewSet(FiltroEstadoMixin, BajaLogicaMixin, viewsets.ModelViewSet):
    """CRUD de usuarios (C_Usuarios). Baja logica en vez de borrado fisico."""

    queryset = Usuario.objects.select_related("rol").all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdministrador]
    search_fields = ["username", "nombre_completo", "email"]
    ordering_fields = ["username", "nombre_completo", "estado", "date_joined"]

    def perform_create(self, serializer):
        serializer.save()
        registrar_auditoria(
            self.request.user,
            "Creacion de usuario",
            "Usuario",
            serializer.instance.pk,
            f"Usuario '{serializer.instance.username}' creado.",
        )

    def perform_update(self, serializer):
        serializer.save()
        registrar_auditoria(
            self.request.user,
            "Edicion de usuario",
            "Usuario",
            serializer.instance.pk,
            f"Usuario '{serializer.instance.username}' editado.",
        )


class RolViewSet(viewsets.ReadOnlyModelViewSet):
    """Roles del sistema (catalogo cerrado)."""

    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [IsAdministrador]


class AuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """Bitacora de auditoria (C_Auditoria): solo lectura, solo administradores."""

    queryset = BitacoraAuditoria.objects.select_related("usuario").all()
    serializer_class = BitacoraAuditoriaSerializer
    permission_classes = [IsAdministrador]
    search_fields = ["accion", "entidad_afectada", "usuario__username"]
    ordering_fields = ["fecha_hora", "accion"]
    ordering = ["-fecha_hora"]
