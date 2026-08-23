"""Vistas del modulo de configuracion (C_Configuracion).

Parametros y tarifas: CRUD para administrador, lectura para operador.
El historial de cambios es solo lectura. Al cambiar un parametro se registra
el `HistorialCambioParametro` y la bitacora de auditoria.
"""
from rest_framework import viewsets
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import EsAdministradorOOperadorLectura, IsOperadorOAdministrador

from .models import HistorialCambioParametro, ParametroConversion, TarifaRecepcion
from .serializers import (
    HistorialCambioParametroSerializer,
    ParametroConversionSerializer,
    TarifaRecepcionSerializer,
)


class ParametroConversionViewSet(viewsets.ModelViewSet):
    """CRUD de parametros de conversion."""

    queryset = ParametroConversion.objects.all()
    serializer_class = ParametroConversionSerializer
    permission_classes = [EsAdministradorOOperadorLectura]
    search_fields = ["clave", "nombre", "unidad"]
    ordering_fields = ["clave", "nombre"]
    ordering = ["clave"]

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        instancia = self.get_object()
        valor_anterior = instancia.valor
        serializer = self.get_serializer(instancia, data=request.data, partial=parcial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if serializer.instance.valor != valor_anterior:
            HistorialCambioParametro.objects.create(
                parametro=instancia,
                usuario=request.user,
                valor_anterior=valor_anterior,
                valor_nuevo=instancia.valor,
            )
            registrar_auditoria(
                request.user,
                "Cambio de parametro",
                "ParametroConversion",
                instancia.pk,
                f"{instancia.clave}: {valor_anterior} -> {instancia.valor}",
            )
        return Response(serializer.data)


class TarifaRecepcionViewSet(viewsets.ModelViewSet):
    """CRUD de tarifas de recepcion."""

    queryset = TarifaRecepcion.objects.all()
    serializer_class = TarifaRecepcionSerializer
    permission_classes = [EsAdministradorOOperadorLectura]
    ordering_fields = ["tramo_min_m3", "monto"]
    ordering = ["tramo_min_m3"]


class HistorialCambioParametroViewSet(viewsets.ReadOnlyModelViewSet):
    """Historial de cambios de parametro: solo lectura."""

    queryset = HistorialCambioParametro.objects.select_related(
        "parametro", "usuario"
    ).all()
    serializer_class = HistorialCambioParametroSerializer
    permission_classes = [IsOperadorOAdministrador]
    search_fields = ["parametro__clave", "usuario__username"]
    ordering_fields = ["fecha_hora"]
    ordering = ["-fecha_hora"]
