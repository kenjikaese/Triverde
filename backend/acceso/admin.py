from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import BitacoraAuditoria, Rol, Usuario


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion")


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "nombre_completo", "rol", "estado", "is_active")
    list_filter = ("rol", "estado", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Datos Triverde", {"fields": ("nombre_completo", "rol", "estado")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Datos Triverde", {"fields": ("nombre_completo", "rol", "estado")}),
    )


@admin.register(BitacoraAuditoria)
class BitacoraAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("fecha_hora", "usuario", "accion", "entidad_afectada", "id_objeto")
    list_filter = ("entidad_afectada", "accion")
    search_fields = ("accion", "entidad_afectada", "id_objeto", "detalle")
    readonly_fields = ("fecha_hora",)
