from django.contrib import admin
from .models import DocumentoLegal, VersionDocumento


@admin.register(DocumentoLegal)
class DocumentoLegalAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'fecha_emision', 'fecha_vencimiento', 'estado']
    list_filter = ['tipo', 'estado']
    search_fields = ['nombre', 'descripcion']
    readonly_fields = ['fecha_creacion']


@admin.register(VersionDocumento)
class VersionDocumentoAdmin(admin.ModelAdmin):
    list_display = ['documento', 'numero_version', 'fecha_creacion']
    list_filter = ['documento']
    search_fields = ['documento__nombre']
    readonly_fields = ['fecha_creacion']
