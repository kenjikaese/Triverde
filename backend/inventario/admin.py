from django.contrib import admin

from .models import ComposicionPila, Inventario, Pila, ProcesoPila


class ComposicionPilaInline(admin.TabularInline):
    model = ComposicionPila
    extra = 0


@admin.register(Pila)
class PilaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "fecha_inicio", "estado")
    list_filter = ("estado",)
    search_fields = ("codigo",)
    inlines = [ComposicionPilaInline]


@admin.register(ProcesoPila)
class ProcesoPilaAdmin(admin.ModelAdmin):
    list_display = (
        "tipo", "pila", "material", "fecha", "volumen_m3", "temperatura",
        "chip_pendiente", "estado_sincronizacion",
    )
    list_filter = ("tipo", "chip_pendiente", "estado_sincronizacion")
    search_fields = ("pila__codigo", "material__nombre")


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ("material", "etapa", "volumen_m3", "actualizado")
    list_filter = ("etapa",)
    search_fields = ("material__nombre",)
    # El saldo es derivado (CU-44): se consulta desde el admin, no se teclea.
    readonly_fields = ("actualizado",)
