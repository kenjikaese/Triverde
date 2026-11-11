"""Vistas del modulo de acceso: autenticacion por token, usuarios y auditoria.

`C_Autenticacion` no es un ViewSet CRUD: son tres APIViews (login, logout,
perfil). `C_Usuarios` y `C_Auditoria` son ViewSets.
"""
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.auditoria import registrar_auditoria
from common.permissions import IsAdministrador
from common.views import BajaLogicaMixin, FiltroEstadoMixin, entero_o_none

from .models import BitacoraAuditoria, Rol, Usuario
from .serializers import (
    BitacoraAuditoriaSerializer,
    LoginSerializer,
    PerfilSerializer,
    RolSerializer,
    UsuarioSerializer,
)


class LoginView(APIView):
    """C_Autenticacion: POST: intercambia username+password por un token de DRF."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        usuario = serializer.validated_data["usuario"]
        token, _ = Token.objects.get_or_create(user=usuario)
        # CU-01: el inicio de sesion queda en la bitacora (poscondicion del caso de uso).
        registrar_auditoria(usuario, "Inicio de sesion", "Usuario", usuario.id)
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
    """C_Autenticacion: POST: invalida el token con el que se viene autenticando."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.auth:
            request.auth.delete()
        # CU-02: el cierre de sesion queda en la bitacora.
        registrar_auditoria(request.user, "Cierre de sesion", "Usuario", request.user.id)
        return Response({"detalle": "Sesion cerrada."})


class PerfilView(APIView):
    """C_Autenticacion: CU-04. GET: devuelve el usuario autenticado. PATCH: actualiza sus datos."""

    def get(self, request, *args, **kwargs):
        return Response(UsuarioSerializer(request.user).data)

    def patch(self, request, *args, **kwargs):
        serializer = PerfilSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        cambio_clave = "password" in serializer.validated_data
        serializer.save()
        registrar_auditoria(
            request.user,
            "Edicion de perfil",
            "Usuario",
            request.user.pk,
            "Datos del perfil actualizados, incluida la contrasena."
            if cambio_clave
            else "Datos del perfil actualizados.",
        )
        return Response(UsuarioSerializer(request.user).data)


class UsuarioViewSet(FiltroEstadoMixin, BajaLogicaMixin, viewsets.ModelViewSet):
    """CRUD de usuarios (C_Usuarios). Baja logica en vez de borrado fisico.

    Reglas de CU-05 y CU-06: el administrador no puede desactivar su propia
    cuenta ni quitarse su propio rol, porque el sistema no puede quedar sin
    ningun usuario administrador activo. Y al desactivar a alguien se le cierra
    la sesion en curso, para que la desactivacion tenga efecto de inmediato.
    """

    queryset = Usuario.objects.select_related("rol").all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdministrador]
    search_fields = ["username", "nombre_completo", "email"]
    ordering_fields = ["username", "nombre_completo", "estado", "date_joined"]

    # -- reglas sobre la propia cuenta ---------------------------------------

    def _es_la_propia_cuenta(self, usuario):
        return usuario.pk == self.request.user.pk

    def _rechazar(self, detalle):
        return Response({"detalle": detalle}, status=status.HTTP_400_BAD_REQUEST)

    def _cerrar_sesion(self, usuario):
        """CU-05 Excepcion 2: invalida el token del usuario desactivado.

        Sin esto, quien ya tenia la sesion abierta seguiria operando con su
        token hasta cerrarla a mano, y la desactivacion no tendria efecto real
        en ese dispositivo.
        """
        Token.objects.filter(user=usuario).delete()

    # -- CU-05: desactivar ---------------------------------------------------

    def destroy(self, request, *args, **kwargs):
        """Desactiva la cuenta (baja logica del mixin) y cierra su sesion."""
        usuario = self.get_object()
        if self._es_la_propia_cuenta(usuario):
            # CU-05 Excepcion 1.
            return self._rechazar(
                "No puedes desactivar tu propia cuenta: el sistema debe "
                "conservar al menos un administrador activo."
            )
        respuesta = super().destroy(request, *args, **kwargs)
        self._cerrar_sesion(usuario)
        registrar_auditoria(
            request.user,
            "Desactivacion de usuario",
            "Usuario",
            usuario.pk,
            f"Usuario '{usuario.username}' desactivado.",
        )
        return respuesta

    # -- CU-05 reactivacion y CU-06 cambio de rol, ambos por PATCH -----------

    def update(self, request, *args, **kwargs):
        usuario = self.get_object()
        rol_pedido = entero_o_none(request.data.get("rol"))

        if self._es_la_propia_cuenta(usuario):
            if request.data.get("estado") == Usuario.INACTIVO:
                # CU-05 Excepcion 1, tambien por PATCH y no solo por el boton.
                return self._rechazar(
                    "No puedes desactivar tu propia cuenta: el sistema debe "
                    "conservar al menos un administrador activo."
                )
            if rol_pedido is not None and rol_pedido != usuario.rol_id:
                # CU-06 Excepcion 2.
                return self._rechazar(
                    "No puedes cambiar el rol de tu propia cuenta: el sistema "
                    "debe conservar al menos un administrador activo."
                )

        # CU-06 Excepcion 1: pedir el rol que el usuario ya tiene no cambia
        # nada, asi que tampoco deja registro en la bitacora.
        self._sin_cambios = (
            rol_pedido is not None
            and rol_pedido == usuario.rol_id
            and set(request.data) == {"rol"}
        )
        self._estado_anterior = usuario.estado
        return super().update(request, *args, **kwargs)

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
        usuario = serializer.save()
        if (
            usuario.estado == Usuario.INACTIVO
            and getattr(self, "_estado_anterior", None) == Usuario.ACTIVO
        ):
            self._cerrar_sesion(usuario)
        if getattr(self, "_sin_cambios", False):
            return
        registrar_auditoria(
            self.request.user,
            "Edicion de usuario",
            "Usuario",
            usuario.pk,
            f"Usuario '{usuario.username}' editado.",
        )


class RolViewSet(viewsets.ReadOnlyModelViewSet):
    """C_Usuarios: Roles del sistema (catalogo cerrado)."""

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
