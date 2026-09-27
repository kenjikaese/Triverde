"""Modulo 12 - Gestion documental (CU-86 a CU-92).

- `DocumentoLegal`: permiso, certificado, resolucion o seguro de la empresa, con
  su vigencia y un `estado` derivado de ella (CU-86 y CU-88).
- `VersionDocumento`: cada archivo adjunto del documento. Solo una por documento
  es la vigente; las anteriores se conservan como historial (CU-87 y CU-89) junto
  con la vigencia que tenia el documento al cargarlas.

Los documentos legales no se eliminan: son evidencia de cumplimiento. Por eso
las versiones protegen a su documento y la API no expone el borrado.
"""
from django.conf import settings
from django.db import models
from django.db.models import F, Q


class DocumentoLegal(models.Model):
    PERMISO = "permiso"
    CERTIFICADO = "certificado"
    RESOLUCION = "resolucion"
    SEGURO = "seguro"
    OTRO = "otro"
    TIPO_CHOICES = [
        (PERMISO, "Permiso"),
        (CERTIFICADO, "Certificado"),
        (RESOLUCION, "Resolucion"),
        (SEGURO, "Seguro"),
        (OTRO, "Otro"),
    ]

    SIN_VIGENCIA = "sin_vigencia"
    VIGENTE = "vigente"
    POR_VENCER = "por_vencer"
    VENCIDO = "vencido"
    ESTADO_CHOICES = [
        (SIN_VIGENCIA, "Sin vigencia registrada"),
        (VIGENTE, "Vigente"),
        (POR_VENCER, "Por vencer"),
        (VENCIDO, "Vencido"),
    ]

    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES, default=OTRO)
    # CU-86, Excepcion 1: una clasificacion fuera de las predefinidas se registra
    # como "otro" con su descripcion libre.
    tipo_detalle = models.CharField(max_length=100, blank=True)
    entidad_emisora = models.CharField(max_length=200)
    fecha_emision = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=12, choices=ESTADO_CHOICES, default=SIN_VIGENCIA, db_index=True
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento legal"
        verbose_name_plural = "Documentos legales"
        ordering = ["nombre", "id"]
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(fecha_emision__isnull=True)
                    | Q(fecha_vencimiento__isnull=True)
                    | Q(fecha_vencimiento__gte=F("fecha_emision"))
                ),
                name="documentolegal_vencimiento_posterior_a_emision",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.entidad_emisora})"

    def version_vigente(self):
        return self.versiones.filter(vigente=True).first()


class VersionDocumento(models.Model):
    documento = models.ForeignKey(
        DocumentoLegal, on_delete=models.PROTECT, related_name="versiones"
    )
    archivo = models.FileField(upload_to="documentos/%Y/")
    nombre_archivo = models.CharField(max_length=255)
    version = models.PositiveIntegerField()
    fecha_carga = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="versiones_documento",
    )
    vigente = models.BooleanField(default=True)
    # Vigencia del documento con la que se cargo esta version: conserva el
    # historial de vigencias al renovar (CU-89).
    fecha_emision = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Version de documento"
        verbose_name_plural = "Versiones de documento"
        ordering = ["documento", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["documento", "version"],
                name="versiondocumento_version_unica",
            ),
            models.UniqueConstraint(
                fields=["documento"],
                condition=Q(vigente=True),
                name="versiondocumento_una_vigente_por_documento",
            ),
        ]

    def __str__(self):
        return f"{self.documento.nombre} v{self.version}"
