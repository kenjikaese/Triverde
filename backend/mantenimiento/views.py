from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from acceso.models import Rol
from common.auditoria import registrar_auditoria
from common.permissions import EsAdministradorOOperadorLectura, IsOperadorOAdministrador
from common.views import FiltroEstadoMixin
from mantenedores.models import Vehiculo

from .models import Maquinaria, Mantencion, RegistroUso
from .serializers import MaquinariaSerializer, MantencionSerializer, RegistroUsoSerializer
from .services import revisar_alertas_mantenimiento


def _es_admin(request):
    return request.user.rol.nombre == Rol.ADMINISTRADOR


class MaquinariaViewSet(FiltroEstadoMixin, viewsets.ModelViewSet):
    queryset = Maquinaria.objects.all()
    serializer_class = MaquinariaSerializer
    permission_classes = [EsAdministradorOOperadorLectura]
    search_fields = ["nombre", "tipo"]
    ordering_fields = ["nombre", "tipo", "horometro", "estado_operativo", "estado"]

    def perform_create(self, serializer):
        obj = serializer.save(estado=Maquinaria.ACTIVO)
        registrar_auditoria(self.request.user, "Alta", "Maquinaria", obj.pk, obj.nombre)

    def perform_update(self, serializer):
        obj = serializer.save()
        registrar_auditoria(self.request.user, "Edicion", "Maquinaria", obj.pk, obj.nombre)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        pendiente = obj.mantencions.filter(estado=Mantencion.PROGRAMADA).exists()
        requiere_confirmacion = obj.estado_operativo == obj.EN_MANTENCION or pendiente
        if requiere_confirmacion and not request.data.get("confirmar_baja"):
            return Response(
                {"confirmar_baja": "El activo esta en mantencion o tiene una mantencion pendiente."},
                status=status.HTTP_409_CONFLICT,
            )
        obj.estado = obj.INACTIVO
        obj.save(update_fields=["estado"])
        registrar_auditoria(request.user, "Baja", "Maquinaria", obj.pk, obj.nombre)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="estado-flota")
    def estado_flota(self, request):
        if not _es_admin(request):
            return Response({"detail": "Solo el administrador puede ver la flota."}, status=403)
        revisar_alertas_mantenimiento()
        activos = []
        maquinarias = Maquinaria.objects.filter(estado=Maquinaria.ACTIVO)
        vehiculos = Vehiculo.objects.filter(estado=Vehiculo.ACTIVO, es_mantenible=True)
        for clase, coleccion in (("maquinaria", maquinarias), ("vehiculo", vehiculos)):
            for activo in coleccion:
                filtro = {clase: activo, "estado": Mantencion.PROGRAMADA}
                proxima = Mantencion.objects.filter(**filtro).order_by(
                    "fecha_programada", "umbral_horas"
                ).first()
                alerta = proxima.alertas.filter(estado="activa").first() if proxima else None
                activos.append({
                    "id": activo.pk,
                    "clase_activo": clase,
                    "codigo": f"MQ-{activo.pk:02d}" if clase == "maquinaria" else f"VH-{activo.pk:02d}",
                    "nombre": activo.nombre if clase == "maquinaria" else activo.patente,
                    "tipo": activo.tipo if clase == "maquinaria" else "Vehiculo",
                    "horometro": activo.horometro,
                    "estado_operativo": activo.estado_operativo,
                    "proxima_mantencion": MantencionSerializer(proxima).data if proxima else None,
                    "alerta": alerta.mensaje if alerta else None,
                    "nivel_alerta": alerta.nivel if alerta else None,
                })
        return Response(activos)


class RegistroUsoViewSet(viewsets.ModelViewSet):
    queryset = RegistroUso.objects.select_related("maquinaria", "vehiculo", "operador")
    serializer_class = RegistroUsoSerializer
    permission_classes = [IsOperadorOAdministrador]
    http_method_names = ["get", "post", "head", "options"]

    def perform_create(self, serializer):
        obj = serializer.save()
        registrar_auditoria(
            self.request.user, "Registro de horas", "RegistroUso", obj.pk,
            f"{obj.activo}: {obj.horas} h",
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        maquinaria = self.request.query_params.get("maquinaria")
        vehiculo = self.request.query_params.get("vehiculo")
        if maquinaria:
            queryset = queryset.filter(maquinaria_id=maquinaria)
        if vehiculo:
            queryset = queryset.filter(vehiculo_id=vehiculo)
        return queryset


class MantencionViewSet(viewsets.ModelViewSet):
    queryset = Mantencion.objects.select_related("maquinaria", "vehiculo")
    serializer_class = MantencionSerializer
    permission_classes = [IsOperadorOAdministrador]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def create(self, request, *args, **kwargs):
        tipo = request.data.get("tipo")
        if tipo == Mantencion.PREVENTIVA and not _es_admin(request):
            return Response({"detail": "Solo el administrador programa mantenciones."}, status=403)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not _es_admin(request):
            return Response({"detail": "Solo el administrador reprograma mantenciones."}, status=403)
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        obj = serializer.save()
        registrar_auditoria(
            self.request.user, "Registro de mantencion", "Mantencion", obj.pk,
            f"{obj.tipo}: {obj.activo}",
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        maquinaria = self.request.query_params.get("maquinaria")
        vehiculo = self.request.query_params.get("vehiculo")
        tipo = self.request.query_params.get("tipo")
        desde = self.request.query_params.get("desde")
        hasta = self.request.query_params.get("hasta")
        if maquinaria:
            queryset = queryset.filter(maquinaria_id=maquinaria)
        if vehiculo:
            queryset = queryset.filter(vehiculo_id=vehiculo)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if desde:
            queryset = queryset.filter(Q(fecha_programada__gte=desde) | Q(fecha_realizada__gte=desde))
        if hasta:
            queryset = queryset.filter(Q(fecha_programada__lte=hasta) | Q(fecha_realizada__lte=hasta))
        return queryset

    @action(detail=True, methods=["post"])
    def realizar(self, request, pk=None):
        if not _es_admin(request):
            return Response({"detail": "Solo el administrador ejecuta una preventiva."}, status=403)
        obj = self.get_object()
        if obj.estado != Mantencion.PROGRAMADA:
            return Response({"detail": "La mantencion ya fue realizada."}, status=400)
        try:
            costo = float(request.data.get("costo", 0))
        except (TypeError, ValueError):
            return Response({"costo": "Ingrese un costo valido."}, status=400)
        if costo < 0:
            return Response({"costo": "El costo no puede ser negativo."}, status=400)
        obj.costo = costo
        obj.fecha_realizada = timezone.localdate()
        obj.estado = Mantencion.REALIZADA
        obj.reparacion = request.data.get("reparacion", obj.reparacion)
        obj.save(update_fields=["costo", "fecha_realizada", "estado", "reparacion"])
        activo = obj.activo
        activo.estado_operativo = (
            activo.OPERATIVA if request.data.get("reparacion_habilita", True)
            else activo.FUERA_DE_SERVICIO
        )
        activo.save(update_fields=["estado_operativo"])
        obj.alertas.filter(estado="activa").update(
            estado="resuelta", fecha_resuelta=timezone.now(), resuelta_por=request.user
        )
        registrar_auditoria(request.user, "Mantencion realizada", "Mantencion", obj.pk)
        return Response(self.get_serializer(obj).data)
