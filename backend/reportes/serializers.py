"""Serializadores de consulta y generacion de reportes."""

from rest_framework import serializers

from .models import Reporte


class ReporteSerializer(serializers.ModelSerializer):
    """Representacion de un reporte ya generado."""
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = Reporte
        fields = [
            "id", "tipo", "tipo_display", "periodo_inicio", "periodo_fin",
            "formato", "fecha_generado", "usuario", "contenido",
        ]
        read_only_fields = ["id", "fecha_generado", "usuario", "contenido"]


class GenerarReporteSerializer(serializers.Serializer):
    """Entrada comun para CU-73, CU-74 y CU-75."""
    tipo = serializers.ChoiceField(choices=Reporte.TIPO_CHOICES)
    periodo_inicio = serializers.DateField()
    periodo_fin = serializers.DateField()
    formato = serializers.ChoiceField(choices=Reporte.FORMATO_CHOICES, default=Reporte.PDF)
    cliente = serializers.IntegerField(required=False, allow_null=True)
    material = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs["periodo_fin"] < attrs["periodo_inicio"]:
            raise serializers.ValidationError(
                {"periodo_fin": "La fecha de termino no puede ser anterior a la fecha de inicio."}
            )
        if attrs["tipo"] != Reporte.RECEPCIONES and (
            attrs.get("cliente") or attrs.get("material")
        ):
            raise serializers.ValidationError(
                "Los filtros de cliente y material solo aplican al reporte de recepciones."
            )
        return attrs
