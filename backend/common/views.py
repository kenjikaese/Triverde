"""Vistas base reutilizables: filtros por query param y baja logica."""
from datetime import date

from rest_framework.response import Response


class FiltroEstadoMixin:
    """Filtra por el query param `estado` (p. ej. `?estado=activo`).

    Permite listar solo los activos, sin necesidad de django-filter.
    """

    parametro_estado = "estado"

    def get_queryset(self):
        queryset = super().get_queryset()
        valor = self.request.query_params.get(self.parametro_estado)
        if valor:
            queryset = queryset.filter(**{self.parametro_estado: valor})
        return queryset


class BajaLogicaMixin:
    """`destroy()` con baja logica: marca `estado = inactivo` y responde 204.

    No borra filas en duro (protege las FK PROTECT y la trazabilidad).
    """

    def destroy(self, request, *args, **kwargs):
        instancia = self.get_object()
        instancia.estado = instancia.INACTIVO
        instancia.save(update_fields=["estado"])
        return Response(status=204)


def entero_o_none(valor):
    """Convierte un parametro de consulta a entero, o None si no lo es.

    Los filtros por clave foranea (`?cliente=3`) llegan como texto desde la
    URL. Pasarlos directo al ORM con un valor no numerico levanta ValueError y
    la peticion termina en un 500. Aca se descarta el filtro invalido en vez de
    reventar: la consulta responde 200 sin aplicarlo.
    """
    if valor in (None, ""):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def fecha_o_none(valor):
    """Convierte un parametro de consulta a fecha ISO, o None si no lo es.

    Mismo motivo que `entero_o_none`: en PostgreSQL un `?desde=hola` termina en
    un error de base de datos. Se valida antes de tocar el ORM.
    """
    if valor in (None, ""):
        return None
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        return None
