"""Modulo 7 - Proyecciones.

Un unico objeto `Proyeccion` (docs/11 Modelo de datos, Modulo 7) cubre los tres
tipos del modulo: proyeccion mensual de compost (CU-50), semanal por material
(CU-51) y rendimiento comercial de un camion (CU-52). `supuestos` guarda una
copia de los parametros usados al calcular, de modo que la proyeccion conserva
su escenario aunque despues cambien los parametros vigentes del sistema, y
CU-54 pueda ajustarlos sin tocar la configuracion global. `valor_proyectado`
guarda el resultado.
"""
from django.conf import settings
from django.db import models

from mantenedores.models import Material


class Proyeccion(models.Model):
    MENSUAL = "mensual"
    SEMANAL = "semanal"
    COMERCIAL = "comercial"
    TIPO_CHOICES = [
        (MENSUAL, "Mensual de compost"),
        (SEMANAL, "Semanal por material"),
        (COMERCIAL, "Rendimiento comercial"),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT, null=True, blank=True,
        related_name="proyecciones",
        help_text="Solo en proyecciones por material (semanal); nulo en las agregadas.",
    )
    supuestos = models.JSONField(
        default=dict,
        help_text="Copia de los parametros usados al calcular (volumen, densidad, "
        "factor, sacos/m3, precio). CU-54 edita esta copia sin tocar la config global.",
    )
    valor_proyectado = models.JSONField(
        default=dict, help_text="Resultado del calculo (toneladas/m3/sacos/ingreso)."
    )
    fecha_generada = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="proyecciones",
    )

    class Meta:
        verbose_name = "Proyeccion"
        verbose_name_plural = "Proyecciones"
        ordering = ["-fecha_generada"]

    def __str__(self):
        return f"Proyeccion {self.get_tipo_display()} ({self.periodo_inicio} - {self.periodo_fin})"
