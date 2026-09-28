from rest_framework import serializers

from .models import PanelControl
from .services import INDICADORES_VALIDOS


class PanelControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = PanelControl
        fields = ["id", "usuario", "indicadores_visibles", "configuracion", "actualizado"]
        read_only_fields = ["id", "usuario", "actualizado"]


class PreferenciasPanelSerializer(serializers.Serializer):
    indicadores_visibles = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    configuracion = serializers.JSONField(required=False)

    def validate_indicadores_visibles(self, value):
        invalidos = sorted(set(value) - INDICADORES_VALIDOS)
        if invalidos:
            raise serializers.ValidationError(
                f"Indicadores no válidos: {', '.join(invalidos)}"
            )
        return value
