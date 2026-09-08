from rest_framework import serializers
from .models import ProyeccionSemanal, ProyeccionMensual

class ProyeccionSemanalSerializer(serializers.ModelSerializer):
    # Usar un campo personalizado que maneje la conversión
    fecha_inicio = serializers.SerializerMethodField()
    fecha_fin = serializers.SerializerMethodField()
    
    class Meta:
        model = ProyeccionSemanal
        fields = '__all__'
    
    def get_fecha_inicio(self, obj):
        # Convertir datetime a date si es necesario
        if hasattr(obj.fecha_inicio, 'date'):
            return obj.fecha_inicio.date().isoformat()
        return obj.fecha_inicio
    
    def get_fecha_fin(self, obj):
        # Convertir datetime a date si es necesario
        if hasattr(obj.fecha_fin, 'date'):
            return obj.fecha_fin.date().isoformat()
        return obj.fecha_fin

class ProyeccionMensualSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProyeccionMensual
        fields = '__all__'

class RendimientoCamionSerializer(serializers.Serializer):
    camion_id = serializers.IntegerField()
    patente = serializers.CharField()
    periodo = serializers.CharField()
    viajes_realizados = serializers.IntegerField()
    total_m3_recibidos = serializers.FloatField()
    total_kg_recibidos = serializers.FloatField()
    total_chip_producido_kg = serializers.FloatField()
    ventas_totales = serializers.FloatField()
    costos_operativos = serializers.FloatField()
    utilidad_neta = serializers.FloatField()
    rendimiento_por_kg = serializers.FloatField()
    margen_porcentual = serializers.FloatField()
