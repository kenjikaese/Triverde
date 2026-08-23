from django.contrib import admin

from .models import DetalleRecepcion, FotoRecepcion, Multa, Recepcion


class DetalleRecepcionInline(admin.TabularInline):
    model = DetalleRecepcion
    extra = 1
    readonly_fields = ("id_local",)


class FotoRecepcionInline(admin.TabularInline):
    model = FotoRecepcion
    extra = 0
    readonly_fields = ("id_local", "fecha")


class MultaInline(admin.TabularInline):
    model = Multa
    extra = 0
    readonly_fields = ("id_local",)


@admin.register(Recepcion)
class RecepcionAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "vehiculo", "fecha", "hora", "estado", "estado_sincronizacion")
    list_filter = ("estado", "estado_sincronizacion", "fecha")
    search_fields = ("cliente__razon_social", "conductor", "id_local")
    readonly_fields = ("id_local",)
    inlines = [DetalleRecepcionInline, FotoRecepcionInline, MultaInline]


@admin.register(DetalleRecepcion)
class DetalleRecepcionAdmin(admin.ModelAdmin):
    list_display = ("recepcion", "material", "volumen_m3", "peso_derivado_kg", "destino_sugerido")
    list_filter = ("destino_sugerido", "material")


@admin.register(Multa)
class MultaAdmin(admin.ModelAdmin):
    list_display = ("cliente", "recepcion", "motivo", "monto", "fecha")
    list_filter = ("fecha",)
