"""Vistas del modulo de configuracion (C_Configuracion).

Parametros y tarifas: CRUD para administrador, lectura para operador.
El historial de cambios es solo lectura. Al cambiar un parametro se registra
el `HistorialCambioParametro` y la bitacora de auditoria.

Recetas de mezcla: CRUD para administrador, lectura para operador. Costo de
transporte y costos operativos: exclusivos del administrador (M02 Incremento 2).
"""
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import (
    EsAdministradorOOperadorLectura,
    IsAdministrador,
    IsOperadorOAdministrador,
)
from common.views import BajaLogicaVigenteMixin, FiltroVigenteMixin

from .models import (
    CostoOperativo,
    CostoTransporte,
    HistorialCambioParametro,
    ParametroConversion,
    RecetaMezcla,
    TarifaRecepcion,
)
from .serializers import (
    CostoOperativoSerializer,
    CostoTransporteSerializer,
    HistorialCambioParametroSerializer,
    ParametroConversionSerializer,
    RecetaMezclaSerializer,
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
    """Historial de cambios de parametro: solo lectura, filtrable por
    parametro (id o clave) y rango de fechas (`desde`/`hasta`)."""

    serializer_class = HistorialCambioParametroSerializer
    permission_classes = [IsOperadorOAdministrador]
    search_fields = ["parametro__clave", "usuario__username"]
    ordering_fields = ["fecha_hora"]
    ordering = ["-fecha_hora"]

    def get_queryset(self):
        qs = HistorialCambioParametro.objects.select_related("parametro", "usuario").order_by("-fecha_hora")
        params = self.request.query_params
        parametro = params.get("parametro")
        desde = parse_date(params.get("desde") or "")
        hasta = parse_date(params.get("hasta") or "")
        if parametro:
            qs = qs.filter(parametro_id=parametro) if parametro.isdigit() else qs.filter(parametro__clave=parametro)
        if desde:
            qs = qs.filter(fecha_hora__date__gte=desde)
        if hasta:
            qs = qs.filter(fecha_hora__date__lte=hasta)
        return qs


class RecetaMezclaViewSet(FiltroVigenteMixin, BajaLogicaVigenteMixin, viewsets.ModelViewSet):
    """CRUD de recetas de mezcla seca/verde."""

    queryset = RecetaMezcla.objects.all()
    serializer_class = RecetaMezclaSerializer
    permission_classes = [EsAdministradorOOperadorLectura]

    def perform_create(self, serializer):
        receta = serializer.save(vigente=True)
        registrar_auditoria(
            self.request.user, "crear_receta", "RecetaMezcla", receta.pk,
            detalle=f"{receta.nombre} {receta.proporcion}",
        )

    def perform_update(self, serializer):
        anterior = serializer.instance.proporcion
        receta = serializer.save()
        if anterior != receta.proporcion:
            registrar_auditoria(
                self.request.user, "editar_receta", "RecetaMezcla", receta.pk,
                detalle=f"{receta.nombre} {anterior} -> {receta.proporcion}",
            )

    def auditar_baja(self, instancia):
        registrar_auditoria(self.request.user, "baja_receta", "RecetaMezcla", instancia.pk)


class CostoTransporteViewSet(viewsets.GenericViewSet):
    """Costo de transporte por km: valor vigente + historico versionado."""

    queryset = CostoTransporte.objects.all()
    serializer_class = CostoTransporteSerializer
    permission_classes = [IsAdministrador]

    def list(self, request):
        vigente = CostoTransporte.objects.vigente()
        if vigente is None:
            return Response({"detail": "No hay costo por km configurado"}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(vigente).data)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instancia, anterior, creado = CostoTransporte.actualizar(serializer.validated_data["costo_por_km"])

        if creado:
            registrar_auditoria(
                request.user, "cambiar_costo_km", "CostoTransporte", instancia.pk,
                detalle=f"{anterior} -> {instancia.costo_por_km}",
            )
        codigo = status.HTTP_201_CREATED if creado else status.HTTP_200_OK
        return Response(self.get_serializer(instancia).data, status=codigo)

    @action(detail=False, methods=["get"])
    def historico(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)


class CostoOperativoViewSet(FiltroVigenteMixin, BajaLogicaVigenteMixin, viewsets.ModelViewSet):
    """CRUD de costos operativos (combustible, mano de obra, etc.)."""

    queryset = CostoOperativo.objects.all()
    serializer_class = CostoOperativoSerializer
    permission_classes = [IsAdministrador]

    def perform_create(self, serializer):
        costo = serializer.save(vigente=True)
        registrar_auditoria(
            self.request.user, "crear_costo_operativo", "CostoOperativo", costo.pk,
            detalle=f"{costo.concepto} {costo.monto}/{costo.unidad}",
        )

    def perform_update(self, serializer):
        anterior = serializer.instance.monto
        costo = serializer.save()
        if anterior != costo.monto:
            registrar_auditoria(
                self.request.user, "editar_costo_operativo", "CostoOperativo", costo.pk,
                detalle=f"{costo.concepto}: {anterior} -> {costo.monto}",
            )

    def auditar_baja(self, instancia):
        registrar_auditoria(self.request.user, "baja_costo_operativo", "CostoOperativo", instancia.pk)
