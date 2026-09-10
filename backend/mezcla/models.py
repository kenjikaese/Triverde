from django.conf import settings
from django.db import models


class Alerta(models.Model):
    MEZCLA = "mezcla"
    MANTENCION = "mantencion"
    DOCUMENTO = "documento"
    ORIGEN_CHOICES = [
        (MEZCLA, "Mezcla"),
        (MANTENCION, "Mantencion"),
        (DOCUMENTO, "Documento"),
    ]

    INFORMATIVA = "informativa"
    ADVERTENCIA = "advertencia"
    CRITICA = "critica"
    NIVEL_CHOICES = [
        (INFORMATIVA, "Informativa"),
        (ADVERTENCIA, "Advertencia"),
        (CRITICA, "Critica"),
    ]

    ACTIVA = "activa"
    RESUELTA = "resuelta"
    ESTADO_CHOICES = [(ACTIVA, "Activa"), (RESUELTA, "Resuelta")]

    origen = models.CharField(max_length=12, choices=ORIGEN_CHOICES)
    clave = models.CharField(
        max_length=160,
        help_text=(
            "Identificador estable para no duplicar alertas. Ejemplos: "
            "mantencion:15 o mezcla:pila:8:seca."
        ),
    )
    nivel = models.CharField(max_length=12, choices=NIVEL_CHOICES)
    estado = models.CharField(max_length=9, choices=ESTADO_CHOICES, default=ACTIVA)
    mensaje = models.TextField()
    fecha_generada = models.DateTimeField(auto_now_add=True)
    fecha_resuelta = models.DateTimeField(null=True, blank=True)
    resuelta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="alertas_resueltas",
    )
    mantencion = models.ForeignKey(
        "mantenimiento.Mantencion", on_delete=models.CASCADE, null=True, blank=True,
        related_name="alertas",
    )

    class Meta:
        ordering = ["-fecha_generada"]
        constraints = [
            models.UniqueConstraint(
                fields=["origen", "clave"],
                condition=models.Q(estado="activa"),
                name="alerta_activa_origen_clave_unica",
            ),
            models.UniqueConstraint(
                fields=["mantencion"],
                condition=models.Q(estado="activa", origen="mantencion"),
                name="alerta_mantencion_activa_unica",
            )
        ]

    def __str__(self):
        return self.mensaje
