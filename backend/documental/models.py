from django.db import models
from django.conf import settings
from django.utils import timezone


class DocumentoLegal(models.Model):
    """
    Documento legal con vigencia y versionado.
    Cubre CU-86, CU-87, CU-88, CU-89.
    """
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=50)  # permiso, certificado, resolucion
    descripcion = models.TextField(blank=True)
    archivo = models.FileField(upload_to='documentos/', null=True, blank=True)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, default='activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'documentos_legales'
        ordering = ['-fecha_creacion']
        verbose_name = 'Documento Legal'
        verbose_name_plural = 'Documentos Legales'

    def __str__(self):
        return self.nombre

    @property
    def esta_vencido(self):
        if self.fecha_vencimiento:
            return self.fecha_vencimiento < timezone.now().date()
        return False


class VersionDocumento(models.Model):
    """
    Historial de versiones de un documento.
    Cubre CU-92 (Parte F de Ignacio).
    """
    documento = models.ForeignKey(
        DocumentoLegal,
        on_delete=models.CASCADE,
        related_name='versiones'
    )
    numero_version = models.IntegerField()
    archivo = models.FileField(upload_to='documentos/versiones/', null=True, blank=True)
    cambios = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'versiones_documento'
        ordering = ['-numero_version']
        unique_together = ['documento', 'numero_version']
        verbose_name = 'Versión de Documento'
        verbose_name_plural = 'Versiones de Documento'

    def __str__(self):
        return f"{self.documento.nombre} v{self.numero_version}"
