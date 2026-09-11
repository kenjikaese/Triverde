"""Controladores del modulo 6: calculo de mezcla y bandeja de alertas.

La bandeja de alertas es transversal: lista y resuelve tanto las alertas de
mezcla (CU-47/49) como las de mantencion generadas por el modulo 11.
"""
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import IsOperadorOAdministrador
from inventario.models import Pila

from .models import Alerta
from .serializers import AlertaSerializer, MezclaObjetivoSerializer
from .services import calcular_mezcla, resolver_alerta


class MezclaObjetivoViewSet(viewsets.ViewSet):
    """Expone CU-45 en `/mezcla-objetivo/<pila>/`."""

    permission_classes = [IsOperadorOAdministrador]

    def retrieve(self, request, pk=None):
        pila = get_object_or_404(Pila, pk=pk)
        return Response(MezclaObjetivoSerializer(calcular_mezcla(pila)).data)


class AlertaViewSet(viewsets.ReadOnlyModelViewSet):
    """Consulta CU-47 y resolucion CU-49 para operadores y administradores."""

    queryset = Alerta.objects.select_related(
        "pila", "resuelta_por",
        "mantencion", "mantencion__maquinaria", "mantencion__vehiculo",
    )
    serializer_class = AlertaSerializer
    permission_classes = [IsOperadorOAdministrador]
    search_fields = ["mensaje", "categoria", "origen"]
    ordering_fields = ["fecha_generada", "faltante_m3", "estado"]

    def get_queryset(self):
        """Por defecto muestra solo alertas activas; permite filtrar el historial."""
        queryset = super().get_queryset()
        estado = self.request.query_params.get("estado", Alerta.ACTIVA)
        if estado:
            queryset = queryset.filter(estado=estado)
        origen = self.request.query_params.get("origen")
        nivel = self.request.query_params.get("nivel")
        pila = self.request.query_params.get("pila")
        categoria = self.request.query_params.get("categoria")
        if origen:
            queryset = queryset.filter(origen=origen)
        if nivel:
            queryset = queryset.filter(nivel=nivel)
        if pila:
            queryset = queryset.filter(pila_id=pila)
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        return queryset

    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        """Resuelve una alerta y deja la accion en la bitacora de auditoria."""
        alerta = self.get_object()
        if alerta.estado != Alerta.RESUELTA:
            resolver_alerta(alerta, request.user)
            registrar_auditoria(request.user, "Resolucion de alerta", "Alerta", alerta.pk)
        return Response(self.get_serializer(alerta).data)
