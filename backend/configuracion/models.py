"""Modulo 2 - Configuracion (docs/11 SS11.6).

Parametriza el sistema sin programar. El historial conserva los cambios de
parametros (auditoria de configuracion).
"""
from django.db import models

from acceso.models import Usuario


class ParametroConversion(models.Model):
    """Parametro global (sacos/m3, rendimiento, CO2, factores de reduccion)."""

    clave = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=12, decimal_places=4)
    unidad = models.CharField(max_length=20, null=True, blank=True)
    descripcion = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        verbose_name = "Parametro de conversion"
        verbose_name_plural = "Parametros de conversion"
        ordering = ["clave"]

    def __str__(self):
        return f"{self.clave} = {self.valor} {self.unidad or ''}".strip()


class TarifaRecepcion(models.Model):
    """Tarifa por tramo de camion (m3)."""

    tramo_min_m3 = models.DecimalField(max_digits=6, decimal_places=2)
    tramo_max_m3 = models.DecimalField(max_digits=6, decimal_places=2)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tarifa de recepcion"
        verbose_name_plural = "Tarifas de recepcion"
        ordering = ["tramo_min_m3"]

    def __str__(self):
        return f"{self.tramo_min_m3}-{self.tramo_max_m3} m3: ${self.monto}"


class HistorialCambioParametro(models.Model):
    """Historial de cambios de un parametro de conversion."""

    parametro = models.ForeignKey(
        ParametroConversion, on_delete=models.CASCADE, related_name="historial"
    )
    usuario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cambios_parametro",
    )
    valor_anterior = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    valor_nuevo = models.DecimalField(max_digits=12, decimal_places=4)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cambio de parametro"
        verbose_name_plural = "Historial de cambios de parametro"
        ordering = ["-fecha_hora"]

    def __str__(self):
        return f"{self.parametro.clave}: {self.valor_anterior} -> {self.valor_nuevo}"
