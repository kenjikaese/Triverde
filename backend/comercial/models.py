"""Modulo 8 - Comercial (docs/11 SS11.3).

Cierra el ciclo comercial: cotizaciones de servicio, ventas de producto con
sus lineas, despachos, cobros y documentos tributarios.

La cuenta corriente del cliente (CU-64) no se almacena: se calcula en
`services.cuenta_corriente()` a partir de las ventas y los cobros. El campo
`Cliente.estado_pago` (CU-62) es un indicador manual complementario que ya
existe en el modulo de mantenedores; no lo reemplaza.

Todos los objetos son online: no heredan de `SincronizableModel` (la captura
offline es del modulo de recepcion, no del comercial).
"""
from django.db import models

from mantenedores.models import Cliente, Producto
from recepcion.models import Recepcion


class Cotizacion(models.Model):
    """Cotizacion de un servicio a un cliente (CU-55).

    `costo_estimado` lo calcula el servidor sobre el recorrido de ida y vuelta
    (`services.calcular_costo_cotizacion`); nunca llega desde el navegador.
    """

    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="cotizaciones"
    )
    fecha = models.DateField(auto_now_add=True)
    distancia_km = models.DecimalField(max_digits=8, decimal_places=2)
    servicio = models.CharField(max_length=120)
    costo_estimado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    # El vocabulario canonico (SS4.3) no fija un ciclo de estados para la
    # cotizacion; se deja abierto como texto hasta que un CU lo defina.
    estado = models.CharField(max_length=20, default="emitida")

    class Meta:
        verbose_name = "Cotizacion"
        verbose_name_plural = "Cotizaciones"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"Cotizacion {self.pk} - {self.cliente.razon_social}"


class Venta(models.Model):
    """Venta de producto a un cliente (CU-58).

    Cabecera del agregado: las lineas viven en `DetalleVenta`. El `total` es
    derivado (suma de los subtotales) y lo calcula el servidor.
    """

    PENDIENTE = "pendiente"
    DESPACHADA = "despachada"
    ESTADO_CHOICES = [(PENDIENTE, "Pendiente"), (DESPACHADA, "Despachada")]

    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="ventas"
    )
    fecha = models.DateField(auto_now_add=True)
    estado = models.CharField(
        max_length=10, choices=ESTADO_CHOICES, default=PENDIENTE
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"Venta {self.pk} - {self.cliente.razon_social}"


class DetalleVenta(models.Model):
    """Linea producto + cantidad de una venta.

    `precio_unitario` se copia del producto al momento de vender (precio
    historico: cambiar el catalogo despues no altera ventas ya registradas) y
    `subtotal` es su producto por la cantidad.

    `pila` es el enlace Venta -> Pila que necesita el CU-68 (Modulo 9, punto de
    integracion 1 del Inc 3): indica de que lote salio el producto vendido. Es
    opcional porque los servicios y los productos sin lote no tienen pila de
    origen. PROTECT porque una pila con ventas asociadas es evidencia de
    trazabilidad y no debe desaparecer.
    """

    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, related_name="detalles"
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name="detalles_venta"
    )
    pila = models.ForeignKey(
        "inventario.Pila",
        on_delete=models.PROTECT,
        related_name="detalles_venta",
        null=True,
        blank=True,
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    unidad = models.CharField(max_length=6, choices=Producto.UNIDAD_VENTA_CHOICES)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"
        ordering = ["id"]

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad} {self.unidad}"


class Despacho(models.Model):
    """Salida efectiva del producto vendido (CU-60).

    Uno por venta (`OneToOne`): la Excepcion 2 del CU-60 pide impedir el
    despacho duplicado, y la restriccion vive en la base, no solo en la vista.
    """

    venta = models.OneToOneField(
        Venta, on_delete=models.CASCADE, related_name="despacho"
    )
    fecha = models.DateField()
    direccion = models.CharField(max_length=200, null=True, blank=True)
    receptor = models.CharField(max_length=120)
    # Sin ciclo de estados canonico definido para el despacho (vocabulario
    # SS4.3): el estado del ciclo lo lleva `Venta.estado`.
    estado = models.CharField(max_length=20, default="entregado")

    class Meta:
        verbose_name = "Despacho"
        verbose_name_plural = "Despachos"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"Despacho de la venta {self.venta_id}"


class Cobro(models.Model):
    """Pago recibido, por una venta o por una recepcion.

    Decision de diseno: el contrato de docs/11 SS11.3 modela `Cobro` con FK a
    `Venta`, pero el CU-61 cobra una *recepcion* (tarifa por tramo del camion).
    Se resuelve con ambas FK nulas y excluyentes mas la FK al cliente, en vez
    de inventar un objeto nuevo. `venta` y `recepcion` no pueden ir las dos
    llenas ni las dos vacias (se valida en el serializer).
    """

    venta = models.ForeignKey(
        Venta, on_delete=models.PROTECT, null=True, blank=True,
        related_name="cobros",
    )
    recepcion = models.OneToOneField(
        Recepcion, on_delete=models.PROTECT, null=True, blank=True,
        related_name="cobro",
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="cobros"
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateField()
    # Forma de pago: el vocabulario canonico no fija la lista de medios, se
    # deja como texto hasta que el cliente la acote.
    medio = models.CharField(max_length=40, null=True, blank=True)
    estado = models.CharField(max_length=20, default="registrado")

    class Meta:
        verbose_name = "Cobro"
        verbose_name_plural = "Cobros"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"Cobro {self.pk} - ${self.monto}"


class DocumentoTributario(models.Model):
    """Boleta o factura pendiente de emitir (CU-63): seguimiento, no emision.

    Decision de diseno: el contrato lo modela con FK a `Venta`, pero el CU-63
    lo registra "desde el detalle de una venta *o de un cobro*". Se aplica el
    mismo criterio que en `Cobro`: dos FK nulas y excluyentes mas el cliente.
    """

    BOLETA = "boleta"
    FACTURA = "factura"
    TIPO_CHOICES = [(BOLETA, "Boleta"), (FACTURA, "Factura")]

    PENDIENTE = "pendiente"
    ESTADO_CHOICES = [(PENDIENTE, "Pendiente")]

    venta = models.ForeignKey(
        Venta, on_delete=models.PROTECT, null=True, blank=True,
        related_name="documentos",
    )
    cobro = models.ForeignKey(
        Cobro, on_delete=models.PROTECT, null=True, blank=True,
        related_name="documentos",
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="documentos_tributarios"
    )
    tipo = models.CharField(max_length=7, choices=TIPO_CHOICES)
    folio = models.CharField(max_length=30, null=True, blank=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    # El vocabulario canonico (SS4.3) deja la transicion a emitido/pagado como
    # item abierto: ningun CU actual la cierra. Nace y queda en "pendiente".
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default=PENDIENTE
    )
    fecha = models.DateField()

    class Meta:
        verbose_name = "Documento tributario"
        verbose_name_plural = "Documentos tributarios"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.folio or self.pk}"
