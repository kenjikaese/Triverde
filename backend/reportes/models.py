"""Modelos del modulo Reportes y panel (CU-72 a CU-77)."""

from django.conf import settings
from django.db import models

from acceso.models import Usuario


class Reporte(models.Model):
    """Resultado agregado de una consulta del administrador."""
    RECEPCIONES = "recepciones"
    PRODUCCION = "produccion"
    VENTAS_COBROS = "ventas_cobros"
    TIPO_CHOICES = [
        (RECEPCIONES, "Recepciones"),
        (PRODUCCION, "Produccion"),
        (VENTAS_COBROS, "Ventas y cobros"),
    ]

    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    FORMATO_CHOICES = [
        (PDF, "PDF"),
        (EXCEL, "Excel"),
        (CSV, "CSV"),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    formato = models.CharField(max_length=10, choices=FORMATO_CHOICES, default=PDF)
    fecha_generado = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, related_name="reportes"
    )
    contenido = models.JSONField(default=dict)

    class Meta:
        ordering = ["-fecha_generado", "-id"]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.periodo_inicio} - {self.periodo_fin}"


class PanelControl(models.Model):
    """Preferencia de indicadores del panel de un administrador (CU-77).

    Uno por usuario; `indicadores_visibles` es la lista de claves de
    indicador activas (subconjunto de `services.INDICADORES_VALIDOS`).
    """

    DEFECTO = ["inventario", "produccion", "ventas"]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="panel_control"
    )
    indicadores_visibles = models.JSONField(default=list)
    configuracion = models.JSONField(default=dict, blank=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PanelControl({self.usuario})"
