from rest_framework import serializers

from .models import Proyeccion


class ProyeccionSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    material_nombre = serializers.CharField(
        source="material.nombre", read_only=True, default=None
    )

    class Meta:
        model = Proyeccion
        fields = [
            "id", "tipo", "tipo_display", "periodo_inicio", "periodo_fin",
            "material", "material_nombre", "supuestos", "valor_proyectado",
            "fecha_generada", "usuario",
        ]
        read_only_fields = ["valor_proyectado", "fecha_generada", "usuario"]

    def validate(self, attrs):
        tipo = attrs.get("tipo")
        if tipo == Proyeccion.SEMANAL and attrs.get("material") is None:
            raise serializers.ValidationError(
                {"material": "La proyeccion semanal por material requiere un material."}
            )
        inicio, fin = attrs.get("periodo_inicio"), attrs.get("periodo_fin")
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError(
                {"periodo_fin": "El fin del periodo no puede ser anterior al inicio."}
            )
        return attrs
