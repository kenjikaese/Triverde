"""Modelos del modulo 6: mezcla objetivo y alertas (CU-45 a CU-49).

`Alerta` es generica a proposito: este modulo crea alertas de mezcla y el
modulo de mantencion podra reutilizar el mismo objeto para sus propias alertas.
"""
from django.db import models
from django.utils import timezone

from acceso.models import Usuario
from inventario.models import Pila


class Alerta(models.Model):
    """Aviso operativo que puede estar activo o quedar resuelto (CU-46/49).

    Las alertas de mezcla apuntan a una pila y categoria. La restriccion unica
    evita que un recalculo cree duplicados para la misma pila y categoria.
    """

    MEZCLA = "mezcla"
    MANTENCION = "mantencion"
    DOCUMENTO = "documento"
    ORIGEN_CHOICES = [
        (MEZCLA, "Mezcla"),
        (MANTENCION, "Mantencion"),
        (DOCUMENTO, "Documento"),
    ]

    ACTIVA = "activa"
    RESUELTA = "resuelta"
    ESTADO_CHOICES = [(ACTIVA, "Activa"), (RESUELTA, "Resuelta")]

    SECA = "seca"
    VERDE = "verde"
    CATEGORIA_CHOICES = [(SECA, "Seca"), (VERDE, "Verde")]

    origen = models.CharField(max_length=12, choices=ORIGEN_CHOICES)
    nivel = models.CharField(max_length=20, default="faltante")
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=ACTIVA)
    mensaje = models.CharField(max_length=240)
    categoria = models.CharField(max_length=6, choices=CATEGORIA_CHOICES, null=True, blank=True)
    faltante_m3 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    disponible_m3 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_generada = models.DateTimeField(auto_now_add=True)
    fecha_resuelta = models.DateTimeField(null=True, blank=True)
    pila = models.ForeignKey(
        Pila, on_delete=models.CASCADE, null=True, blank=True, related_name="alertas"
    )
    mantencion = models.IntegerField(null=True, blank=True)
    resuelta_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="alertas_resueltas",
    )

    class Meta:
        ordering = ["-fecha_generada", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["pila", "categoria"],
                condition=models.Q(origen="mezcla", estado="activa"),
                name="alerta_mezcla_activa_pila_categoria_unica",
            )
        ]

    def resolver(self, usuario=None):
        """Marca la alerta como resuelta y conserva quien la atendio."""
        self.estado = self.RESUELTA
        self.fecha_resuelta = timezone.now()
        self.resuelta_por = usuario
        self.save(update_fields=["estado", "fecha_resuelta", "resuelta_por"])
