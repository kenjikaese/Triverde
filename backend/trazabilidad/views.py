from decimal import Decimal

from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import IsAdministrador
from common.trazas import traza
from common.views import entero_o_none
from mantenedores.models import Cliente
from recepcion.models import Recepcion

from .certificados import (
    CertificadoNoGenerable,
    ConsolidadoPrevio,
    generar_certificado_descarga,
    generar_consolidado,
)
from .models import CertificadoTrazabilidad, DeclaracionSinader, IndicadorAmbiental
from .serializers import (
    CertificadoTrazabilidadSerializer,
    DeclaracionSinaderSerializer,
    IndicadorAmbientalSerializer,
)
from .services import listar_pendientes
from .sinader import DeclaracionNoGenerable, generar_declaracion


def _leer_periodo(datos):
    """Valida `periodo_inicio` y `periodo_fin` (AAAA-MM-DD, inicio <= fin)."""
    inicio_crudo = datos.get("periodo_inicio")
    fin_crudo = datos.get("periodo_fin")
    if not inicio_crudo or not fin_crudo:
        return None, None, "Indique periodo_inicio y periodo_fin."
    inicio = parse_date(str(inicio_crudo))
    fin = parse_date(str(fin_crudo))
    if inicio is None or fin is None:
        return None, None, "El periodo debe tener formato AAAA-MM-DD."
    if fin < inicio:
        return None, None, "El fin del periodo no puede ser anterior al inicio."
    return inicio, fin, None


class CertificadoTrazabilidadViewSet(viewsets.ReadOnlyModelViewSet):
    """C_Trazabilidad (docs/13), certificados: emitir por descarga (CU-65), consolidado (CU-66),
    historial y exportacion. Solo Administrador (spec M9, Parte A)."""

    queryset = CertificadoTrazabilidad.objects.select_related("cliente", "recepcion")
    serializer_class = CertificadoTrazabilidadSerializer
    permission_classes = [IsAdministrador]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        cliente = entero_o_none(self.request.query_params.get("cliente"))
        tipo = self.request.query_params.get("tipo")
        if cliente:
            queryset = queryset.filter(cliente_id=cliente)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        return queryset

    @action(detail=False, methods=["post"], url_path="generar-descarga")
    def generar_descarga(self, request):
        """CU-65: certificado de una descarga recibida con peso calculado."""
        recepcion_id = entero_o_none(request.data.get("recepcion"))
        if not recepcion_id:
            return Response(
                {"detalle": "Indique la recepcion a certificar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recepcion = get_object_or_404(
            Recepcion.objects.select_related("cliente", "transportista", "vehiculo"),
            pk=recepcion_id,
        )
        try:
            certificado, creado = generar_certificado_descarga(recepcion)
        except CertificadoNoGenerable as exc:
            traza("CU-65", "certificado.rechazado", recepcion=recepcion.pk, motivo=exc.motivo)
            return Response(
                {"detalle": exc.motivo, **exc.datos}, status=status.HTTP_400_BAD_REQUEST
            )
        if creado:
            registrar_auditoria(
                request.user,
                "Generacion de certificado de trazabilidad",
                "CertificadoTrazabilidad",
                certificado.pk,
                f"{certificado.codigo} por descarga, recepcion {recepcion.pk}",
            )
        return Response(
            self.get_serializer(certificado).data,
            status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="generar-consolidado")
    def generar_consolidado(self, request):
        """CU-66: consolidado mensual del cliente. Con consolidado previo,
        exige `confirmar` y emite una nueva version conservando la anterior."""
        cliente_id = entero_o_none(request.data.get("cliente"))
        if not cliente_id:
            return Response(
                {"detalle": "Indique el cliente."}, status=status.HTTP_400_BAD_REQUEST
            )
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        inicio, fin, error = _leer_periodo(request.data)
        if error:
            return Response({"detalle": error}, status=status.HTTP_400_BAD_REQUEST)
        confirmar = str(request.data.get("confirmar", "")).lower() in ("true", "1", "si")
        try:
            certificado = generar_consolidado(cliente, inicio, fin, confirmar=confirmar)
        except ConsolidadoPrevio as exc:
            return Response(
                {
                    "detalle": "Ya existe un consolidado para este cliente y periodo. "
                    "Confirme para emitir una nueva version.",
                    "requiere_confirmacion": True,
                    "previo": self.get_serializer(exc.previo).data,
                },
                status=status.HTTP_409_CONFLICT,
            )
        except CertificadoNoGenerable as exc:
            traza("CU-66", "consolidado.rechazado", cliente=cliente.pk, motivo=exc.motivo)
            return Response(
                {"detalle": exc.motivo, **exc.datos}, status=status.HTTP_400_BAD_REQUEST
            )
        registrar_auditoria(
            request.user,
            "Generacion de certificado consolidado",
            "CertificadoTrazabilidad",
            certificado.pk,
            f"{certificado.codigo} version {certificado.contenido.get('version')} "
            f"para cliente {cliente.pk}, {inicio} a {fin}",
        )
        return Response(self.get_serializer(certificado).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def exportar(self, request, pk=None):
        """Documento descargable del certificado (mismo patron que CU-56)."""
        certificado = self.get_object()
        traza("CU-65", "certificado.exportado", codigo=certificado.codigo)
        return Response(certificado.contenido)


class DeclaracionSinaderViewSet(viewsets.ReadOnlyModelViewSet):
    """C_Trazabilidad (docs/13), SINADER: generar y descargar la declaracion del periodo (CU-67).
    Solo Administrador."""

    queryset = DeclaracionSinader.objects.select_related("usuario")
    serializer_class = DeclaracionSinaderSerializer
    permission_classes = [IsAdministrador]
    http_method_names = ["get", "post", "head", "options"]

    @action(detail=False, methods=["post"])
    def generar(self, request):
        inicio, fin, error = _leer_periodo(request.data)
        if error:
            return Response({"detalle": error}, status=status.HTTP_400_BAD_REQUEST)
        try:
            declaracion = generar_declaracion(inicio, fin, request.user)
        except DeclaracionNoGenerable as exc:
            traza("CU-67", "declaracion.rechazada", desde=inicio, hasta=fin, motivo=exc.motivo)
            return Response(
                {"detalle": exc.motivo, **exc.datos}, status=status.HTTP_400_BAD_REQUEST
            )
        registrar_auditoria(
            request.user,
            "Generacion de declaracion SINADER",
            "DeclaracionSinader",
            declaracion.pk,
            f"Periodo {inicio} a {fin}; {declaracion.contenido['totales']['clientes']} "
            f"clientes, {len(declaracion.contenido['excluidos'])} excluidos",
        )
        return Response(self.get_serializer(declaracion).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def descargar(self, request, pk=None):
        """Entrega la planilla XLSX para cargarla a mano en SINADER."""
        declaracion = self.get_object()
        traza("CU-67", "declaracion.descargada", declaracion=declaracion.pk)
        return FileResponse(
            declaracion.archivo.open("rb"),
            as_attachment=True,
            filename=declaracion.archivo.name.rsplit("/", 1)[-1],
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class IndicadorAmbientalViewSet(viewsets.ReadOnlyModelViewSet):
    """C_Ambiental (docs/13): acumulado, desglose y filtro de CU-71."""

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

