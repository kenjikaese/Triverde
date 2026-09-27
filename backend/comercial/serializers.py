"""Serializers del modulo comercial.

`VentaSerializer` es el agregado: acepta y devuelve sus `detalles` anidados y
se crea completo o no se crea (`transaction.atomic`), igual que el agregado de
recepcion del Incremento 1.

Los montos son derivados del servidor: quien registra teclea la cantidad y
elige el producto; el `precio_unitario`, el `subtotal` y el `total` los calcula
el backend a partir del catalogo.
"""
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from mantenedores.models import Producto

from .models import (
    Cobro,
    Cotizacion,
    Despacho,
    DetalleVenta,
    DocumentoTributario,
    Venta,
)
from .services import calcular_costo_cotizacion, tarifa_sugerida


class CotizacionSerializer(serializers.ModelSerializer):
    """Cotizacion de servicio (CU-55).

    `costo_estimado` es de solo lectura: lo calcula el servidor aplicando el
    costo por kilometro vigente sobre el recorrido de ida y vuelta.
    """

    cliente_razon_social = serializers.CharField(
        source="cliente.razon_social", read_only=True
    )
    costo_estimado = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Cotizacion
        fields = [
            "id",
            "cliente",
            "cliente_razon_social",
            "fecha",
            "distancia_km",
            "servicio",
            "costo_estimado",
            "estado",
        ]
        read_only_fields = ["fecha"]

    def validate_distancia_km(self, valor):
        # CU-55, Excepcion 2: distancia en cero, vacia o negativa.
        if valor is None or valor <= 0:
            raise serializers.ValidationError(
                "La distancia debe ser mayor a cero."
            )
        return valor

    def create(self, validated_data):
        validated_data["costo_estimado"] = calcular_costo_cotizacion(
            validated_data["distancia_km"]
        )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instancia = super().update(instance, validated_data)
        instancia.costo_estimado = calcular_costo_cotizacion(
            instancia.distancia_km
        )
        instancia.save(update_fields=["costo_estimado"])
        return instancia


class DetalleVentaSerializer(serializers.ModelSerializer):
    """Linea producto + cantidad. Precio, unidad y subtotal son derivados."""

    producto_nombre = serializers.CharField(
        source="producto.nombre", read_only=True
    )
    pila_codigo = serializers.CharField(
        source="pila.codigo", read_only=True, default=None
    )
    unidad = serializers.CharField(read_only=True)
    precio_unitario = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    subtotal = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = DetalleVenta
        fields = [
            "id",
            "producto",
            "producto_nombre",
            "pila",
            "pila_codigo",
            "cantidad",
            "unidad",
            "precio_unitario",
            "subtotal",
        ]

    def validate_cantidad(self, valor):
        # CU-58, Excepcion 3: cantidad en cero o vacia.
        if valor is None or valor <= 0:
            raise serializers.ValidationError(
                "La cantidad debe ser mayor a cero."
            )
        return valor

    def validate_producto(self, producto):
        # CU-58: el producto vendido debe estar activo y tener precio.
        if producto.estado != Producto.ACTIVO:
            raise serializers.ValidationError(
                f"El producto {producto.nombre} no esta activo."
            )
        if producto.precio is None:
            raise serializers.ValidationError(
                f"El producto {producto.nombre} no tiene precio configurado; "
                "no se puede calcular el monto de la venta."
            )
        return producto


class VentaSerializer(serializers.ModelSerializer):
    """Cabecera de venta con sus lineas anidadas (agregado).

    `estado` lo gobierna el despacho (CU-60), no la escritura directa: nace en
    "pendiente" y solo la accion de despachar lo mueve a "despachada".
    """

    cliente_razon_social = serializers.CharField(
        source="cliente.razon_social", read_only=True
    )
    detalles = DetalleVentaSerializer(many=True)
    estado = serializers.CharField(read_only=True)
    total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    despachada = serializers.SerializerMethodField()

    class Meta:
        model = Venta
        fields = [
            "id",
            "cliente",
            "cliente_razon_social",
            "fecha",
            "estado",
            "total",
            "detalles",
            "despachada",
        ]
        read_only_fields = ["fecha"]

    def get_despachada(self, obj):
        return hasattr(obj, "despacho")

    def validate_detalles(self, detalles):
        if not detalles:
            raise serializers.ValidationError(
                "La venta debe tener al menos una linea de producto."
            )
        return detalles

    def _crear_detalles(self, venta, detalles_data):
        """Crea las lineas derivando precio, unidad y subtotal del catalogo."""
        total = Decimal("0.00")
        for detalle in detalles_data:
            producto = detalle["producto"]
            cantidad = Decimal(str(detalle["cantidad"]))
            subtotal = (cantidad * producto.precio).quantize(Decimal("0.01"))
            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                pila=detalle.get("pila"),
                cantidad=cantidad,
                unidad=producto.unidad_de_venta,
                precio_unitario=producto.precio,
                subtotal=subtotal,
            )
            total += subtotal
        venta.total = total
        venta.save(update_fields=["total"])

    def create(self, validated_data):
        detalles_data = validated_data.pop("detalles", [])
        with transaction.atomic():
            venta = Venta.objects.create(**validated_data)
            self._crear_detalles(venta, detalles_data)
        return venta

    def update(self, instance, validated_data):
        detalles_data = validated_data.pop("detalles", None)
        with transaction.atomic():
            for atributo, valor in validated_data.items():
                setattr(instance, atributo, valor)
            instance.save()
            if detalles_data is not None:
                instance.detalles.all().delete()
                self._crear_detalles(instance, detalles_data)
        return instance


class DespachoSerializer(serializers.ModelSerializer):
    """Despacho de una venta (CU-60). La venta la fija la accion del viewset."""

    venta = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Despacho
        fields = ["id", "venta", "fecha", "direccion", "receptor", "estado"]
        read_only_fields = ["estado"]

    def validate_receptor(self, valor):
        # CU-60, Excepcion 1: confirmar sin indicar quien retira.
        if not valor or not valor.strip():
            raise serializers.ValidationError(
                "Debe indicar quien retira el producto."
            )
        return valor


class CobroSerializer(serializers.ModelSerializer):
    """Cobro de una venta o de una recepcion (CU-61).

    Expone `monto_sugerido` en la lectura para que la vista muestre la tarifa
    del tramo sin recalcularla en el navegador.
    """

    monto_sugerido = serializers.SerializerMethodField()

    class Meta:
        model = Cobro
        fields = [
            "id",
            "venta",
            "recepcion",
            "cliente",
            "monto",
            "monto_sugerido",
            "fecha",
            "medio",
            "estado",
        ]

    def get_monto_sugerido(self, obj):
        return tarifa_sugerida(obj.recepcion) if obj.recepcion_id else None

    def validate_monto(self, valor):
        # CU-61, Excepcion 2: monto en cero o negativo.
        if valor is None or valor <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a cero.")
        return valor

    def validate(self, attrs):
        venta = attrs.get("venta", getattr(self.instance, "venta", None))
        recepcion = attrs.get(
            "recepcion", getattr(self.instance, "recepcion", None)
        )
        if bool(venta) == bool(recepcion):
            raise serializers.ValidationError(
                "El cobro debe apuntar a una venta o a una recepcion, no a "
                "ambas ni a ninguna."
            )
        return attrs


class DocumentoTributarioSerializer(serializers.ModelSerializer):
    """Documento tributario pendiente (CU-63): seguimiento, no emision."""

    class Meta:
        model = DocumentoTributario
        fields = [
            "id",
            "venta",
            "cobro",
            "cliente",
            "tipo",
            "folio",
            "monto",
            "estado",
            "fecha",
        ]
        read_only_fields = ["estado"]

    def validate_monto(self, valor):
        # CU-63, Excepcion 1: el origen no tiene monto, se ingresa a mano.
        if valor is None or valor <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a cero.")
        return valor

    def validate(self, attrs):
        venta = attrs.get("venta", getattr(self.instance, "venta", None))
        cobro = attrs.get("cobro", getattr(self.instance, "cobro", None))
        if bool(venta) == bool(cobro):
            raise serializers.ValidationError(
                "El documento debe apuntar a una venta o a un cobro, no a "
                "ambos ni a ninguno."
            )
        return attrs


class MovimientoCuentaCorrienteSerializer(serializers.Serializer):
    """Una linea del detalle cronologico de la cuenta corriente (CU-64)."""

    tipo = serializers.CharField()
    id = serializers.IntegerField()
    fecha = serializers.DateField()
    detalle = serializers.CharField()
    monto = serializers.DecimalField(max_digits=12, decimal_places=2)


class CuentaCorrienteSerializer(serializers.Serializer):
    """Saldo calculado del cliente y sus movimientos (CU-64)."""

    cliente = serializers.IntegerField()
    razon_social = serializers.CharField()
    estado_pago = serializers.CharField()
    total_ventas = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_cobros = serializers.DecimalField(max_digits=12, decimal_places=2)
    saldo = serializers.DecimalField(max_digits=12, decimal_places=2)
    movimientos = MovimientoCuentaCorrienteSerializer(many=True)
