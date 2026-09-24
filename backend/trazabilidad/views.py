from decimal import Decimal

from django.db.models import Sum
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.response import Response

from common.permissions import IsAdministrador
from common.trazas import traza

from .models import IndicadorAmbiental
from .serializers import IndicadorAmbientalSerializer
from .services import listar_pendientes


class IndicadorAmbientalViewSet(viewsets.ReadOnlyModelViewSet):
    """C_IndicadorAmbiental - acumulado, desglose y filtro de CU-71."""

    queryset = IndicadorAmbiental.objects.select_related(
        "recepcion__cliente", "pila"
    ).all()
    serializer_class = IndicadorAmbientalSerializer
    permission_classes = [IsAdministrador]
    http_method_names = ["get", "head", "options"]

    def _periodo(self, request):
        desde_crudo = request.query_params.get("desde")
        hasta_crudo = request.query_params.get("hasta")
        desde = parse_date(desde_crudo) if desde_crudo else None
        hasta = parse_date(hasta_crudo) if hasta_crudo else None
        if desde_crudo and desde is None:
            return None, None, "'desde' debe tener formato AAAA-MM-DD."
        if hasta_crudo and hasta is None:
            return None, None, "'hasta' debe tener formato AAAA-MM-DD."
        if desde and hasta and hasta < desde:
            return None, None, "La fecha hasta no puede ser anterior a desde."
        return desde, hasta, None

    def list(self, request, *args, **kwargs):
        desde, hasta, error = self._periodo(request)
        if error:
            return Response({"detalle": error}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset()
        if desde:
            queryset = queryset.filter(fecha__gte=desde)
        if hasta:
            queryset = queryset.filter(fecha__lte=hasta)

        cero = Decimal("0.00")
        total = queryset.aggregate(valor=Sum("co2_evitado_kg"))["valor"] or cero
        recepciones = queryset.filter(origen=IndicadorAmbiental.RECEPCION)
        pilas = queryset.filter(origen=IndicadorAmbiental.PILA)
        total_recepciones = (
            recepciones.aggregate(valor=Sum("co2_evitado_kg"))["valor"] or cero
        )
        total_pilas = pilas.aggregate(valor=Sum("co2_evitado_kg"))["valor"] or cero
        pendientes = listar_pendientes()
        traza(
            "CU-71",
            "indicador.consultado",
            desde=desde or "historico",
            hasta=hasta or "historico",
            total_kg=total,
        )
        return Response(
            {
                "periodo": {
                    "desde": desde.isoformat() if desde else None,
                    "hasta": hasta.isoformat() if hasta else None,
                },
                "total_co2_evitado_kg": f"{total:.2f}",
                "recepciones_co2_evitado_kg": f"{total_recepciones:.2f}",
                "pilas_co2_evitado_kg": f"{total_pilas:.2f}",
                "cantidad_recepciones": recepciones.count(),
                "cantidad_pilas": pilas.count(),
                "resultados": self.get_serializer(queryset, many=True).data,
                "pendientes": [
                    {
                        "origen": pendiente.origen,
                        "objeto_id": pendiente.objeto_id,
                        "referencia": pendiente.referencia,
                        "motivo": pendiente.motivo,
                    }
                    for pendiente in pendientes
                ],
            }
        )

