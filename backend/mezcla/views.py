from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import IsOperadorOAdministrador

from .models import Alerta
from .serializers import AlertaSerializer
from .services import resolver_alerta


class AlertaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Alerta.objects.select_related(
        "mantencion", "mantencion__maquinaria", "mantencion__vehiculo"
    )
    serializer_class = AlertaSerializer
    permission_classes = [IsOperadorOAdministrador]

    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self.request.query_params.get("estado")
        origen = self.request.query_params.get("origen")
        nivel = self.request.query_params.get("nivel")
        if estado:
            queryset = queryset.filter(estado=estado)
        if origen:
            queryset = queryset.filter(origen=origen)
        if nivel:
            queryset = queryset.filter(nivel=nivel)
        return queryset

    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        alerta = self.get_object()
        if alerta.estado != Alerta.RESUELTA:
            resolver_alerta(alerta, request.user)
            registrar_auditoria(request.user, "Resolucion de alerta", "Alerta", alerta.pk)
        return Response(self.get_serializer(alerta).data)
