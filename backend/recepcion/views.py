"""Vistas del modulo de recepcion: CRUD del agregado y sincronizacion (CU-33).

`C_Recepcion` expone la Recepcion con sus partes anidadas. `C_Sincronizacion`
aplica lotes de operaciones capturadas offline de forma idempotente: la clave
es el `id_local` (UUID generado en el dispositivo); reenviar el mismo lote dos
veces da el mismo resultado que enviarlo una vez.
"""
import uuid
from datetime import datetime
from decimal import InvalidOperation

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from common.auditoria import registrar_auditoria
from common.permissions import EsOperadorOAdministradorOTransportista, IsOperadorOAdministrador
from common.views import FiltroEstadoMixin

from acceso.models import Rol
from mantenedores.models import Transportista

from .models import Recepcion
from .serializers import MultaSerializer, RecepcionSerializer


class RecepcionViewSet(FiltroEstadoMixin, viewsets.ModelViewSet):
    """C_Recepcion: recepciones (agregado con detalles, fotos y multas).

    Un transportista solo ve las recepciones cuyo `transportista.usuario` es
    el mismo (CU-28); al crear, se le fuerza su propio transportista.
    El DELETE fisico no esta permitido (no hay baja logica definida para
    recepciones en el modelo); el rechazo se modela con `estado = rechazada`.
    """

    queryset = Recepcion.objects.select_related(
        "cliente", "transportista", "vehiculo", "operador"
    ).prefetch_related("detalles__material", "fotos", "multas")
    serializer_class = RecepcionSerializer
    permission_classes = [EsOperadorOAdministradorOTransportista]
    search_fields = [
        "conductor",
        "cliente__razon_social",
        "transportista__nombre",
        "vehiculo__patente",
        "observaciones",
    ]
    ordering_fields = ["fecha", "hora", "estado", "estado_sincronizacion"]
    ordering = ["-fecha", "-hora"]

    def get_queryset(self):
        queryset = super().get_queryset()
        usuario = self.request.user
        if usuario.rol.nombre == Rol.TRANSPORTISTA:
            queryset = queryset.filter(transportista__usuario=usuario)
        return queryset

    def perform_create(self, serializer):
        usuario = self.request.user
        if usuario.rol.nombre == Rol.TRANSPORTISTA:
            try:
                transportista = usuario.transportista
            except Transportista.DoesNotExist:
                raise serializers.ValidationError(
                    {"transportista": "La cuenta no tiene un transportista asociado."}
                )
            serializer.save(transportista=transportista)
        elif not serializer.validated_data.get("operador"):
            serializer.save(operador=usuario)
        else:
            serializer.save()

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        instancia = self.get_object()
        estado_anterior = instancia.estado
        serializer = self.get_serializer(instancia, data=request.data, partial=parcial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if "multas" in request.data:
            registrar_auditoria(
                request.user,
                "Aplicacion de multa",
                "Recepcion",
                instancia.pk,
                "Se modificaron las multas de la recepcion.",
            )
        if (
            instancia.estado == Recepcion.RECHAZADA
            and estado_anterior != Recepcion.RECHAZADA
        ):
            registrar_auditoria(
                request.user,
                "Rechazo de recepcion",
                "Recepcion",
                instancia.pk,
                instancia.motivo_rechazo or "",
            )
        return Response(serializer.data)

    def _exigir_en_inspeccion(self, recepcion):
        """Solo se inspecciona una carga que todavia no tiene resultado."""
        if recepcion.estado in (Recepcion.RECIBIDA, Recepcion.RECHAZADA):
            raise serializers.ValidationError(
                {"detalle": f"La recepcion #{recepcion.pk} ya esta '{recepcion.estado}'."}
            )

    @action(detail=True, methods=["post"], permission_classes=[IsOperadorOAdministrador])
    def aceptar(self, request, pk=None):
        """Cierra la inspeccion con la carga aceptada: queda 'recibida'."""
        recepcion = self.get_object()
        self._exigir_en_inspeccion(recepcion)
        recepcion.estado = Recepcion.RECIBIDA
        recepcion.save(update_fields=["estado"])
        registrar_auditoria(
            request.user,
            "Aceptacion de recepcion",
            "Recepcion",
            recepcion.pk,
            "La carga paso la inspeccion y quedo recibida.",
        )
        return Response(self.get_serializer(recepcion).data)

    @action(detail=True, methods=["post"], permission_classes=[IsOperadorOAdministrador])
    def multa(self, request, pk=None):
        """CU-30: registra una multa y mantiene la recepcion en inspeccion."""
        recepcion = self.get_object()
        self._exigir_en_inspeccion(recepcion)
        serializer = MultaSerializer(
            data={
                "cliente": recepcion.cliente_id,
                "motivo": request.data.get("motivo"),
                "monto": request.data.get("monto"),
                "fecha": request.data.get("fecha") or timezone.localdate(),
            }
        )
        serializer.is_valid(raise_exception=True)
        multa = serializer.save(recepcion=recepcion)
        registrar_auditoria(
            request.user,
            "Aplicacion de multa",
            "Recepcion",
            recepcion.pk,
            f"Multa de {multa.monto}: {multa.motivo}",
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsOperadorOAdministrador])
    def rechazar(self, request, pk=None):
        """CU-31: rechaza la carga con su motivo y la saca del inventario."""
        recepcion = self.get_object()
        self._exigir_en_inspeccion(recepcion)
        serializer = self.get_serializer(
            recepcion,
            data={
                "estado": Recepcion.RECHAZADA,
                "motivo_rechazo": request.data.get("motivo_rechazo"),
            },
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        registrar_auditoria(
            request.user,
            "Rechazo de recepcion",
            "Recepcion",
            recepcion.pk,
            recepcion.motivo_rechazo or "",
        )
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {
                "detalle": "Las recepciones no se borran fisicamente; use "
                "estado 'rechazada' con su motivo."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


def _aplanar_errores(detalle, prefijo=""):
    """Convierte el detalle de error de DRF en una lista de mensajes planos."""
    mensajes = []
    if isinstance(detalle, dict):
        for clave, valor in detalle.items():
            mensajes.extend(_aplanar_errores(valor, f"{prefijo}{clave}: "))
    elif isinstance(detalle, (list, tuple)):
        for item in detalle:
            mensajes.extend(_aplanar_errores(item, prefijo))
    else:
        mensajes.append(f"{prefijo}{detalle}")
    return mensajes


class SincronizacionView(APIView):
    """Endpoint de sincronizacion (CU-33).

    POST /api/v1/sincronizacion/ con la cola local del dispositivo. Aplica las
    operaciones en orden de `capturado_en`, cada una en su propia transaccion,
    y reporta el resultado por operacion.
    """

    permission_classes = [IsOperadorOAdministrador]

    def post(self, request, *args, **kwargs):
        operaciones = request.data.get("operaciones")
        if not isinstance(operaciones, list):
            return Response(
                {"detalle": "El cuerpo debe incluir la lista 'operaciones'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ordenadas = self._ordenar_operaciones(operaciones)
        resultados = [self._procesar(op) for op in ordenadas]
        return Response({"resultados": resultados})

    def _ordenar_operaciones(self, operaciones):
        """Ordena por `capturado_en` si todas lo traen; si no, deja el orden
        del arreglo (que se asume ya ordenado). No reordena por otra cosa."""
        parseadas = []
        for indice, op in enumerate(operaciones):
            capturado = op.get("capturado_en") if isinstance(op, dict) else None
            instante = None
            if capturado:
                try:
                    instante = datetime.fromisoformat(
                        str(capturado).replace("Z", "+00:00")
                    )
                except ValueError:
                    instante = None
            if instante is not None:
                if instante.tzinfo is None:
                    instante = instante.replace(tzinfo=timezone.utc)
                instante = instante.astimezone(timezone.utc).replace(tzinfo=None)
            parseadas.append((instante, indice, op))
        if all(instante is not None for instante, _, _ in parseadas):
            parseadas.sort(key=lambda item: item[0])
        return [op for _, _, op in parseadas]

    def _procesar(self, operacion):
        """Procesa una operacion del lote y devuelve su resultado."""
        if not isinstance(operacion, dict):
            return {
                "id_local": None,
                "estado": "rechazada",
                "motivo": "La operacion debe ser un objeto JSON.",
            }
        id_local_crudo = operacion.get("id_local") or (
            operacion.get("datos") or {}
        ).get("id_local")
        try:
            id_local = uuid.UUID(str(id_local_crudo))
        except (TypeError, ValueError, AttributeError):
            return {
                "id_local": id_local_crudo,
                "estado": "rechazada",
                "motivo": "id_local ausente o no es un UUID valido.",
            }
        tipo = operacion.get("tipo")
        if tipo not in ("recepcion", "proceso_pila"):
            return {
                "id_local": str(id_local),
                "estado": "rechazada",
                "motivo": f"Tipo de operacion '{tipo}' no soportado.",
            }
        datos = operacion.get("datos") or {}
        if not isinstance(datos, dict):
            return {
                "id_local": str(id_local),
                "estado": "rechazada",
                "motivo": "'datos' debe ser un objeto JSON.",
            }
        try:
            with transaction.atomic():
                if tipo == "proceso_pila":
                    # Modulo 5: los procesos de pila (CU-37 a CU-42) tambien se
                    # capturan sin senal. La logica vive en su propia app; aqui
                    # solo se despacha por tipo. El import es local para no
                    # acoplar el modulo 4 con el 5 al cargar.
                    from inventario.sincronizacion import sincronizar_proceso_pila

                    return sincronizar_proceso_pila(id_local, datos, self.request)
                return self._sincronizar_recepcion(id_local, datos)
        except (serializers.ValidationError, ObjectDoesNotExist, IntegrityError,
                InvalidOperation, ValueError) as exc:
            if isinstance(exc, serializers.ValidationError):
                motivo = "; ".join(_aplanar_errores(exc.detail)) or str(exc)
            else:
                motivo = str(exc)
            return {
                "id_local": str(id_local),
                "estado": "rechazada",
                "motivo": motivo,
            }

    def _sincronizar_recepcion(self, id_local, datos):
        """Crea-si-no-existe por `id_local`; no duplica; marca conflictos."""
        existente = Recepcion.objects.filter(id_local=id_local).first()
        if existente is not None:
            if existente.estado_sincronizacion == Recepcion.SINCRONIZADA:
                return {
                    "id_local": str(id_local),
                    "estado": "sincronizada",
                    "id_servidor": existente.pk,
                }
            existente.estado_sincronizacion = Recepcion.EN_CONFLICTO
            existente.save(update_fields=["estado_sincronizacion"])
            return {
                "id_local": str(id_local),
                "estado": "en conflicto",
                "motivo": "El objeto ya existe en el servidor en un estado "
                "incompatible con la sincronizacion.",
            }
        datos_serializer = dict(datos)
        datos_serializer.setdefault("id_local", str(id_local))
        serializer = RecepcionSerializer(
            data=datos_serializer, context={"request": self.request}
        )
        serializer.is_valid(raise_exception=True)
        recepcion = serializer.save()
        self._marcar_sincronizada(recepcion)
        return {
            "id_local": str(id_local),
            "estado": "sincronizada",
            "id_servidor": recepcion.pk,
        }

    def _marcar_sincronizada(self, recepcion):
        """Marca la recepcion y todas sus partes como sincronizadas, para que la
        cabecera y sus objetos hijos queden consistentes tras el sync."""
        recepcion.estado_sincronizacion = Recepcion.SINCRONIZADA
        recepcion.save(update_fields=["estado_sincronizacion"])
        for relacion in ("detalles", "fotos", "multas"):
            getattr(recepcion, relacion).update(
                estado_sincronizacion=Recepcion.SINCRONIZADA
            )
