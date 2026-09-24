from rest_framework import serializers

from .models import IndicadorAmbiental


class IndicadorAmbientalSerializer(serializers.ModelSerializer):
    origen_display = serializers.CharField(source="get_origen_display", read_only=True)
    referencia = serializers.SerializerMethodField()
    descripcion = serializers.SerializerMethodField()

    class Meta:
        model = IndicadorAmbiental
        fields = [
            "id",
            "origen",
            "origen_display",
            "recepcion",
            "pila",
            "referencia",
            "descripcion",
            "co2_evitado_kg",
            "metodo",
            "fecha",
        ]
        read_only_fields = fields

    def get_referencia(self, indicador):
        if indicador.origen == IndicadorAmbiental.RECEPCION:
            return f"Recepcion #{indicador.recepcion_id}"
        return indicador.pila.codigo

    def get_descripcion(self, indicador):
        if indicador.origen == IndicadorAmbiental.RECEPCION:
            return indicador.recepcion.cliente.razon_social
        return "Lote compostado"

