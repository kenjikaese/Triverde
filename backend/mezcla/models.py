"""Modelos del modulo 6: mezcla objetivo y alertas (CU-45 a CU-49).

`Alerta` es un objeto compartido: el modulo 6 genera alertas de mezcla y el
modulo 11 (mantenimiento) reutiliza el mismo objeto para sus propias alertas.
La deduplicacion se apoya en la ``clave`` estable de cada origen; los campos
propios de mezcla (pila, categoria, faltante y disponible) quedan nulos cuando
la alerta proviene de otro origen.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Alerta(models.Model):
    """Aviso operativo que puede estar activo o quedar resuelto (CU-46/49).

    Las alertas de mezcla apuntan a una pila y categoria; las de mantencion
    apuntan a la mantencion de origen. La restriccion unica por ``origen`` y
    ``clave`` evita que un recalculo genere duplicados de la misma alerta.
    """

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

    SECA = "seca"
    VERDE = "verde"
    CATEGORIA_CHOICES = [(SECA, "Seca"), (VERDE, "Verde")]

    # --- Campos genericos (compartidos por todos los origenes) ---
    origen = models.CharField(max_length=12, choices=ORIGEN_CHOICES)
    clave = models.CharField(
        max_length=160,
        blank=True,
        help_text=(
            "Identificador estable para no duplicar alertas. Ejemplos: "
            "mantencion:15 o mezcla:pila:8:seca."
        ),
    )
    nivel = models.CharField(max_length=20)
    estado = models.CharField(max_length=9, choices=ESTADO_CHOICES, default=ACTIVA)
    mensaje = models.TextField()
    fecha_generada = models.DateTimeField(auto_now_add=True)
    fecha_resuelta = models.DateTimeField(null=True, blank=True)
    resuelta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="alertas_resueltas",
    )

    # --- Origen mantencion (Modulo 11) ---
    mantencion = models.ForeignKey(
        "mantenimiento.Mantencion", on_delete=models.CASCADE, null=True, blank=True,
        related_name="alertas",
    )

    # --- Origen mezcla (Modulo 6) ---
    categoria = models.CharField(
        max_length=6, choices=CATEGORIA_CHOICES, null=True, blank=True
    )
    faltante_m3 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    disponible_m3 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pila = models.ForeignKey(
        "inventario.Pila", on_delete=models.CASCADE, null=True, blank=True,
        related_name="alertas",
    )

    # --- Origen documento (Modulo 12 - Parte F / Ignacio) ---
    documento = models.ForeignKey(
        "documental.DocumentoLegal", on_delete=models.CASCADE, null=True, blank=True,
        related_name="alertas",
    )

    class Meta:
        ordering = ["-fecha_generada", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["origen", "clave"],
                condition=models.Q(estado="activa") & ~models.Q(clave=""),
                name="alerta_activa_origen_clave_unica",
            ),
            models.UniqueConstraint(
                fields=["mantencion"],
                condition=models.Q(estado="activa", origen="mantencion"),
                name="alerta_mantencion_activa_unica",
            ),
            models.UniqueConstraint(
                fields=["pila", "categoria"],
                condition=models.Q(origen="mezcla", estado="activa"),
                name="alerta_mezcla_activa_pila_categoria_unica",
            ),
            models.UniqueConstraint(
                fields=["documento"],
                condition=models.Q(origen="documento", estado="activa"),
                name="alerta_documento_activa_unica",
            ),
        ]

    def __str__(self):
        return self.mensaje

    def resolver(self, usuario=None):
        """Marca la alerta como resuelta y conserva quien la atendio."""
        self.estado = self.RESUELTA
        self.fecha_resuelta = timezone.now()
        self.resuelta_por = usuario
        self.save(update_fields=["estado", "fecha_resuelta", "resuelta_por"])
