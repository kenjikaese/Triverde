from django.contrib import admin

from .models import Cliente, Material, Producto, Transportista, Vehiculo


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "rut", "nombre_contacto", "estado_pago", "estado")
    list_filter = ("estado", "estado_pago")
    search_fields = ("razon_social", "rut", "nombre_contacto")


@admin.register(Transportista)
class TransportistaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rut", "cliente", "usuario", "estado")
    list_filter = ("estado", "cliente")
    search_fields = ("nombre", "rut")


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ("patente", "cliente", "capacidad_m3", "tramo", "estado_operativo", "estado")
    list_filter = ("estado", "estado_operativo")
    search_fields = ("patente",)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "densidad_kg_m3", "factor_reduccion_chip", "admite_chip", "estado")
    list_filter = ("estado", "categoria", "admite_chip")
    search_fields = ("nombre",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "precio", "unidad_de_venta", "estado")
    list_filter = ("estado", "tipo")
    search_fields = ("nombre",)
