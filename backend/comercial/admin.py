from django.contrib import admin

from .models import (
    Cobro,
    Cotizacion,
    Despacho,
    DetalleVenta,
    DocumentoTributario,
    Venta,
)


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "servicio", "distancia_km", "costo_estimado", "fecha")
    list_filter = ("estado", "fecha")
    search_fields = ("cliente__razon_social", "servicio")


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ("unidad", "precio_unitario", "subtotal")


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "fecha", "estado", "total")
    list_filter = ("estado", "fecha")
    search_fields = ("cliente__razon_social",)
    inlines = [DetalleVentaInline]


@admin.register(Despacho)
class DespachoAdmin(admin.ModelAdmin):
    list_display = ("id", "venta", "fecha", "receptor", "estado")
    list_filter = ("fecha",)
    search_fields = ("receptor", "direccion")


@admin.register(Cobro)
class CobroAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "venta", "recepcion", "monto", "medio", "fecha")
    list_filter = ("fecha", "medio")
    search_fields = ("cliente__razon_social",)


@admin.register(DocumentoTributario)
class DocumentoTributarioAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "tipo", "folio", "monto", "estado", "fecha")
    list_filter = ("tipo", "estado", "fecha")
    search_fields = ("cliente__razon_social", "folio")
