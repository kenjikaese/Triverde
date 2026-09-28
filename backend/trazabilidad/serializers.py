from rest_framework import serializers

from .models import CertificadoTrazabilidad, DeclaracionSinader, IndicadorAmbiental


class CertificadoTrazabilidadSerializer(serializers.ModelSerializer):
    """Certificado emitido (CU-65/66). Solo lectura: se emite por accion."""

    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    cliente_razon_social = serializers.CharField(
        source="cliente.razon_social", read_only=True
    )
    referencia = serializers.SerializerMethodField()

    class Meta:
        model = CertificadoTrazabilidad
        fields = [
            "id",
            "codigo",
            "tipo",
            "tipo_display",
            "cliente",
            "cliente_razon_social",
            "recepcion",
            "periodo_inicio",
            "periodo_fin",
            "fecha_emision",
            "referencia",
            "contenido",
        ]
        read_only_fields = fields

    def get_referencia(self, certificado):
        if certificado.tipo == CertificadoTrazabilidad.DESCARGA:
            return f"Recepcion #{certificado.recepcion_id}"
        return f"{certificado.periodo_inicio} a {certificado.periodo_fin}"


class DeclaracionSinaderSerializer(serializers.ModelSerializer):
    """Declaracion generada (CU-67). El archivo se descarga por accion."""

    usuario_nombre = serializers.CharField(
        source="usuario.nombre_completo", read_only=True, default=None
    )
    nombre_archivo = serializers.SerializerMethodField()

    class Meta:
        model = DeclaracionSinader
        fields = [
            "id",
            "periodo_inicio",
            "periodo_fin",
            "fecha_generada",
            "usuario",
            "usuario_nombre",
            "nombre_archivo",
            "contenido",
        ]
        read_only_fields = fields

    def get_nombre_archivo(self, declaracion):
        return declaracion.archivo.name.rsplit("/", 1)[-1] if declaracion.archivo else None


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

