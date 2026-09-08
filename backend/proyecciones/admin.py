from django.contrib import admin

from .models import Proyeccion


@admin.register(Proyeccion)
class ProyeccionAdmin(admin.ModelAdmin):
    list_display = ["id", "tipo", "periodo_inicio", "periodo_fin", "material", "fecha_generada"]
    list_filter = ["tipo"]
    date_hierarchy = "fecha_generada"
