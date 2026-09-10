"""Vistas base reutilizables (mixin de filtro por estado)."""
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


class FiltroVigenteMixin:
    """Filtra por el query param `vigente` (p. ej. `?vigente=true`).
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        valor = self.request.query_params.get("vigente")
        if valor is not None:
            queryset = queryset.filter(vigente=valor.lower() in ("1", "true", "si"))
        return queryset


class BajaLogicaVigenteMixin:
    """`destroy()` con baja logica para modelos con campo `vigente`.
    """

    def destroy(self, request, *args, **kwargs):
        instancia = self.get_object()
        if instancia.vigente:
            instancia.vigente = False
            instancia.save(update_fields=["vigente"])
            self.auditar_baja(instancia)
        return Response(status=204)

    def auditar_baja(self, instancia):
        pass
