"""Controlador C_Reportes."""

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import IsAdministrador

from .models import Reporte
from .serializers import GenerarReporteSerializer, ReporteSerializer
from .services import exportar_reporte, generar_reporte


class ReporteViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Genera, consulta y exporta reportes para administradores."""
    queryset = Reporte.objects.select_related("usuario").all()
    serializer_class = ReporteSerializer
    permission_classes = [IsAdministrador]

    def create(self, request, *args, **kwargs):
        entrada = GenerarReporteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        filtros = {clave: datos.get(clave) for clave in ("cliente", "material")}
        reporte = generar_reporte(
            datos["tipo"], datos["periodo_inicio"], datos["periodo_fin"],
            request.user, datos.get("formato", Reporte.PDF), filtros,
        )
        registrar_auditoria(
            request.user, "Generacion de reporte", "Reporte", reporte.pk,
            f"Tipo {reporte.tipo}, periodo {reporte.periodo_inicio} a {reporte.periodo_fin}",
        )
        return Response(ReporteSerializer(reporte).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def exportar(self, request, pk=None):
        return exportar_reporte(self.get_object())
