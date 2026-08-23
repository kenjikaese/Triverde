from django.contrib import admin

from .models import HistorialCambioParametro, ParametroConversion, TarifaRecepcion


@admin.register(ParametroConversion)
class ParametroConversionAdmin(admin.ModelAdmin):
    list_display = ("clave", "nombre", "valor", "unidad")
    search_fields = ("clave", "nombre")


@admin.register(TarifaRecepcion)
class TarifaRecepcionAdmin(admin.ModelAdmin):
    list_display = ("tramo_min_m3", "tramo_max_m3", "monto", "vigente")
    list_filter = ("vigente",)


@admin.register(HistorialCambioParametro)
class HistorialCambioParametroAdmin(admin.ModelAdmin):
    list_display = ("parametro", "valor_anterior", "valor_nuevo", "usuario", "fecha_hora")
    list_filter = ("parametro",)
    readonly_fields = ("fecha_hora",)
