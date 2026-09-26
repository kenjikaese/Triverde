from rest_framework import serializers
from .models import DocumentoLegal, VersionDocumento


class VersionDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersionDocumento
        fields = '__all__'
        read_only_fields = ['fecha_creacion']


class DocumentoLegalSerializer(serializers.ModelSerializer):
    versiones = VersionDocumentoSerializer(many=True, read_only=True)
    esta_vencido = serializers.BooleanField(read_only=True)

    class Meta:
        model = DocumentoLegal
        fields = '__all__'
        read_only_fields = ['fecha_creacion']
