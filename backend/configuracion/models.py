"""Modulo 2 - Configuracion (docs/11 SS11.6).
"""
from django.db import models, transaction
from django.utils import timezone

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


class RecetaMezcla(models.Model):
    """Receta de mezcla seca/verde para compostaje (M02 Incremento 2)."""

    nombre = models.CharField(max_length=100, unique=True)
    relacion_seca = models.DecimalField(max_digits=6, decimal_places=2)
    relacion_verde = models.DecimalField(max_digits=6, decimal_places=2)
    descripcion = models.CharField(max_length=200, blank=True)
    vigente = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Receta de mezcla"
        verbose_name_plural = "Recetas de mezcla"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(check=models.Q(relacion_seca__gt=0), name="receta_seca_positiva"),
            models.CheckConstraint(check=models.Q(relacion_verde__gt=0), name="receta_verde_positiva"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.proporcion})"

    @property
    def proporcion(self):
        return f"{self.relacion_seca.normalize()}:{self.relacion_verde.normalize()}"

    @property
    def fraccion_seca(self):
        return self.relacion_seca / (self.relacion_seca + self.relacion_verde)

    @property
    def fraccion_verde(self):
        return 1 - self.fraccion_seca


class CostoTransporteQuerySet(models.QuerySet):
    def vigente(self):
        return self.filter(vigente=True).order_by("-fecha").first()


class CostoTransporte(models.Model):

    costo_por_km = models.DecimalField(max_digits=12, decimal_places=2)
    vigente = models.BooleanField(default=True)
    fecha = models.DateTimeField(default=timezone.now)

    objects = CostoTransporteQuerySet.as_manager()

    class Meta:
        verbose_name = "Costo de transporte"
        verbose_name_plural = "Costos de transporte"
        ordering = ["-fecha"]
        constraints = [
            models.CheckConstraint(check=models.Q(costo_por_km__gt=0), name="costo_km_positivo"),
            models.UniqueConstraint(
                fields=["vigente"], condition=models.Q(vigente=True), name="costo_km_solo_un_vigente",
            ),
        ]

    def __str__(self):
        estado = "vigente" if self.vigente else "historico"
        return f"${self.costo_por_km}/km ({estado})"

    @classmethod
    def actualizar(cls, nuevo_valor):
        with transaction.atomic():
            actual = cls.objects.select_for_update().filter(vigente=True).first()
            if actual and actual.costo_por_km == nuevo_valor:
                return actual, None, False
            anterior = actual.costo_por_km if actual else None
            if actual:
                actual.vigente = False
                actual.save(update_fields=["vigente"])
            nuevo = cls.objects.create(costo_por_km=nuevo_valor)
            return nuevo, anterior, True


class CostoOperativo(models.Model):

    LITRO = "litro"
    HORA = "hora"
    DIA = "dia"
    VIAJE = "viaje"
    UNIDAD = "unidad"
    UNIDAD_CHOICES = [
        (LITRO, "Litro"),
        (HORA, "Hora"),
        (DIA, "Dia"),
        (VIAJE, "Viaje"),
        (UNIDAD, "Unidad"),
    ]

    concepto = models.CharField(max_length=100)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    unidad = models.CharField(max_length=10, choices=UNIDAD_CHOICES)
    vigente = models.BooleanField(default=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Costo operativo"
        verbose_name_plural = "Costos operativos"
        ordering = ["concepto"]
        constraints = [
            models.CheckConstraint(check=models.Q(monto__gt=0), name="costo_operativo_positivo"),
            models.UniqueConstraint(
                fields=["concepto"], condition=models.Q(vigente=True), name="costo_operativo_concepto_unico_vigente",
            ),
        ]

    def __str__(self):
        return f"{self.concepto}: ${self.monto}/{self.get_unidad_display()}"
