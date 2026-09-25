"""Modulo 9 - Trazabilidad, SINADER e indicador ambiental.

La Parte B materializa el indicador de CO2 evitado por recepcion y por pila.
Cada fila tiene exactamente uno de sus dos origenes y conserva el resultado
historico del calculo que alimenta el acumulado ambiental.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class IndicadorAmbiental(models.Model):
    RECEPCION = "recepcion"
    PILA = "pila"
    ORIGEN_CHOICES = [
        (RECEPCION, "Recepcion"),
        (PILA, "Pila"),
    ]

    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES)
    recepcion = models.ForeignKey(
        "recepcion.Recepcion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="indicadores_ambientales",
    )
    pila = models.ForeignKey(
        "inventario.Pila",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="indicadores_ambientales",
    )
    co2_evitado_kg = models.DecimalField(max_digits=14, decimal_places=2)
    metodo = models.CharField(max_length=200)
    fecha = models.DateField(db_index=True)

    class Meta:
        verbose_name = "Indicador ambiental"
        verbose_name_plural = "Indicadores ambientales"
        ordering = ["-fecha", "-id"]
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(origen="recepcion", recepcion__isnull=False, pila__isnull=True)
                    | Q(origen="pila", recepcion__isnull=True, pila__isnull=False)
                ),
                name="indicador_ambiental_origen_excluyente",
            ),
            models.UniqueConstraint(
                fields=["recepcion"],
                condition=Q(recepcion__isnull=False),
                name="indicador_ambiental_recepcion_unica",
            ),
            models.UniqueConstraint(
                fields=["pila"],
                condition=Q(pila__isnull=False),
                name="indicador_ambiental_pila_unica",
            ),
        ]

    def clean(self):
        super().clean()
        recepcion_valida = (
            self.origen == self.RECEPCION
            and self.recepcion_id is not None
            and self.pila_id is None
        )
        pila_valida = (
            self.origen == self.PILA
            and self.pila_id is not None
            and self.recepcion_id is None
        )
        if not (recepcion_valida or pila_valida):
            raise ValidationError(
                "El indicador debe vincular exactamente una recepcion o una pila "
                "coherente con su origen."
            )

    def __str__(self):
        referencia = self.recepcion or self.pila
        return f"{self.get_origen_display()} {referencia}: {self.co2_evitado_kg} kg CO2e"
