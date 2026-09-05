"""Vistas del modulo 5: C_Inventario, C_Pilas y C_ProcesosPila (docs/13).

- `C_Inventario` (CU-34): consulta del saldo por material y etapa. Solo lectura;
  el inventario se mueve por los procesos, nunca a mano.
- `C_Pilas` (CU-35, CU-36, CU-43): alta de la pila, su composicion inicial y su
  ficha de trazabilidad.
- `C_ProcesosPila` (CU-37 a CU-42): registro de los seis procesos. No admite
  editar ni borrar: un proceso es un hecho historico, como la recepcion.

Actores: Administrador y Operador. El transportista no tiene acceso al modulo.
"""
from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import IsOperadorOAdministrador
from mantenedores.models import Material

from .models import ComposicionPila, Inventario, Pila, ProcesoPila
from .serializers import (
    AgregarComposicionSerializer,
    ComposicionPilaSerializer,
    InventarioSerializer,
    PilaSerializer,
    PilaTrazabilidadSerializer,
    ProcesoPilaSerializer,
)
from . import services


class InventarioViewSet(viewsets.ReadOnlyModelViewSet):
    """C_Inventario (CU-34): existencias por material y etapa.

    Filtra por `?material=<id>` y `?etapa=<etapa>`. Las combinaciones sin
    movimiento aparecen en cero, no como error (CU-34 Excepcion 1).
    """

    queryset = Inventario.objects.select_related("material").all()
    serializer_class = InventarioSerializer
    permission_classes = [IsOperadorOAdministrador]
    search_fields = ["material__nombre", "etapa"]
    ordering_fields = ["etapa", "volumen_m3", "actualizado"]

    def get_queryset(self):
        queryset = super().get_queryset()
        material = self.request.query_params.get("material")
        etapa = self.request.query_params.get("etapa")
        if material:
            queryset = queryset.filter(material_id=material)
        if etapa:
            queryset = queryset.filter(etapa=etapa)
        return queryset

    def list(self, request, *args, **kwargs):
        """Devuelve la grilla completa material x etapa.

        CU-34 Excepcion 1: las combinaciones sin ningun movimiento se muestran
        en cero, no se omiten. Solo existen como fila en la base las que ya se
        movieron, asi que aqui se completan las que faltan. Con `?search=` se
        devuelve el listado tal cual, sin completar.
        """
        queryset = self.filter_queryset(self.get_queryset())
        if request.query_params.get("search"):
            return Response(self.get_serializer(queryset, many=True).data)

        filas = {(fila.material_id, fila.etapa): fila for fila in queryset}
        materiales = Material.objects.filter(estado=Material.ACTIVO)
        material = request.query_params.get("material")
        if material:
            materiales = materiales.filter(pk=material)
        etapa_pedida = request.query_params.get("etapa")
        etapas = [
            valor for valor, _ in Inventario.ETAPA_CHOICES
            if not etapa_pedida or valor == etapa_pedida
        ]

        grilla = []
        for material_actual in materiales.order_by("nombre"):
            for etapa in etapas:
                fila = filas.get((material_actual.pk, etapa))
                if fila is not None:
                    grilla.append(self.get_serializer(fila).data)
                else:
                    grilla.append(
                        {
                            "id": None,
                            "material": material_actual.pk,
                            "material_nombre": material_actual.nombre,
                            "material_categoria": material_actual.categoria,
                            "etapa": etapa,
                            "volumen_m3": "0.00",
                            "actualizado": None,
                        }
                    )
        return Response(grilla)


class PilaViewSet(viewsets.ModelViewSet):
    """C_Pilas (CU-35, CU-36, CU-43).

    Filtra por `?estado=` (en formacion, en proceso, en reposo, cerrada).
    """

    queryset = Pila.objects.prefetch_related(
        "composiciones__material", "procesos"
    ).all()
    serializer_class = PilaSerializer
    permission_classes = [IsOperadorOAdministrador]
    search_fields = ["codigo", "observaciones"]
    ordering_fields = ["codigo", "fecha_inicio", "estado"]

    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self.request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset

    def destroy(self, request, *args, **kwargs):
        """Las pilas no se borran: son la trazabilidad interna del lote (CU-43)."""
        return Response(
            {
                "detalle": "Las pilas no se borran; su ciclo termina con el "
                "estado 'cerrada' tras el ensacado."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=False, methods=["get"], url_path="codigo-sugerido")
    def codigo_sugerido(self, request):
        """Correlativo libre para proponer en el formulario de alta (CU-35)."""
        return Response({"codigo": Pila.generar_codigo()})

    @action(detail=True, methods=["post"])
    def composicion(self, request, pk=None):
        """CU-36: incorpora un material a la pila en formacion.

        Si el material ya estaba declarado, suma la cantidad al registro
        existente en vez de duplicarlo (CU-36 Excepcion 2).
        """
        pila = self.get_object()
        if pila.estado != Pila.EN_FORMACION:
            return Response(
                {
                    "detalle": f"La pila {pila.codigo} esta '{pila.estado}'; solo "
                    "se compone una pila en formacion."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = AgregarComposicionSerializer(
            data=request.data, context={"pila": pila}
        )
        serializer.is_valid(raise_exception=True)
        material = serializer.validated_data["material"]
        volumen = serializer.validated_data["volumen_m3"]
        with transaction.atomic():
            composicion, creada = ComposicionPila.objects.get_or_create(
                pila=pila, material=material, defaults={"volumen_m3": volumen}
            )
            if not creada:
                composicion.volumen_m3 = composicion.volumen_m3 + volumen
                composicion.save(update_fields=["volumen_m3"])
        return Response(
            ComposicionPilaSerializer(composicion).data,
            status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="confirmar-composicion")
    def confirmar_composicion(self, request, pk=None):
        """CU-36: cierra la composicion, mueve el inventario y arranca la pila.

        Descuenta cada material de su etapa de origen y lo traslada a 'pila en
        proceso'; la pila pasa de 'en formacion' a 'en proceso'.
        """
        pila = self.get_object()
        if pila.estado != Pila.EN_FORMACION:
            return Response(
                {"detalle": f"La pila {pila.codigo} ya esta '{pila.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        composiciones = list(pila.composiciones.select_related("material"))
        if not composiciones:
            # CU-36 Excepcion 3.
            return Response(
                {"detalle": "La pila necesita al menos un material para confirmarse."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            for composicion in composiciones:
                services.aplicar_movimiento(
                    composicion.material,
                    services.etapa_origen_para_pila(composicion.material),
                    Inventario.PILA_EN_PROCESO,
                    composicion.volumen_m3,
                )
            pila.estado = Pila.EN_PROCESO
            pila.save(update_fields=["estado"])
            registrar_auditoria(
                request.user,
                "Confirmacion de composicion de pila",
                "Pila",
                pila.pk,
                f"Pila {pila.codigo} confirmada con {len(composiciones)} material(es); "
                f"{pila.volumen_composicion()} m3 trasladados a 'pila en proceso'.",
            )
        return Response(PilaTrazabilidadSerializer(pila).data)

    @action(detail=True, methods=["get"])
    def trazabilidad(self, request, pk=None):
        """CU-43: ficha completa de la pila (composicion + linea de tiempo)."""
        pila = self.get_object()
        return Response(PilaTrazabilidadSerializer(pila).data)


class ProcesoPilaViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """C_ProcesosPila (CU-37 a CU-42): triturado, volteo, riego, harneado,
    reposo y ensacado.

    Solo crear y consultar: un proceso registrado no se edita ni se borra,
    porque el inventario ya se movio con el. Filtra por `?pila=` y `?tipo=`.
    """

    queryset = ProcesoPila.objects.select_related(
        "pila", "material", "operador"
    ).all()
    serializer_class = ProcesoPilaSerializer
    permission_classes = [IsOperadorOAdministrador]
    search_fields = ["tipo", "pila__codigo", "material__nombre"]
    ordering_fields = ["fecha", "tipo"]

    def get_queryset(self):
        queryset = super().get_queryset()
        pila = self.request.query_params.get("pila")
        tipo = self.request.query_params.get("tipo")
        if pila:
            queryset = queryset.filter(pila_id=pila)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        return queryset

    def perform_create(self, serializer):
        """Deja al usuario como operador del proceso y audita lo que mueve stock."""
        serializer.save(operador=self.request.user)
        proceso = serializer.instance
        if proceso.tipo in (
            ProcesoPila.TRITURADO,
            ProcesoPila.REPOSO,
            ProcesoPila.ENSACADO,
        ):
            registrar_auditoria(
                self.request.user,
                f"Registro de {proceso.tipo}",
                "ProcesoPila",
                proceso.pk,
                proceso.advertencia
                or f"{proceso.tipo} registrado; el inventario fue actualizado.",
            )
