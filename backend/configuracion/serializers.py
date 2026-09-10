"""Serializers del modulo de configuracion."""
from rest_framework import serializers

from .models import HistorialCambioParametro, ParametroConversion, TarifaRecepcion


class ParametroConversionSerializer(serializers.ModelSerializer):
    """Parametro global de conversion."""

    class Meta:
        model = ParametroConversion
        fields = ["id", "clave", "nombre", "valor", "unidad", "descripcion"]

    def validate(self, attrs):
        clave = attrs.get("clave", getattr(self.instance, "clave", ""))
        valor = attrs.get("valor", getattr(self.instance, "valor", None))
        if clave in {"alerta_mantenimiento_dias", "alerta_mantenimiento_horas"}:
            if valor is None or valor <= 0:
                raise serializers.ValidationError(
                    {"valor": "La anticipacion debe ser mayor que cero."}
                )
            if clave == "alerta_mantenimiento_dias" and valor != valor.to_integral_value():
                raise serializers.ValidationError(
                    {"valor": "La anticipacion en dias debe ser un numero entero."}
                )
        return attrs


class TarifaRecepcionSerializer(serializers.ModelSerializer):
    """Tarifa por tramo de camion (m3)."""

    class Meta:
        model = TarifaRecepcion
        fields = ["id", "tramo_min_m3", "tramo_max_m3", "monto", "vigente"]


class HistorialCambioParametroSerializer(serializers.ModelSerializer):
    """Historial de cambios de parametro (solo lectura via API)."""

    parametro_clave = serializers.CharField(source="parametro.clave", read_only=True)
    usuario_username = serializers.CharField(source="usuario.username", read_only=True)

    class Meta:
        model = HistorialCambioParametro
        fields = [
            "id",
            "parametro",
            "parametro_clave",
            "usuario",
            "usuario_username",
            "valor_anterior",
            "valor_nuevo",
            "fecha_hora",
        ]
        read_only_fields = fields
