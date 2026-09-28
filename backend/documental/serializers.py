from rest_framework import serializers

from .models import DocumentoLegal, VersionDocumento


class VersionDocumentoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source="usuario.nombre_completo", read_only=True, default=None
    )

    class Meta:
        model = VersionDocumento
        fields = [
            "id",
            "documento",
            "version",
            "archivo",
            "nombre_archivo",
            "fecha_carga",
            "usuario",
            "usuario_nombre",
            "vigente",
            "fecha_emision",
            "fecha_vencimiento",
        ]
        read_only_fields = fields


class DocumentoLegalSerializer(serializers.ModelSerializer):
    """CU-86: registro y edicion de los datos basicos.

    La vigencia (`fecha_emision`, `fecha_vencimiento`) y el `estado` se
    registran por sus propias acciones (CU-88/CU-89) para que el estado siempre
    quede derivado de las fechas; aca son de solo lectura.
    """

    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    version_vigente = serializers.SerializerMethodField()

    class Meta:
        model = DocumentoLegal
        fields = [
            "id",
            "nombre",
            "tipo",
            "tipo_display",
            "tipo_detalle",
            "entidad_emisora",
            "fecha_emision",
            "fecha_vencimiento",
            "estado",
            "estado_display",
            "fecha_registro",
            "version_vigente",
        ]
        read_only_fields = [
            "fecha_emision",
            "fecha_vencimiento",
            "estado",
            "fecha_registro",
        ]

    def get_version_vigente(self, documento):
        version = documento.version_vigente()
        if version is None:
            return None
        return VersionDocumentoSerializer(version, context=self.context).data

    def validate_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("El nombre del documento es obligatorio.")
        return valor

    def validate_entidad_emisora(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("La entidad emisora es obligatoria.")
        return valor

    def validate(self, attrs):
        tipo = attrs.get("tipo", getattr(self.instance, "tipo", DocumentoLegal.OTRO))
        detalle = attrs.get("tipo_detalle", getattr(self.instance, "tipo_detalle", ""))
        if tipo == DocumentoLegal.OTRO and not (detalle or "").strip():
            raise serializers.ValidationError(
                {"tipo_detalle": "Describa la clasificacion cuando el tipo es 'otro'."}
            )
        if tipo != DocumentoLegal.OTRO:
            attrs["tipo_detalle"] = ""
        return attrs
