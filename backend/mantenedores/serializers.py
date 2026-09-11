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


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ["id", "nombre", "tipo", "precio", "unidad_de_venta", "estado"]
