"""Modulo 4 - Recepcion (docs/11 SS11.6).

El ciclo central del sistema. La Recepcion y sus partes (DetalleRecepcion,
FotoRecepcion, Multa) son objetos de la capa offline: heredan `id_local` y
`estado_sincronizacion` de SincronizableModel (docs/11 Decision 2). Sus partes
usan CASCADE porque son composicion (docs/11 Decision 4); las FK hacia
catalogos usan PROTECT/SET_NULL (baja logica).
"""
from django.db import models

from common.models import SincronizableModel
from acceso.models import Usuario
from mantenedores.models import Cliente, Material, Transportista, Vehiculo


class Recepcion(SincronizableModel):
    """Cabecera de la descarga de un camion."""

    EN_CURSO = "en curso"
    PENDIENTE_INSPECCION = "pendiente de inspeccion"
    RECIBIDA = "recibida"
    RECHAZADA = "rechazada"
    ESTADO_CHOICES = [
        (EN_CURSO, "En curso"),
        (PENDIENTE_INSPECCION, "Pendiente de inspeccion"),
        (RECIBIDA, "Recibida"),
        (RECHAZADA, "Rechazada"),
    ]

    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="recepciones"
    )
    transportista = models.ForeignKey(
        Transportista, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="recepciones",
    )
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="recepciones",
    )
    operador = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="recepciones_operadas",
    )
    conductor = models.CharField(max_length=120, null=True, blank=True)
    fecha = models.DateField()
    hora = models.TimeField()
    estado = models.CharField(
        max_length=24, choices=ESTADO_CHOICES, default=EN_CURSO
    )
    motivo_rechazo = models.CharField(max_length=200, null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Recepcion"
        verbose_name_plural = "Recepciones"
        ordering = ["-fecha", "-hora"]

    def __str__(self):
        return f"Recepcion #{self.pk} - {self.cliente} ({self.fecha})"


class DetalleRecepcion(SincronizableModel):
    """Linea material+volumen de una recepcion (N por recepcion)."""

    A_PILA = "a pila"
    A_CHIP = "a chip"
    A_VENTA_DIRECTA = "a venta directa"
    DESTINO_CHOICES = [
        (A_PILA, "A pila"),
        (A_CHIP, "A chip"),
        (A_VENTA_DIRECTA, "A venta directa"),
    ]

    recepcion = models.ForeignKey(
        Recepcion, on_delete=models.CASCADE, related_name="detalles"
    )
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT, related_name="detalles_recepcion"
    )
    volumen_m3 = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text="Unico dato tecleado; no hay balanza (R2).",
    )
    peso_derivado_kg = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Derivado (volumen x densidad) y persistido como hecho historico (docs/11 Decision 1).",
    )
    chip_derivado_m3 = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    destino_sugerido = models.CharField(
        max_length=16, choices=DESTINO_CHOICES, null=True, blank=True
    )

    class Meta:
        verbose_name = "Detalle de recepcion"
        verbose_name_plural = "Detalles de recepcion"

    def __str__(self):
        return f"{self.material} - {self.volumen_m3} m3"


class FotoRecepcion(SincronizableModel):
    """Foto de respaldo de una recepcion (N por recepcion)."""

    recepcion = models.ForeignKey(
        Recepcion, on_delete=models.CASCADE, related_name="fotos"
    )
    archivo = models.ImageField(upload_to="recepciones/%Y/%m/")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Foto de recepcion"
        verbose_name_plural = "Fotos de recepcion"

    def __str__(self):
        return f"Foto de recepcion #{self.recepcion_id}"


class Multa(SincronizableModel):
    """Multa por material contaminado (1:1 sobre el volumen, docs/02)."""

    recepcion = models.ForeignKey(
        Recepcion, on_delete=models.CASCADE, related_name="multas"
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="multas"
    )
    motivo = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()

    class Meta:
        verbose_name = "Multa"
        verbose_name_plural = "Multas"
        ordering = ["-fecha"]

    def __str__(self):
        return f"Multa {self.cliente} - ${self.monto}"
