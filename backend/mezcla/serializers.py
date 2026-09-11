from rest_framework import serializers

from .models import Alerta


class AlertaSerializer(serializers.ModelSerializer):
    activo_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Alerta
        fields = [
            "id", "origen", "clave", "nivel", "estado", "mensaje", "fecha_generada",
            "fecha_resuelta", "mantencion", "activo_nombre",
        ]
        read_only_fields = fields

    def get_activo_nombre(self, obj):
        if not obj.mantencion_id:
            return None
        activo = obj.mantencion.activo
        return activo.nombre if obj.mantencion.maquinaria_id else activo.patente
