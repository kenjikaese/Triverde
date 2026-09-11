"""Modulo 5 - Inventario, pilas y procesos (docs/11 SS11.6, CU-34 a CU-44).

Tres objetos y un libro mayor:

- `Pila`: el lote de compostaje, con su ciclo de vida en formacion -> en
  proceso -> en reposo -> cerrada (CU-35, CU-41, CU-42).
- `ComposicionPila`: que material y cuanto entro a cada pila (CU-36).
- `ProcesoPila`: cada movimiento aplicado -triturado, volteo, riego, harneado,
  reposo, ensacado- (CU-37 a CU-42). Hereda de `SincronizableModel` porque el
  operador los registra en el patio, donde no siempre hay senal.
- `Inventario`: el saldo por material y etapa. No se edita a mano: lo mueve
  siempre `inventario/services.py` (CU-44).

Los catalogos se referencian con PROTECT (baja logica, docs/11 Decision 3); las
partes de una pila usan CASCADE porque son composicion (docs/11 Decision 4).
"""
from decimal import Decimal

from django.db import models

from acceso.models import Usuario
from common.models import SincronizableModel
from mantenedores.models import Material

CERO = Decimal("0.00")


class Pila(models.Model):
    """Lote de compostaje (CU-35).

    El `codigo` es el identificador que usa el operador en el patio; se propone
    correlativo al abrir el formulario y es unico.
    """

    EN_FORMACION = "en formacion"
    EN_PROCESO = "en proceso"
    EN_REPOSO = "en reposo"
    CERRADA = "cerrada"
    ESTADO_CHOICES = [
        (EN_FORMACION, "En formacion"),
        (EN_PROCESO, "En proceso"),
        (EN_REPOSO, "En reposo"),
        (CERRADA, "Cerrada"),
    ]

    codigo = models.CharField(max_length=30, unique=True)
    fecha_inicio = models.DateField()
    estado = models.CharField(
        max_length=16, choices=ESTADO_CHOICES, default=EN_FORMACION
    )
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Pila"
        verbose_name_plural = "Pilas"
        ordering = ["-fecha_inicio", "-id"]

    def __str__(self):
        return self.codigo

    @classmethod
    def generar_codigo(cls):
        """Propone el siguiente codigo correlativo (P-0001, P-0002, ...).

        CU-35 Excepcion 1: si el correlativo propuesto ya existe por un
        conflicto de generacion, avanza hasta encontrar uno libre sin
        intervencion del operador.
        """
        ultima = cls.objects.order_by("-id").first()
        siguiente = (ultima.id + 1) if ultima else 1
        while cls.objects.filter(codigo=f"P-{siguiente:04d}").exists():
            siguiente += 1
        return f"P-{siguiente:04d}"

    def volumen_composicion(self):
        """Volumen total incorporado a la pila (suma de su composicion)."""
        total = self.composiciones.aggregate(total=models.Sum("volumen_m3"))["total"]
        return total or CERO

    def volumen_ensacado(self):
        """Volumen ya ensacado desde esta pila (CU-42)."""
        total = self.procesos.filter(tipo=ProcesoPila.ENSACADO).aggregate(
            total=models.Sum("volumen_m3")
        )["total"]
        return total or CERO

    def volumen_curado_disponible(self):
        """Material curado de esta pila que aun no se ensaca (CU-42 Excepcion 2).

        El Inventario lleva el saldo global por material y etapa; el saldo
        *por pila* se deriva de sus propios registros: lo que entro menos lo
        que ya salio ensacado.
        """
        return self.volumen_composicion() - self.volumen_ensacado()


class ComposicionPila(models.Model):
    """Material que entra a una pila y en que cantidad (CU-36).

    Un material aparece una sola vez por pila: si el operador lo agrega de
    nuevo, se suma al registro existente (CU-36 Excepcion 2).
    """

    pila = models.ForeignKey(
        Pila, on_delete=models.CASCADE, related_name="composiciones"
    )
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT, related_name="composiciones_pila"
    )
    volumen_m3 = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = "Composicion de pila"
        verbose_name_plural = "Composicion de pilas"
        ordering = ["pila", "material"]
        constraints = [
            models.UniqueConstraint(
                fields=["pila", "material"], name="composicionpila_unica_por_material"
            )
        ]

    def __str__(self):
        return f"{self.pila} - {self.material} ({self.volumen_m3} m3)"


class ProcesoPila(SincronizableModel):
    """Movimiento aplicado a la planta o a una pila (CU-37 a CU-42).

    `pila` va nulo en el triturado, que ocurre antes de que exista una pila.
    `material` solo lo trae el triturado: en los procesos de pila el material
    se deduce de su composicion.
    """

    TRITURADO = "triturado"
    VOLTEO = "volteo"
    RIEGO = "riego"
    HARNEADO = "harneado"
    REPOSO = "reposo"
    ENSACADO = "ensacado"
    TIPO_CHOICES = [
        (TRITURADO, "Triturado"),
        (VOLTEO, "Volteo"),
        (RIEGO, "Riego"),
        (HARNEADO, "Harneado"),
        (REPOSO, "Reposo"),
        (ENSACADO, "Ensacado"),
    ]

    pila = models.ForeignKey(
        Pila, on_delete=models.CASCADE, null=True, blank=True,
        related_name="procesos",
    )
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT, null=True, blank=True,
        related_name="procesos_pila",
        help_text="Solo en el triturado (CU-37); el resto lo deduce de la pila.",
    )
    operador = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="procesos_registrados",
    )
    tipo = models.CharField(max_length=16, choices=TIPO_CHOICES)
    fecha = models.DateTimeField()
    temperatura = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    humedad = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    volumen_m3 = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    chip_pendiente = models.BooleanField(
        default=False,
        help_text="Triturado sin factor de reduccion configurado (CU-37 Excepcion 3).",
    )
    advertencia = models.CharField(
        max_length=200, null=True, blank=True,
        help_text="Observacion del sistema, p. ej. temperatura sobre el techo (CU-38 Excepcion 2).",
    )

    class Meta:
        verbose_name = "Proceso de pila"
        verbose_name_plural = "Procesos de pila"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        destino = self.pila or self.material or "planta"
        return f"{self.get_tipo_display()} - {destino} ({self.fecha:%Y-%m-%d})"


class Inventario(models.Model):
    """Saldo de material por etapa del proceso (CU-34).

    Es un libro mayor derivado: nace de las recepciones y lo mueven los
    procesos. Nunca se edita a mano; ver `inventario/services.py` (CU-44).
    """

    POR_TRITURAR = "por triturar"
    CHIP = "chip"
    PILA_EN_PROCESO = "pila en proceso"
    CURADO = "curado"
    ENSACADO = "ensacado"
    ETAPA_CHOICES = [
        (POR_TRITURAR, "Por triturar"),
        (CHIP, "Chip"),
        (PILA_EN_PROCESO, "Pila en proceso"),
        (CURADO, "Curado"),
        (ENSACADO, "Ensacado"),
    ]

    material = models.ForeignKey(
        Material, on_delete=models.PROTECT, related_name="existencias"
    )
    etapa = models.CharField(max_length=20, choices=ETAPA_CHOICES)
    volumen_m3 = models.DecimalField(
        max_digits=10, decimal_places=2, default=CERO
    )
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Existencia de inventario"
        verbose_name_plural = "Inventario"
        ordering = ["material__nombre", "etapa"]
        constraints = [
            models.UniqueConstraint(
                fields=["material", "etapa"], name="inventario_unico_material_etapa"
            )
        ]

    def __str__(self):
        return f"{self.material} en {self.etapa}: {self.volumen_m3} m3"
