from django.utils import timezone
from datetime import timedelta
from .models import DocumentoLegal, VersionDocumento
import logging

logger = logging.getLogger(__name__)


class DocumentoService:
    """Servicio para gestión documental - CU-86 a CU-89"""

    @classmethod
    def documentos_por_vencer(cls, dias=30):
        hoy = timezone.now().date()
        limite = hoy + timedelta(days=dias)
        return DocumentoLegal.objects.filter(
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=limite,
            estado='activo'
        ).order_by('fecha_vencimiento')

    @classmethod
    def documentos_vencidos(cls):
        hoy = timezone.now().date()
        return DocumentoLegal.objects.filter(
            fecha_vencimiento__lt=hoy,
            estado='activo'
        ).order_by('fecha_vencimiento')

    @classmethod
    def renovar_documento(cls, documento, nueva_fecha_emision, nueva_fecha_vencimiento, usuario=None):
        ultima_version = documento.versiones.first()
        numero = (ultima_version.numero_version + 1) if ultima_version else 1

        VersionDocumento.objects.create(
            documento=documento,
            numero_version=numero,
            archivo=documento.archivo,
            cambios=f"Renovación: {documento.fecha_emision} → {nueva_fecha_emision}",
            creado_por=usuario
        )

        documento.fecha_emision = nueva_fecha_emision
        documento.fecha_vencimiento = nueva_fecha_vencimiento
        documento.estado = 'activo'
        documento.save()

        return documento

    @classmethod
    def documentos_con_versiones(cls, documento_id):
        try:
            documento = DocumentoLegal.objects.get(id=documento_id)
            return {
                'documento': documento,
                'versiones': documento.versiones.all().order_by('-numero_version')
            }
        except DocumentoLegal.DoesNotExist:
            return None
