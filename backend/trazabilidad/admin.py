from django.contrib import admin

from .models import IndicadorAmbiental


@admin.register(IndicadorAmbiental)
class IndicadorAmbientalAdmin(admin.ModelAdmin):
    list_display = ("origen", "recepcion", "pila", "co2_evitado_kg", "fecha")
    list_filter = ("origen", "fecha")
    search_fields = ("recepcion__cliente__razon_social", "pila__codigo", "metodo")

