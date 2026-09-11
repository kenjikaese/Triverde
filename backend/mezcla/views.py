"""Controladores del modulo 6: calculo de mezcla y bandeja de alertas."""
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import IsOperadorOAdministrador
from inventario.models import Pila

from .models import Alerta
from .serializers import AlertaSerializer, MezclaObjetivoSerializer
from .services import calcular_mezcla


class MezclaObjetivoViewSet(viewsets.ViewSet):
    """Expone CU-45 en `/mezcla-objetivo/<pila>/`."""

    permission_classes = [IsOperadorOAdministrador]

    def retrieve(self, request, pk=None):
        pila = get_object_or_404(Pila, pk=pk)
        return Response(MezclaObjetivoSerializer(calcular_mezcla(pila)).data)


class AlertaViewSet(viewsets.ReadOnlyModelViewSet):
    """Consulta CU-47 y resolucion CU-49 para operadores y administradores."""
    queryset = Alerta.objects.select_related("pila", "resuelta_por").all()
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
        pila = self.request.query_params.get("pila")
        categoria = self.request.query_params.get("categoria")
        if pila:
            queryset = queryset.filter(pila_id=pila)
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        return queryset

    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        """Resuelve una alerta y deja la accion en la bitacora de auditoria."""
        alerta = self.get_object()
        if alerta.estado == Alerta.RESUELTA:
            return Response(AlertaSerializer(alerta).data)
        alerta.estado = Alerta.RESUELTA
        alerta.fecha_resuelta = timezone.now()
        alerta.resuelta_por = request.user
        alerta.save(update_fields=["estado", "fecha_resuelta", "resuelta_por"])
        registrar_auditoria(
            request.user,
            "resolver_alerta",
            "Alerta",
            alerta.pk,
            alerta.mensaje,
        )
        return Response(AlertaSerializer(alerta).data, status=status.HTTP_200_OK)
