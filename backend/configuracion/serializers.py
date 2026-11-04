"""Serializers del modulo de configuracion."""
from rest_framework import serializers

from .models import (
    CostoOperativo,
    CostoTransporte,
    HistorialCambioParametro,
    ParametroConversion,
    RecetaMezcla,
    TarifaRecepcion,
)


def positivo(valor):
    if valor is None or valor <= 0:
        raise serializers.ValidationError("Debe ser mayor a cero")
    return valor


class ParametroConversionSerializer(serializers.ModelSerializer):
    """Parametro global de conversion."""

    class Meta:
        model = ParametroConversion
        fields = ["id", "clave", "nombre", "valor", "unidad", "descripcion"]

    def validate(self, attrs):
        clave = attrs.get("clave", getattr(self.instance, "clave", ""))
        valor = attrs.get("valor", getattr(self.instance, "valor", None))
        if clave in {
            "alerta_mantenimiento_dias",
            "alerta_mantenimiento_horas",
            "co2_evitado_camion",
            "co2_evitado_compostaje",
        }:
            if valor is None or valor <= 0:
                raise serializers.ValidationError(
                    {"valor": "El valor del parametro debe ser mayor que cero."}
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

    validate_monto = staticmethod(positivo)

    def validate(self, attrs):
        """CU-11: el rango debe ser valido y no superponerse con otro tramo vigente."""
        minimo = attrs.get("tramo_min_m3", getattr(self.instance, "tramo_min_m3", None))
        maximo = attrs.get("tramo_max_m3", getattr(self.instance, "tramo_max_m3", None))
        vigente = attrs.get("vigente", getattr(self.instance, "vigente", True))
        if minimo is not None and maximo is not None:
            if minimo >= maximo:
                raise serializers.ValidationError(
                    {"tramo_max_m3": "El volumen máximo debe ser mayor que el mínimo."}
                )
            if vigente:
                otros = TarifaRecepcion.objects.filter(
                    vigente=True, tramo_min_m3__lt=maximo, tramo_max_m3__gt=minimo
                )
                if self.instance:
                    otros = otros.exclude(pk=self.instance.pk)
                if otros.exists():
                    raise serializers.ValidationError(
                        {"tramo_min_m3": "El rango se superpone con otro tramo vigente."}
                    )
        return attrs


class HistorialCambioParametroSerializer(serializers.ModelSerializer):
    """Historial de cambios de parametro (solo lectura via API)."""

    parametro_clave = serializers.CharField(source="parametro.clave", read_only=True)
    parametro_nombre = serializers.CharField(source="parametro.nombre", read_only=True)
    usuario_username = serializers.CharField(source="usuario.username", read_only=True)

    class Meta:
        model = HistorialCambioParametro
        fields = [
            "id",
            "parametro",
            "parametro_clave",
            "parametro_nombre",
            "usuario",
            "usuario_username",
            "valor_anterior",
            "valor_nuevo",
            "fecha_hora",
        ]
        read_only_fields = fields


class RecetaMezclaSerializer(serializers.ModelSerializer):
    """Receta de mezcla seca/verde para compostaje."""

    proporcion = serializers.CharField(read_only=True)

    class Meta:
        model = RecetaMezcla
        fields = [
            "id", "nombre", "relacion_seca", "relacion_verde", "proporcion",
            "descripcion", "vigente", "actualizado_en",
        ]
        read_only_fields = ["actualizado_en"]

    validate_relacion_seca = staticmethod(positivo)
    validate_relacion_verde = staticmethod(positivo)


class CostoTransporteSerializer(serializers.ModelSerializer):
    """Costo de transporte por km vigente."""

    class Meta:
        model = CostoTransporte
        fields = ["id", "costo_por_km", "vigente", "fecha"]
        read_only_fields = ["vigente", "fecha"]

    validate_costo_por_km = staticmethod(positivo)


class CostoOperativoSerializer(serializers.ModelSerializer):
    """Costo operativo por concepto."""

    unidad_display = serializers.CharField(source="get_unidad_display", read_only=True)

    class Meta:
        model = CostoOperativo
        fields = ["id", "concepto", "monto", "unidad", "unidad_display", "vigente", "actualizado_en"]
        read_only_fields = ["vigente", "actualizado_en"]
        # El nombre repetido lo revisa validate(): sin esto DRF responde antes con un
        # mensaje generico, sin distinguir mayusculas ni sugerir editar (CU-13 Excepcion 1).
        extra_kwargs = {"concepto": {"validators": []}}

    validate_monto = staticmethod(positivo)

    def validate_concepto(self, valor):
        return valor.strip()

    def validate(self, data):
        concepto = data.get("concepto", getattr(self.instance, "concepto", None))
        vigente = getattr(self.instance, "vigente", True)

        if concepto and vigente:
            duplicados = CostoOperativo.objects.filter(concepto__iexact=concepto, vigente=True)
            if self.instance:
                duplicados = duplicados.exclude(pk=self.instance.pk)
            if duplicados.exists():
                raise serializers.ValidationError(
                    {"concepto": f'Ya existe un costo operativo vigente llamado "{concepto}". Edita ese concepto en su lugar.'}
                )
        return data
