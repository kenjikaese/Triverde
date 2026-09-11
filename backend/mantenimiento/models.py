from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from mantenedores.models import Vehiculo


class Maquinaria(models.Model):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    ESTADO_CHOICES = [(ACTIVO, "Activo"), (INACTIVO, "Inactivo")]

    OPERATIVA = "operativa"
    EN_MANTENCION = "en mantencion"
    FUERA_DE_SERVICIO = "fuera de servicio"
    ESTADO_OPERATIVO_CHOICES = [
        (OPERATIVA, "Operativa"),
        (EN_MANTENCION, "En mantencion"),
        (FUERA_DE_SERVICIO, "Fuera de servicio"),
    ]

    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=80)
    datos_tecnicos = models.JSONField(default=dict, blank=True)
    horometro = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado_operativo = models.CharField(
        max_length=17, choices=ESTADO_OPERATIVO_CHOICES, default=OPERATIVA
    )
    estado = models.CharField(max_length=8, choices=ESTADO_CHOICES, default=ACTIVO)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Maquinaria"
        verbose_name_plural = "Maquinarias"

    def clean(self):
        if self.horometro < 0:
            raise ValidationError({"horometro": "El horometro no puede ser negativo."})

    def __str__(self):
        return self.nombre


class ActivoPolimorfico(models.Model):
    maquinaria = models.ForeignKey(
        Maquinaria, on_delete=models.PROTECT, null=True, blank=True,
        related_name="%(class)ss",
    )
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.PROTECT, null=True, blank=True,
        related_name="%(class)ss",
    )

    class Meta:
        abstract = True

    @property
    def activo(self):
        return self.maquinaria or self.vehiculo

    def clean(self):
        super().clean()
        if bool(self.maquinaria_id) == bool(self.vehiculo_id):
            raise ValidationError("Debe indicar exactamente una maquinaria o un vehiculo.")


class RegistroUso(ActivoPolimorfico):
    horas = models.DecimalField(max_digits=10, decimal_places=2)
    horas_transcurridas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha = models.DateTimeField()
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="registros_uso"
    )

    class Meta:
        ordering = ["-fecha", "-id"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(maquinaria__isnull=False, vehiculo__isnull=True)
                    | models.Q(maquinaria__isnull=True, vehiculo__isnull=False)
                ),
                name="registro_uso_un_activo",
            )
        ]

    def __str__(self):
        return f"{self.activo}: {self.horas} h"


class Mantencion(ActivoPolimorfico):
    PREVENTIVA = "preventiva"
    CORRECTIVA = "correctiva"
    TIPO_CHOICES = [(PREVENTIVA, "Preventiva"), (CORRECTIVA, "Correctiva")]

    POR_FECHA = "fecha"
    POR_HORAS = "horas"
    CRITERIO_CHOICES = [(POR_FECHA, "Por fecha"), (POR_HORAS, "Por horas")]

    PROGRAMADA = "programada"
    REALIZADA = "realizada"
    ESTADO_CHOICES = [(PROGRAMADA, "Programada"), (REALIZADA, "Realizada")]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    criterio = models.CharField(
        max_length=6, choices=CRITERIO_CHOICES, null=True, blank=True
    )
    umbral_horas = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    fecha_programada = models.DateField(null=True, blank=True)
    fecha_realizada = models.DateField(null=True, blank=True)
    costo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    descripcion = models.TextField()
    falla = models.TextField(blank=True, default="")
    reparacion = models.TextField(blank=True, default="")
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES)

    class Meta:
        ordering = ["-fecha_programada", "-fecha_realizada", "-id"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(maquinaria__isnull=False, vehiculo__isnull=True)
                    | models.Q(maquinaria__isnull=True, vehiculo__isnull=False)
                ),
                name="mantencion_un_activo",
            )
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.activo}"
