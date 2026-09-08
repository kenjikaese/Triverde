from django.contrib import admin
from .models import ProyeccionSemanal, ProyeccionMensual

@admin.register(ProyeccionSemanal)
class ProyeccionSemanalAdmin(admin.ModelAdmin):
    list_display = ['semana', 'fecha_inicio', 'fecha_fin', 'chip_estimado_kg', 'compost_estimado_kg']
    list_filter = ['semana']
    search_fields = ['semana']

@admin.register(ProyeccionMensual)
class ProyeccionMensualAdmin(admin.ModelAdmin):
    list_display = ['mes', 'chip_estimado_kg', 'compost_estimado_kg']
    list_filter = ['mes']
    search_fields = ['mes']
