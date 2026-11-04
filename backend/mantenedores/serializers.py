"""Serializers del modulo de mantenedores (serializadores directos)."""
from rest_framework import serializers

from .models import Cliente, Material, Producto, Transportista, Vehiculo


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = [
            "id",
            "razon_social",
            "rut",
            "nombre_contacto",
            "telefono",
            "email",
            "direccion",
            "estado_pago",
            "estado",
        ]


class TransportistaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transportista
        fields = ["id", "nombre", "rut", "telefono", "cliente", "usuario", "estado"]

    def validate_cliente(self, value):
        """CU-18 Excepcion 2: no se asocia a un cliente inactivo."""
        sin_cambio = self.instance is not None and self.instance.cliente_id == value.pk
        if value.estado != Cliente.ACTIVO and not sin_cambio:
            raise serializers.ValidationError("El cliente seleccionado no está activo.")
        return value


class VehiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehiculo
        fields = [
            "id",
            "patente",
            "cliente",
            "capacidad_m3",
            "tramo",
            "descripcion",
            "es_mantenible",
            "datos_tecnicos",
            "horometro",
            "estado_operativo",
            "estado",
        ]

    def validate_horometro(self, value):
        if value < 0:
            raise serializers.ValidationError("El horometro no puede ser negativo.")
        if self.instance and value < self.instance.horometro:
            raise serializers.ValidationError("El horometro no puede retroceder.")
        return value


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = [
            "id",
            "nombre",
            "categoria",
            "densidad_kg_m3",
            "factor_reduccion_chip",
            "admite_chip",
            "estado",
        ]

    def validate_densidad_kg_m3(self, value):
        """CU-20 Excepcion 1: al editar, la densidad sigue siendo obligatoria."""
        if value is None and self.instance is not None:
            raise serializers.ValidationError("Ingresa una densidad mayor a cero.")
        if value is not None and value <= 0:
            raise serializers.ValidationError("Ingresa una densidad mayor a cero.")
        return value

    def validate_factor_reduccion_chip(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("El factor debe ser mayor a cero.")
        return value


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ["id", "nombre", "tipo", "precio", "unidad_de_venta", "estado"]

    def validate_nombre(self, value):
        """CU-22 Excepcion 2: el nombre no puede repetir el de otro producto."""
        otros = Producto.objects.filter(nombre__iexact=value)
        if self.instance is not None:
            otros = otros.exclude(pk=self.instance.pk)
        if otros.exists():
            raise serializers.ValidationError("Ya existe un producto con ese nombre.")
        return value
