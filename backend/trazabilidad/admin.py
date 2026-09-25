from django.contrib import admin

from .models import CertificadoTrazabilidad, DeclaracionSinader, IndicadorAmbiental


@admin.register(CertificadoTrazabilidad)
class CertificadoTrazabilidadAdmin(admin.ModelAdmin):
    list_display = ("codigo", "tipo", "cliente", "recepcion", "periodo_inicio", "periodo_fin", "fecha_emision")
    list_filter = ("tipo", "fecha_emision")
    search_fields = ("codigo", "cliente__razon_social")
    readonly_fields = ("codigo", "fecha_emision", "contenido")


@admin.register(DeclaracionSinader)
class DeclaracionSinaderAdmin(admin.ModelAdmin):
    list_display = ("periodo_inicio", "periodo_fin", "fecha_generada", "usuario")
    list_filter = ("fecha_generada",)
    readonly_fields = ("fecha_generada", "contenido")


@admin.register(IndicadorAmbiental)
class IndicadorAmbientalAdmin(admin.ModelAdmin):
    list_display = ("origen", "recepcion", "pila", "co2_evitado_kg", "fecha")
    list_filter = ("origen", "fecha")
    search_fields = ("recepcion__cliente__razon_social", "pila__codigo", "metodo")

