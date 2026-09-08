from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ProyeccionSemanal, ProyeccionMensual
from .serializers import (
    ProyeccionSemanalSerializer,
    ProyeccionMensualSerializer,
    RendimientoCamionSerializer
)
from .services import ProyeccionService

class ProyeccionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def semanal(self, request):
        semanas = int(request.query_params.get('semanas', 4))
        proyecciones = ProyeccionService.proyectar_semanal(semanas)
        serializer = ProyeccionSemanalSerializer(proyecciones, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def mensual(self, request):
        meses = int(request.query_params.get('meses', 6))
        proyecciones = ProyeccionService.proyectar_mensual(meses)
        serializer = ProyeccionMensualSerializer(proyecciones, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='rendimiento-camion/(?P<camion_id>[0-9]+)')
    def rendimiento_camion(self, request, camion_id=None):
        meses = int(request.query_params.get('meses', 3))
        resultado = ProyeccionService.rendimiento_camion(camion_id, meses)
        
        if resultado is None:
            return Response(
                {'error': f'Camión ID {camion_id} no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = RendimientoCamionSerializer(resultado)
        return Response(serializer.data)
