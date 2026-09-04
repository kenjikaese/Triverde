"""Vistas del modulo comercial (docs/13: C_Cotizaciones, C_Ventas, C_Cobros).

Un ViewSet por controlador. La logica de negocio (calculo del costo, tarifa
sugerida, saldo del cliente) vive en `services.py`; aca solo se orquesta y se
resuelven los permisos y la auditoria.

Permisos por rol (spec M8 SS4):
- cotizar, cuenta corriente, estado de pago y documentos tributarios -> Administrador
- registrar venta -> Administrador y Operador
- despacho y cobro -> Operador (y Administrador, que tiene acceso total)
"""
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from common.auditoria import registrar_auditoria
from common.permissions import IsAdministrador, IsOperadorOAdministrador
from common.trazas import traza
from mantenedores.models import Cliente

from .models import Cobro, Cotizacion, DocumentoTributario, Venta
from .serializers import (
    CobroSerializer,
    CotizacionSerializer,
    CuentaCorrienteSerializer,
    DespachoSerializer,
    DocumentoTributarioSerializer,
    VentaSerializer,
)
from .services import costo_por_km_vigente, cuenta_corriente, tarifa_sugerida


class RangoFechaMixin:
    """Filtra por `?desde=` y `?hasta=` sobre el campo `fecha`.

    Se resuelve a mano porque el proyecto no incluye django-filter (ver
    `common.views.FiltroEstadoMixin`, que hace lo mismo con el estado).
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        desde = self.request.query_params.get("desde")
        hasta = self.request.query_params.get("hasta")
        if desde:
            queryset = queryset.filter(fecha__gte=desde)
        if hasta:
            queryset = queryset.filter(fecha__lte=hasta)
        return queryset


class CotizacionViewSet(RangoFechaMixin, viewsets.ModelViewSet):
    """C_Cotizaciones: cotizar, exportar y consultar el historial.

    CU-55 (crear), CU-56 (exportar), CU-57 (historial con busqueda y filtros).
    """

    queryset = Cotizacion.objects.select_related("cliente").all()
    serializer_class = CotizacionSerializer
    permission_classes = [IsAdministrador]
    search_fields = ["cliente__razon_social", "servicio"]
    ordering_fields = ["fecha", "costo_estimado"]
    ordering = ["-fecha", "-id"]

    def get_queryset(self):
        queryset = super().get_queryset()
        cliente = self.request.query_params.get("cliente")
        if cliente:
            queryset = queryset.filter(cliente_id=cliente)
        return queryset

    def create(self, request, *args, **kwargs):
        respuesta = super().create(request, *args, **kwargs)
        # CU-55, Excepcion 3: sin costo por km configurado no se calcula, pero
        # la cotizacion queda registrada con el aviso de que falta el parametro.
        if respuesta.data.get("costo_estimado") is None:
            respuesta.data["advertencia"] = (
                "No hay un costo por kilometro configurado; la cotizacion se "
                "guardo sin costo calculado."
            )
        registrar_auditoria(
            request.user,
            "Generacion de cotizacion",
            "Cotizacion",
            respuesta.data.get("id"),
            f"Cliente {respuesta.data.get('cliente')}, "
            f"{respuesta.data.get('distancia_km')} km",
        )
        return respuesta

    @action(detail=True, methods=["get"])
    def exportar(self, request, pk=None):
        """CU-56: arma el documento descargable de la cotizacion.

        Excepcion 1: si el cliente no tiene datos de contacto completos, se
        senalan los faltantes y no se arma el documento.
        """
        cotizacion = self.get_object()
        cliente = cotizacion.cliente
        faltantes = [
            etiqueta
            for campo, etiqueta in (
                ("rut", "RUT"),
                ("nombre_contacto", "nombre de contacto"),
                ("telefono", "telefono"),
                ("email", "email"),
                ("direccion", "direccion"),
            )
            if not getattr(cliente, campo)
        ]
        if faltantes:
            return Response(
                {
                    "detalle": "El cliente no tiene sus datos de contacto "
                    "completos; complete los datos antes de exportar.",
                    "faltantes": faltantes,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "cotizacion": cotizacion.pk,
                "fecha": cotizacion.fecha,
                "cliente": {
                    "razon_social": cliente.razon_social,
                    "rut": cliente.rut,
                    "nombre_contacto": cliente.nombre_contacto,
                    "telefono": cliente.telefono,
                    "email": cliente.email,
                    "direccion": cliente.direccion,
                },
                "servicio": cotizacion.servicio,
                "distancia_km": cotizacion.distancia_km,
                "costo_estimado": cotizacion.costo_estimado,
            }
        )

    @action(detail=False, methods=["get"], url_path="costo-km")
    def costo_km(self, request):
        """Costo por kilometro vigente, para que el cotizador lo muestre."""
        costo = costo_por_km_vigente()
        return Response({"costo_por_km": costo, "configurado": costo is not None})


class VentaViewSet(RangoFechaMixin, viewsets.ModelViewSet):
    """C_Ventas: registrar venta, consultar el periodo y despachar.

    CU-58 (registrar), CU-59 (consultar con total del periodo), CU-60 (despacho).
    """

    queryset = Venta.objects.select_related("cliente").prefetch_related(
        "detalles__producto", "despacho"
    )
    serializer_class = VentaSerializer
    permission_classes = [IsOperadorOAdministrador]
    search_fields = ["cliente__razon_social", "detalles__producto__nombre"]
    ordering_fields = ["fecha", "total", "estado"]
    ordering = ["-fecha", "-id"]

    def get_queryset(self):
        queryset = super().get_queryset()
        cliente = self.request.query_params.get("cliente")
        producto = self.request.query_params.get("producto")
        estado = self.request.query_params.get("estado")
        if cliente:
            queryset = queryset.filter(cliente_id=cliente)
        if producto:
            queryset = queryset.filter(detalles__producto_id=producto)
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset.distinct()

    def create(self, request, *args, **kwargs):
        respuesta = super().create(request, *args, **kwargs)
        traza(
            "CU-58",
            "venta.creada",
            venta=respuesta.data.get("id"),
            cliente=respuesta.data.get("cliente"),
            lineas=len(respuesta.data.get("detalles", [])),
            total=respuesta.data.get("total"),
            estado=respuesta.data.get("estado"),
        )
        registrar_auditoria(
            request.user,
            "Registro de venta",
            "Venta",
            respuesta.data.get("id"),
            f"Cliente {respuesta.data.get('cliente')}, "
            f"total {respuesta.data.get('total')}",
        )
        return respuesta

    def destroy(self, request, *args, **kwargs):
        return Response(
            {
                "detalle": "Las ventas no se borran fisicamente; conservan la "
                "trazabilidad de la cuenta corriente del cliente."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=False, methods=["get"])
    def totales(self, request):
        """CU-59: total vendido del periodo consultado (mismos filtros)."""
        queryset = self.filter_queryset(self.get_queryset())
        total = sum((venta.total for venta in queryset), 0)
        return Response({"cantidad": queryset.count(), "total": total})

    @action(detail=True, methods=["post"])
    def despachar(self, request, pk=None):
        """CU-60: crea el despacho y pasa la venta a "despachada".

        Excepcion 2: si la venta ya tiene despacho, no se duplica.
        """
        venta = self.get_object()
        if hasattr(venta, "despacho"):
            traza("CU-60", "despacho.duplicado_rechazado", venta=venta.pk)
            return Response(
                {"detalle": "Esa venta ya fue despachada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = DespachoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(venta=venta)
        estado_anterior = venta.estado
        venta.estado = Venta.DESPACHADA
        venta.save(update_fields=["estado"])
        traza(
            "CU-60",
            "despacho.creado",
            venta=venta.pk,
            receptor=serializer.data.get("receptor"),
        )
        traza(
            "CU-60",
            "venta.estado",
            venta=venta.pk,
            transicion=f"{estado_anterior}->{venta.estado}",
        )
        registrar_auditoria(
            request.user,
            "Registro de despacho",
            "Venta",
            venta.pk,
            f"Despacho a {serializer.data.get('receptor')}",
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CobroViewSet(RangoFechaMixin, viewsets.ModelViewSet):
    """C_Cobros: cobro de una recepcion o de una venta (CU-61)."""

    queryset = Cobro.objects.select_related("cliente", "venta", "recepcion").all()
    serializer_class = CobroSerializer
    permission_classes = [IsOperadorOAdministrador]
    search_fields = ["cliente__razon_social", "medio"]
    ordering_fields = ["fecha", "monto"]
    ordering = ["-fecha", "-id"]

    def get_queryset(self):
        queryset = super().get_queryset()
        cliente = self.request.query_params.get("cliente")
        if cliente:
            queryset = queryset.filter(cliente_id=cliente)
        return queryset

    def create(self, request, *args, **kwargs):
        # CU-61, Excepcion 3: la recepcion ya tiene cobro registrado.
        recepcion = request.data.get("recepcion")
        if recepcion and Cobro.objects.filter(recepcion_id=recepcion).exists():
            traza("CU-61", "cobro.duplicado_rechazado", recepcion=recepcion)
            return Response(
                {"detalle": "Esa recepcion ya fue cobrada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        respuesta = super().create(request, *args, **kwargs)
        traza(
            "CU-61",
            "cobro.creado",
            cobro=respuesta.data.get("id"),
            recepcion=respuesta.data.get("recepcion"),
            venta=respuesta.data.get("venta"),
            monto=respuesta.data.get("monto"),
        )
        registrar_auditoria(
            request.user,
            "Registro de cobro",
            "Cobro",
            respuesta.data.get("id"),
            f"Monto {respuesta.data.get('monto')}",
        )
        return respuesta

    @action(detail=False, methods=["get"], url_path="sugerencia")
    def sugerencia(self, request):
        """Monto sugerido por la tarifa del tramo, antes de crear el cobro.

        Excepcion 1 del CU-61: si no hay tarifa para el tramo, devuelve null y
        el operador ingresa el monto manualmente; no bloquea el cobro.
        """
        from recepcion.models import Recepcion

        recepcion_id = request.query_params.get("recepcion")
        if not recepcion_id:
            return Response(
                {"detalle": "Indique la recepcion a cobrar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recepcion = get_object_or_404(Recepcion, pk=recepcion_id)
        monto = tarifa_sugerida(recepcion)
        return Response(
            {
                "recepcion": recepcion.pk,
                "cliente": recepcion.cliente_id,
                "monto_sugerido": monto,
                "cobrada": Cobro.objects.filter(recepcion=recepcion).exists(),
            }
        )


class DocumentoTributarioViewSet(RangoFechaMixin, viewsets.ModelViewSet):
    """Documentos tributarios pendientes (CU-63): seguimiento, no emision."""

    queryset = DocumentoTributario.objects.select_related(
        "cliente", "venta", "cobro"
    ).all()
    serializer_class = DocumentoTributarioSerializer
    permission_classes = [IsAdministrador]
    search_fields = ["cliente__razon_social", "folio"]
    ordering_fields = ["fecha", "monto"]
    ordering = ["-fecha", "-id"]

    def create(self, request, *args, **kwargs):
        respuesta = super().create(request, *args, **kwargs)
        traza(
            "CU-63",
            "documento.registrado",
            documento=respuesta.data.get("id"),
            tipo=respuesta.data.get("tipo"),
            origen="venta" if respuesta.data.get("venta") else "cobro",
            estado=respuesta.data.get("estado"),
        )
        return respuesta


class CuentaCorrienteView(APIView):
    """CU-64: saldo y movimientos de un cliente. CU-62: su estado de pago.

    El saldo es calculado (ventas - cobros), no almacenado. El PATCH actualiza
    `Cliente.estado_pago`, que es el indicador manual complementario.
    """

    permission_classes = [IsAdministrador]

    def get(self, request, cliente_id):
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        datos = cuenta_corriente(
            cliente,
            desde=request.query_params.get("desde"),
            hasta=request.query_params.get("hasta"),
        )
        return Response(CuentaCorrienteSerializer(datos).data)

    def patch(self, request, cliente_id):
        """CU-62: registra el estado de pago del cliente."""
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        estado_pago = request.data.get("estado_pago")
        # Excepcion 2: guardar sin seleccionar un estado de pago.
        if not estado_pago:
            return Response(
                {"estado_pago": "Debe seleccionar un estado de pago."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        validos = [opcion for opcion, _ in Cliente.ESTADO_PAGO_CHOICES]
        if estado_pago not in validos:
            return Response(
                {"estado_pago": f"Valor no valido. Opciones: {', '.join(validos)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Excepcion 1: no hay cuenta corriente que conciliar.
        tiene_movimientos = (
            cliente.ventas.exists() or cliente.cobros.exists()
        )
        if not tiene_movimientos:
            return Response(
                {
                    "detalle": "El cliente no tiene ventas ni cobros asociados; "
                    "no hay cuenta corriente que conciliar."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        anterior = cliente.estado_pago
        cliente.estado_pago = estado_pago
        cliente.save(update_fields=["estado_pago"])
        traza(
            "CU-62",
            "estado_pago.actualizado",
            cliente=cliente.pk,
            transicion=f"{anterior}->{estado_pago}",
        )
        registrar_auditoria(
            request.user,
            "Cambio de estado de pago",
            "Cliente",
            cliente.pk,
            f"{anterior} -> {estado_pago}",
        )
        return Response({"cliente": cliente.pk, "estado_pago": cliente.estado_pago})
