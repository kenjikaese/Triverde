"""Vistas del modulo de mantenedores (C_Clientes ... C_Vehiculos).

Administrador: CRUD. Operador: solo lectura. Transportista: sin acceso.
Todos usan baja logica en `destroy()` (`estado = inactivo`).
"""
from rest_framework import status, viewsets
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import EsAdministradorOOperadorLectura
from common.views import BajaLogicaMixin, FiltroEstadoMixin

from .models import Cliente, Material, Producto, Transportista, Vehiculo
from .serializers import (
    ClienteSerializer,
    MaterialSerializer,
    ProductoSerializer,
    TransportistaSerializer,
    VehiculoSerializer,
)


class ClienteViewSet(FiltroEstadoMixin, BajaLogicaMixin, viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [EsAdministradorOOperadorLectura]
    search_fields = ["razon_social", "rut", "nombre_contacto", "email"]
    ordering_fields = ["razon_social", "estado", "estado_pago"]


class TransportistaViewSet(FiltroEstadoMixin, BajaLogicaMixin, viewsets.ModelViewSet):
    queryset = Transportista.objects.select_related("cliente", "usuario").all()
    serializer_class = TransportistaSerializer
    permission_classes = [EsAdministradorOOperadorLectura]
    search_fields = ["nombre", "rut", "telefono"]
    ordering_fields = ["nombre", "estado"]


class VehiculoViewSet(FiltroEstadoMixin, BajaLogicaMixin, viewsets.ModelViewSet):
    queryset = Vehiculo.objects.select_related("cliente").all()
    serializer_class = VehiculoSerializer
    permission_classes = [EsAdministradorOOperadorLectura]
    search_fields = ["patente", "tramo", "descripcion"]
    ordering_fields = ["patente", "estado_operativo", "estado"]

    def perform_update(self, serializer):
        era_mantenible = serializer.instance.es_mantenible
        vehiculo = serializer.save()
        if not era_mantenible and vehiculo.es_mantenible:
            registrar_auditoria(
                self.request.user, "Alta mantenible", "Vehiculo", vehiculo.pk,
                vehiculo.patente,
            )

    def destroy(self, request, *args, **kwargs):
        vehiculo = self.get_object()
        if vehiculo.es_mantenible:
            from mantenimiento.models import Mantencion
            pendiente = vehiculo.mantencions.filter(
                estado=Mantencion.PROGRAMADA
            ).exists()
            requiere_confirmacion = (
                vehiculo.estado_operativo == vehiculo.EN_MANTENCION or pendiente
            )
            if requiere_confirmacion and not request.data.get("confirmar_baja"):
                return Response(
                    {"confirmar_baja": "El vehiculo esta en mantencion o tiene una mantencion pendiente."},
                    status=status.HTTP_409_CONFLICT,
                )
        vehiculo.estado = vehiculo.INACTIVO
        vehiculo.save(update_fields=["estado"])
        registrar_auditoria(
            request.user, "Baja", "Vehiculo", vehiculo.pk, vehiculo.patente
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MaterialViewSet(FiltroEstadoMixin, BajaLogicaMixin, viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [EsAdministradorOOperadorLectura]
    search_fields = ["nombre", "categoria"]
    ordering_fields = ["nombre", "categoria", "estado"]


class ProductoViewSet(FiltroEstadoMixin, BajaLogicaMixin, viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [EsAdministradorOOperadorLectura]
    search_fields = ["nombre", "tipo"]
    ordering_fields = ["nombre", "tipo", "precio", "estado"]
