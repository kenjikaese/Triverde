from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime

from .models import DocumentoLegal, VersionDocumento
from .serializers import DocumentoLegalSerializer, VersionDocumentoSerializer
from .services import DocumentoService


class DocumentoLegalViewSet(viewsets.ModelViewSet):
    """
    ViewSet para DocumentoLegal.
    Cubre CU-86, CU-87, CU-88, CU-89.
    """
    queryset = DocumentoLegal.objects.all()
    serializer_class = DocumentoLegalSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    @action(detail=False, methods=['get'])
    def por_vencer(self, request):
        """CU-87: Documentos por vencer en N días"""
        dias = int(request.query_params.get('dias', 30))
        docs = DocumentoService.documentos_por_vencer(dias)
        serializer = self.get_serializer(docs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def vencidos(self, request):
        """CU-87: Documentos vencidos"""
        docs = DocumentoService.documentos_vencidos()
        serializer = self.get_serializer(docs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def renovar(self, request, pk=None):
        """CU-88: Renovar un documento"""
        documento = self.get_object()
        nueva_fecha_emision = request.data.get('fecha_emision')
        nueva_fecha_vencimiento = request.data.get('fecha_vencimiento')

        if not nueva_fecha_emision or not nueva_fecha_vencimiento:
            return Response(
                {'error': 'Se requieren fecha_emision y fecha_vencimiento'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            fecha_emision = datetime.strptime(nueva_fecha_emision, '%Y-%m-%d').date()
            fecha_vencimiento = datetime.strptime(nueva_fecha_vencimiento, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        documento = DocumentoService.renovar_documento(
            documento,
            fecha_emision,
            fecha_vencimiento,
            usuario=request.user
        )
        serializer = self.get_serializer(documento)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def versiones(self, request, pk=None):
        """CU-89: Obtener versiones de un documento"""
        documento = self.get_object()
        versiones = documento.versiones.all().order_by('-numero_version')
        serializer = VersionDocumentoSerializer(versiones, many=True)
        return Response(serializer.data)


class VersionDocumentoViewSet(viewsets.ModelViewSet):
    """ViewSet para VersionDocumento (CU-92)"""
    queryset = VersionDocumento.objects.all()
    serializer_class = VersionDocumentoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)
