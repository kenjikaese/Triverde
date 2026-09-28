"""Modelo persistente de los reportes generados (CU-73 a CU-76)."""

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
