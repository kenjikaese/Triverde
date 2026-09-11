"""Serializers de consulta del calculo de mezcla y de alertas (CU-45/47).

``AlertaSerializer`` es unico para todos los origenes: expone tanto los campos
de mezcla (pila, categoria, faltante) como los de mantencion (activo). Los
campos que no aplican al origen de la alerta se resuelven como ``null``.
"""
from rest_framework import serializers

from .models import Alerta
from .services import calcular_mezcla


class AlertaSerializer(serializers.ModelSerializer):
    """Representacion de lectura para la bandeja de alertas."""

    pila_codigo = serializers.CharField(source="pila.codigo", read_only=True)
    categoria_display = serializers.CharField(source="get_categoria_display", read_only=True)
    resuelta_por_username = serializers.CharField(source="resuelta_por.username", read_only=True)
    activo_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Alerta
        fields = [
            "id", "origen", "clave", "nivel", "estado", "mensaje",
            "categoria", "categoria_display", "faltante_m3", "disponible_m3",
            "pila", "pila_codigo", "mantencion", "activo_nombre",
            "fecha_generada", "fecha_resuelta", "resuelta_por_username",
        ]
        read_only_fields = fields

    def get_activo_nombre(self, obj):
        if not obj.mantencion_id:
            return None
        activo = obj.mantencion.activo
        return activo.nombre if obj.mantencion.maquinaria_id else activo.patente


class MezclaObjetivoSerializer(serializers.Serializer):
    """Respuesta de CU-45: receta, composicion, faltantes y disponibilidad."""
    pila = serializers.IntegerField(source="pila.id")
    pila_codigo = serializers.CharField(source="pila.codigo")
    estado = serializers.CharField(source="pila.estado")
    receta = serializers.SerializerMethodField()
    mensaje = serializers.CharField(allow_null=True)
    actual = serializers.SerializerMethodField()
    faltantes = serializers.SerializerMethodField()
    disponibles = serializers.SerializerMethodField()

    def get_receta(self, resultado):
        receta = resultado["receta"]
        if receta is None:
            return None
        return {
            "id": receta.id,
            "nombre": receta.nombre,
            "relacion_seca": receta.relacion_seca,
            "relacion_verde": receta.relacion_verde,
            "proporcion": receta.proporcion,
        }

    def _categorias(self, resultado, clave):
        """Convierte el mapa interno por categoria al formato de la API."""
        return [
            {"categoria": categoria, "volumen_m3": resultado[clave][categoria]}
            for categoria in ("seca", "verde")
        ]

    def get_actual(self, resultado):
        return self._categorias(resultado, "actual")

    def get_faltantes(self, resultado):
        return self._categorias(resultado, "faltantes")

    def get_disponibles(self, resultado):
        return self._categorias(resultado, "disponibles")

    @classmethod
    def from_pila(cls, pila):
        """Atajo para serializar un calculo completo de una pila."""
        return cls(calcular_mezcla(pila)).data
