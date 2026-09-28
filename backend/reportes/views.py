"""Controlador C_Reportes: reportes por periodo (CU-73 a CU-76) y panel de control (CU-72, CU-77)."""

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import IsAdministrador
from common.trazas import traza

from .models import PanelControl, Reporte
from .serializers import (
    GenerarReporteSerializer,
    PanelControlSerializer,
    PreferenciasPanelSerializer,
    ReporteSerializer,
)
from . import services
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
        traza(
            CU_POR_TIPO[reporte.tipo], "reporte.generado", reporte=reporte.pk,
            desde=reporte.periodo_inicio, hasta=reporte.periodo_fin,
        )
        return Response(ReporteSerializer(reporte).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def exportar(self, request, pk=None):
        """CU-76: `?formato=pdf|excel|csv` exporta en otro formato sin recalcular."""
        formato = request.query_params.get("formato") or None
        if formato and formato not in dict(Reporte.FORMATO_CHOICES):
            return Response(
                {"formato": "Formato no valido. Usa pdf, excel o csv."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reporte = self.get_object()
        respuesta = exportar_reporte(reporte, formato)
        traza("CU-76", "reporte.exportado", reporte=reporte.pk, formato=formato or reporte.formato)
        return respuesta


CU_POR_TIPO = {
    Reporte.RECEPCIONES: "CU-73",
    Reporte.PRODUCCION: "CU-74",
    Reporte.VENTAS_COBROS: "CU-75",
}


class PanelControlViewSet(viewsets.ViewSet):
    """Panel de control (CU-72) y su personalizacion (CU-77), parte de C_Reportes."""

    permission_classes = [IsAdministrador]

    def list(self, request):
        panel = services.armar_panel(request.user)
        traza("CU-72", "panel.armado", usuario=request.user.pk, indicadores=panel["indicadores_visibles"])
        return Response(panel)

    def _preferencias(self, request, panel, cambio=None):
        datos = {
            "indicadores_visibles": services.indicadores_activos(request.user),
            "configuracion": panel.configuracion if panel else {},
            "actualizado": PanelControlSerializer(panel).data["actualizado"] if panel else None,
            "disponibles": services.indicadores_disponibles(),
        }
        if cambio is not None:
            datos["cambio"] = cambio
        return Response(datos)

    @action(detail=False, methods=["get", "post"], url_path="preferencias")
    def preferencias(self, request):
        if request.method == "GET":
            return self._preferencias(request, PanelControl.objects.filter(usuario=request.user).first())

        entrada = PreferenciasPanelSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            panel, hubo_cambio = services.guardar_preferencias(
                usuario=request.user,
                indicadores_visibles=entrada.validated_data["indicadores_visibles"],
                configuracion=entrada.validated_data.get("configuracion"),
            )
        except services.SinIndicadores as exc:
            traza("CU-77", "panel.preferencias_rechazadas", usuario=request.user.pk)
            return Response({"indicadores_visibles": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        if hubo_cambio:
            registrar_auditoria(
                request.user, "Preferencias de panel", "PanelControl", panel.pk,
                f"indicadores_visibles: {panel.indicadores_visibles}",
            )
            traza("CU-77", "panel.preferencias_guardadas", panel=panel.pk, indicadores=panel.indicadores_visibles)
        else:
            traza("CU-77", "panel.preferencias_sin_cambios", panel=panel.pk)
        return self._preferencias(request, panel, cambio=hubo_cambio)
