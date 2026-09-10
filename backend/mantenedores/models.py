"""Modulo 3 - Mantenedores (docs/11 SS11.6).

Todos los mantenedores usan baja logica (`estado = inactivo`, docs/11 Decision 3):
no se borran, se desactivan; por eso las FK hacia ellos usan PROTECT o SET_NULL.
"""
from django.db import models

from acceso.models import Usuario


class Cliente(models.Model):
    """Empresa/generador que descarga material."""

    ACTIVO = "activo"
    INACTIVO = "inactivo"
    ESTADO_CHOICES = [(ACTIVO, "Activo"), (INACTIVO, "Inactivo")]

    AL_DIA = "al dia"
    CON_DEUDA = "con deuda"
    ESTADO_PAGO_CHOICES = [(AL_DIA, "Al dia"), (CON_DEUDA, "Con deuda")]

    razon_social = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    nombre_contacto = models.CharField(max_length=120, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    direccion = models.CharField(max_length=200, null=True, blank=True)
    estado_pago = models.CharField(
        max_length=10, choices=ESTADO_PAGO_CHOICES, default=AL_DIA
    )
    estado = models.CharField(max_length=8, choices=ESTADO_CHOICES, default=ACTIVO)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["razon_social"]

    def __str__(self):
        return self.razon_social


class Transportista(models.Model):
    """Camionero/arborista, puede tener cuenta propia (CU-28)."""

    ACTIVO = "activo"
    INACTIVO = "inactivo"
    ESTADO_CHOICES = [(ACTIVO, "Activo"), (INACTIVO, "Inactivo")]

    nombre = models.CharField(max_length=120)
    rut = models.CharField(max_length=12, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="transportistas"
    )
    usuario = models.OneToOneField(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transportista",
    )
    estado = models.CharField(max_length=8, choices=ESTADO_CHOICES, default=ACTIVO)

    class Meta:
        verbose_name = "Transportista"
        verbose_name_plural = "Transportistas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Vehiculo(models.Model):
    """Camion (patente, tramo). Tambien es activo mantenible (M11)."""

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

    patente = models.CharField(max_length=10, unique=True)
    cliente = models.ForeignKey(
        Cliente, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="vehiculos",
    )
    capacidad_m3 = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    tramo = models.CharField(max_length=20, null=True, blank=True)
    descripcion = models.CharField(max_length=120, null=True, blank=True)
    es_mantenible = models.BooleanField(default=False)
    datos_tecnicos = models.JSONField(default=dict, blank=True)
    horometro = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado_operativo = models.CharField(
        max_length=17, choices=ESTADO_OPERATIVO_CHOICES, default=OPERATIVA
    )
    estado = models.CharField(max_length=8, choices=ESTADO_CHOICES, default=ACTIVO)

    class Meta:
        verbose_name = "Vehiculo"
        verbose_name_plural = "Vehiculos"
        ordering = ["patente"]

    def __str__(self):
        return self.patente


class Material(models.Model):
    """Tipo de material con parametros de conversion."""

    ACTIVO = "activo"
    INACTIVO = "inactivo"
    ESTADO_CHOICES = [(ACTIVO, "Activo"), (INACTIVO, "Inactivo")]

    SECA = "seca"
    VERDE = "verde"
    CATEGORIA_CHOICES = [(SECA, "Seca"), (VERDE, "Verde")]

    nombre = models.CharField(max_length=80, unique=True)
    categoria = models.CharField(
        max_length=6, choices=CATEGORIA_CHOICES, null=True, blank=True,
        help_text="Seca/verde. Pendiente de confirmar con Javier.",
    )
    densidad_kg_m3 = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    factor_reduccion_chip = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    admite_chip = models.BooleanField(default=False)
    estado = models.CharField(max_length=8, choices=ESTADO_CHOICES, default=ACTIVO)

    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materiales"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Producto vendible (chip, mulch, compost, lena)."""

    ACTIVO = "activo"
    INACTIVO = "inactivo"
    ESTADO_CHOICES = [(ACTIVO, "Activo"), (INACTIVO, "Inactivo")]

    CHIP = "chip"
    MULCH = "mulch"
    COMPOST = "compost"
    LENA = "lena"
    TIPO_CHOICES = [
        (CHIP, "Chip"),
        (MULCH, "Mulch"),
        (COMPOST, "Compost"),
        (LENA, "Lena"),
    ]

    SACO = "saco"
    M3 = "m3"
    UNIDAD_VENTA_CHOICES = [(SACO, "Saco"), (M3, "Metro cubico")]

    nombre = models.CharField(max_length=80)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    precio = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    unidad_de_venta = models.CharField(max_length=6, choices=UNIDAD_VENTA_CHOICES)
    estado = models.CharField(max_length=8, choices=ESTADO_CHOICES, default=ACTIVO)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
