"""Serializers del modulo de recepcion (agregado Recepcion + partes).

`RecepcionSerializer` acepta y devuelve `detalles`, `fotos` y `multas`
anidados. El agregado se crea completo o no se crea (`transaction.atomic`).

`peso_derivado_kg` y `chip_derivado_m3` son derivados en el servidor: el
cliente solo teclea `volumen_m3` y elige el `material`.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import serializers

from common.fields import Base64ImageField

from .models import DetalleRecepcion, FotoRecepcion, Multa, Recepcion


def derivar_peso_y_chip(material, volumen_m3):
    """Deriva peso y chip a partir de volumen y parametros del material.

    Reglas (brief capa API sec. 4.3):
    - peso = volumen * material.densidad_kg_m3 (obligatorio).
    - chip = volumen / material.factor_reduccion_chip solo si admite_chip y
      hay factor configurado.

    Lanza ValidationError si el material no tiene densidad configurada: no se
    inventa una densidad por defecto.
    """
    if material.densidad_kg_m3 is None:
        raise serializers.ValidationError(
            f"El material '{material.nombre}' no tiene densidad configurada; "
            "no se puede derivar el peso."
        )
    try:
        volumen = Decimal(str(volumen_m3))
    except (InvalidOperation, TypeError, ValueError):
        raise serializers.ValidationError(
            {"volumen_m3": "El volumen debe ser un numero valido."}
        )
    peso = volumen * material.densidad_kg_m3
    if peso >= Decimal("100000000"):
        raise serializers.ValidationError(
            "El peso derivado supera la capacidad del sistema; revise el "
            "volumen o la densidad del material."
        )
    peso = peso.quantize(Decimal("0.01"))
    chip = None
    if material.admite_chip and material.factor_reduccion_chip:
        factor = material.factor_reduccion_chip
        if factor > 0:
            chip_crudo = volumen / factor
            if chip_crudo < Decimal("1000000"):
                chip = chip_crudo.quantize(Decimal("0.01"))
    return peso, chip


class DetalleRecepcionSerializer(serializers.ModelSerializer):
    """Linea material+volumen. Los derivados son de lectura (calculados)."""

    id_local = serializers.UUIDField(required=False)
    peso_derivado_kg = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    chip_derivado_m3 = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )

    class Meta:
        model = DetalleRecepcion
        fields = [
            "id",
            "id_local",
            "material",
            "volumen_m3",
            "peso_derivado_kg",
            "chip_derivado_m3",
            "destino_sugerido",
        ]

    def validate(self, attrs):
        material = attrs.get("material")
        volumen = attrs.get("volumen_m3")
        if material is not None and volumen is not None:
            attrs["_peso"], attrs["_chip"] = derivar_peso_y_chip(material, volumen)
            if not attrs.get("destino_sugerido"):
                from mezcla.services import sugerir_destino

                attrs["destino_sugerido"] = sugerir_destino(material)
        return attrs


class FotoRecepcionSerializer(serializers.ModelSerializer):
    """Foto de respaldo.

    `archivo` acepta base64 (sync offline: la cola local la envia embebida en el
    JSON, CU-33) o un archivo subido por multipart (CRUD online).
    """

    id_local = serializers.UUIDField(required=False)
    archivo = Base64ImageField()

    class Meta:
        model = FotoRecepcion
        fields = ["id", "id_local", "archivo", "fecha"]
        read_only_fields = ["fecha"]


class MultaSerializer(serializers.ModelSerializer):
    """Multa por material contaminado."""

    id_local = serializers.UUIDField(required=False)

    class Meta:
        model = Multa
        fields = ["id", "id_local", "cliente", "motivo", "monto", "fecha"]


class RecepcionSerializer(serializers.ModelSerializer):
    """Cabecera de recepcion con sus partes anidadas (agregado).

    `id_local` es escribible en la entrada (lo genera el dispositivo offline)
    pero estable en actualizaciones. `estado_sincronizacion` lo gobierna el
    endpoint de sincronizacion (CU-33): aqui es de solo lectura.
    """

    id_local = serializers.UUIDField(required=False)
    estado_sincronizacion = serializers.CharField(read_only=True)
    detalles = DetalleRecepcionSerializer(many=True, required=False)
    fotos = FotoRecepcionSerializer(many=True, required=False)
    multas = MultaSerializer(many=True, required=False)

    class Meta:
        model = Recepcion
        fields = [
            "id",
            "id_local",
            "estado_sincronizacion",
            "cliente",
            "transportista",
            "vehiculo",
            "operador",
            "conductor",
            "fecha",
            "hora",
            "estado",
            "motivo_rechazo",
            "observaciones",
            "detalles",
            "fotos",
            "multas",
        ]

    def _crear_detalles(self, recepcion, detalles_data):
        for detalle in detalles_data:
            peso = detalle.pop("_peso")
            chip = detalle.pop("_chip")
            DetalleRecepcion.objects.create(
                recepcion=recepcion,
                peso_derivado_kg=peso,
                chip_derivado_m3=chip,
                **detalle,
            )

    def create(self, validated_data):
        detalles_data = validated_data.pop("detalles", [])
        fotos_data = validated_data.pop("fotos", [])
        multas_data = validated_data.pop("multas", [])
        with transaction.atomic():
            recepcion = Recepcion.objects.create(**validated_data)
            self._crear_detalles(recepcion, detalles_data)
            for foto in fotos_data:
                FotoRecepcion.objects.create(recepcion=recepcion, **foto)
            for multa in multas_data:
                Multa.objects.create(recepcion=recepcion, **multa)
        return recepcion

    def update(self, instance, validated_data):
        validated_data.pop("id_local", None)
        detalles_data = validated_data.pop("detalles", None)
        fotos_data = validated_data.pop("fotos", None)
        multas_data = validated_data.pop("multas", None)
        with transaction.atomic():
            for atributo, valor in validated_data.items():
                setattr(instance, atributo, valor)
            instance.save()
            if detalles_data is not None:
                instance.detalles.all().delete()
                self._crear_detalles(instance, detalles_data)
            if fotos_data is not None:
                instance.fotos.all().delete()
                for foto in fotos_data:
                    FotoRecepcion.objects.create(recepcion=instance, **foto)
            if multas_data is not None:
                instance.multas.all().delete()
                for multa in multas_data:
                    Multa.objects.create(recepcion=instance, **multa)
        return instance
