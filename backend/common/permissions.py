"""Permisos por rol (docs/13 C_* y tabla de roles del brief de la capa API).

Reglas:
- Administrador: acceso total.
- Operador: recepciones y sync en escritura; lectura de mantenedores y
  parametros/tarifas. Sin acceso a usuarios ni auditoria.
- Transportista: solo sus recepciones (crear y ver, CU-28); sin acceso al resto.

Todos exigen usuario autenticado con `estado = activo` (baja logica).
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from acceso.models import Rol, Usuario


def _usuario_valido(user):
    return bool(
        user
        and user.is_authenticated
        and user.rol_id
        and user.estado == Usuario.ACTIVO
    )


class IsAdministrador(BasePermission):
    message = "Solo un administrador puede realizar esta accion."

    def has_permission(self, request, view):
        return _usuario_valido(request.user) and (
            request.user.rol.nombre == Rol.ADMINISTRADOR
        )


class IsOperadorOAdministrador(BasePermission):
    message = "Solo un operador o administrador puede realizar esta accion."

    def has_permission(self, request, view):
        return _usuario_valido(request.user) and request.user.rol.nombre in (
            Rol.OPERADOR,
            Rol.ADMINISTRADOR,
        )


class EsAdministradorOOperadorLectura(BasePermission):
    """Administrador: todo; operador: solo lectura; transportista: nada."""

    message = (
        "Solo el administrador puede modificar este recurso; "
        "el operador solo puede leerlo."
    )

    def has_permission(self, request, view):
        user = request.user
        if not _usuario_valido(user):
            return False
        if user.rol.nombre == Rol.ADMINISTRADOR:
            return True
        if user.rol.nombre == Rol.OPERADOR:
            return request.method in SAFE_METHODS
        return False


class EsOperadorOAdministradorOTransportista(BasePermission):
    """Recepciones: admin/operador full; transportista solo crea y lee (CU-28).

    La restriccion de que el transportista solo vea las suyas se aplica en el
    `get_queryset()` del viewset, no aqui.
    """

    message = (
        "El transportista solo puede crear y consultar sus propias recepciones."
    )

    def has_permission(self, request, view):
        user = request.user
        if not _usuario_valido(user):
            return False
        if user.rol.nombre in (Rol.OPERADOR, Rol.ADMINISTRADOR):
            return True
        if user.rol.nombre == Rol.TRANSPORTISTA:
            return request.method in SAFE_METHODS or request.method == "POST"
        return False
