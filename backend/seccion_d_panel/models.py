from django.conf import settings
from django.db import models


class PanelControl(models.Model):
    DEFECTO = ["inventario", "produccion", "ventas"]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="panel_control"
    )
    indicadores_visibles = models.JSONField(default=list)
    configuracion = models.JSONField(default=dict, blank=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PanelControl({self.usuario})"
