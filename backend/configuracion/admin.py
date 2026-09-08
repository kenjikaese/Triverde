from django.contrib import admin

from .models import (
    CostoOperativo,
    CostoTransporte,
    HistorialCambioParametro,
    ParametroConversion,
    RecetaMezcla,
    TarifaRecepcion,
)


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


@admin.register(RecetaMezcla)
class RecetaMezclaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "proporcion", "vigente", "actualizado_en")
    list_filter = ("vigente",)
    search_fields = ("nombre",)


@admin.register(CostoTransporte)
class CostoTransporteAdmin(admin.ModelAdmin):
    list_display = ("costo_por_km", "vigente", "fecha")
    list_filter = ("vigente",)


@admin.register(CostoOperativo)
class CostoOperativoAdmin(admin.ModelAdmin):
    list_display = ("concepto", "monto", "unidad", "vigente", "actualizado_en")
    list_filter = ("vigente", "unidad")
    search_fields = ("concepto",)
