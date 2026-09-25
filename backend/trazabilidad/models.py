"""Modulo 9 - Trazabilidad, SINADER e indicador ambiental.

La Parte B materializa el indicador de CO2 evitado por recepcion y por pila.
Cada fila tiene exactamente uno de sus dos origenes y conserva el resultado
historico del calculo que alimenta el acumulado ambiental.
"""
from django.conf import settings
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


# --- Parte A: certificados y declaracion SINADER (CU-65 a CU-67) ------------


class CertificadoTrazabilidad(models.Model):
    """Certificado de trazabilidad entregable al cliente (CU-65 y CU-66).

    `contenido` guarda los datos compilados al momento de emitir (hecho
    historico: si despues cambia el cliente o la recepcion, el certificado
    emitido no se altera). Un certificado por descarga apunta a su
    `recepcion`; un consolidado mensual apunta al periodo y deja la recepcion
    nula. El `codigo` es el folio unico que se imprime en el documento.
    """

    DESCARGA = "descarga"
    CONSOLIDADO = "consolidado"
    TIPO_CHOICES = [(DESCARGA, "Descarga"), (CONSOLIDADO, "Consolidado")]

    tipo = models.CharField(max_length=11, choices=TIPO_CHOICES)
    cliente = models.ForeignKey(
        "mantenedores.Cliente",
        on_delete=models.PROTECT,
        related_name="certificados_trazabilidad",
    )
    recepcion = models.ForeignKey(
        "recepcion.Recepcion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="certificados_trazabilidad",
    )
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fin = models.DateField(null=True, blank=True)
    fecha_emision = models.DateField(auto_now_add=True)
    codigo = models.CharField(max_length=30, unique=True)
    contenido = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Certificado de trazabilidad"
        verbose_name_plural = "Certificados de trazabilidad"
        ordering = ["-fecha_emision", "-id"]
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(
                        tipo="descarga",
                        recepcion__isnull=False,
                        periodo_inicio__isnull=True,
                        periodo_fin__isnull=True,
                    )
                    | Q(
                        tipo="consolidado",
                        recepcion__isnull=True,
                        periodo_inicio__isnull=False,
                        periodo_fin__isnull=False,
                    )
                ),
                name="certificado_tipo_coherente",
            ),
        ]

    def __str__(self):
        return f"{self.codigo} ({self.get_tipo_display()}) - {self.cliente}"

    @classmethod
    def generar_codigo(cls, anio):
        """Folio correlativo por anio (CTR-2026-0001, CTR-2026-0002, ...).

        Si el correlativo propuesto ya existe por una generacion concurrente,
        avanza hasta encontrar uno libre; el folio nunca se reutiliza.
        """
        siguiente = cls.objects.filter(codigo__startswith=f"CTR-{anio}-").count() + 1
        while cls.objects.filter(codigo=f"CTR-{anio}-{siguiente:04d}").exists():
            siguiente += 1
        return f"CTR-{anio}-{siguiente:04d}"


class DeclaracionSinader(models.Model):
    """Declaracion del periodo para SINADER (CU-67).

    El sistema no se conecta con la plataforma de la autoridad: produce el
    `archivo` (planilla XLSX) que el administrador carga a mano. `contenido`
    conserva el resumen agrupado por cliente y la lista de clientes excluidos
    por datos incompletos, para mostrarlo sin reabrir la planilla.
    """

    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    fecha_generada = models.DateTimeField(auto_now_add=True)
    archivo = models.FileField(upload_to="sinader/")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="declaraciones_sinader",
    )
    contenido = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Declaracion SINADER"
        verbose_name_plural = "Declaraciones SINADER"
        ordering = ["-fecha_generada", "-id"]

    def __str__(self):
        return f"Declaracion SINADER {self.periodo_inicio} a {self.periodo_fin}"
