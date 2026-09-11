from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import IsAdministrador

from .models import Proyeccion
from .serializers import ProyeccionSerializer
from .services import ParametroFaltante, ProyeccionService


class ProyeccionViewSet(viewsets.ModelViewSet):
    """C_Proyecciones (Modulo 7). Solo Administrador: las proyecciones son gestion.

    - POST crea y calcula la proyeccion (CU-50/51/52) y la persiste.
    - GET  .../comparar/ contrasta lo proyectado con lo real del periodo (CU-53).
    - POST .../ajustar/  recalcula con supuestos ajustados sin tocar la config (CU-54).
    """

    queryset = Proyeccion.objects.select_related("material", "usuario").all()
    serializer_class = ProyeccionSerializer
    permission_classes = [IsAdministrador]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        try:
            supuestos, valor = ProyeccionService.calcular(
                datos["tipo"], datos.get("material"), datos.get("supuestos"),
            )
        except ParametroFaltante as exc:
            return Response(
                {"supuestos": f"Falta el parametro requerido: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        proyeccion = serializer.save(
            usuario=request.user, supuestos=supuestos, valor_proyectado=valor,
        )
        registrar_auditoria(
            request.user, "crear_proyeccion", "Proyeccion", proyeccion.pk,
            detalle=proyeccion.tipo,
        )
        return Response(
            self.get_serializer(proyeccion).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get"])
    def comparar(self, request, pk=None):
        proyeccion = self.get_object()
        try:
            return Response(ProyeccionService.comparar(proyeccion))
        except ParametroFaltante as exc:
            return Response(
                {"error": f"Falta el parametro: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def ajustar(self, request, pk=None):
        proyeccion = self.get_object()
        nuevos = request.data.get("supuestos", request.data)
        try:
            proyeccion = ProyeccionService.ajustar(proyeccion, nuevos)
        except ParametroFaltante as exc:
            return Response(
                {"supuestos": f"Falta el parametro requerido: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        registrar_auditoria(request.user, "ajustar_proyeccion", "Proyeccion", proyeccion.pk)
        return Response(self.get_serializer(proyeccion).data)
