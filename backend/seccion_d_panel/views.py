from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import EsAdministrador

from . import services
from .models import PanelControl
from .serializers import PanelControlSerializer, PreferenciasPanelSerializer


class C_PanelControl(viewsets.ViewSet):
    permission_classes = [EsAdministrador]

    def list(self, request):
        panel = services.armar_panel(request.user)
        return Response(panel)

    @action(detail=False, methods=["get", "post"], url_path="preferencias")
    def preferencias(self, request):
        if request.method == "GET":
            panel = PanelControl.objects.filter(usuario=request.user).first()
            if not panel:
                return Response(
                    {"indicadores_visibles": list(PanelControl.DEFECTO), "configuracion": {}}
                )
            return Response(PanelControlSerializer(panel).data)

        entrada = PreferenciasPanelSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            panel, hubo_cambio = services.guardar_preferencias(
                usuario=request.user,
                indicadores_visibles=entrada.validated_data["indicadores_visibles"],
                configuracion=entrada.validated_data.get("configuracion"),
            )
        except services.SinIndicadores as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if hubo_cambio:
            registrar_auditoria(
                request.user,
                accion="guardar_preferencias_panel",
                entidad="PanelControl",
                entidad_id=panel.pk,
                detalle={"indicadores_visibles": panel.indicadores_visibles},
            )
        return Response(PanelControlSerializer(panel).data)
