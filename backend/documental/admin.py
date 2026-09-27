from django.contrib import admin

from .models import DocumentoLegal, VersionDocumento


class VersionDocumentoInline(admin.TabularInline):
    model = VersionDocumento
    extra = 0
    readonly_fields = ["version", "archivo", "fecha_carga", "usuario", "vigente"]
    can_delete = False


@admin.register(DocumentoLegal)
class DocumentoLegalAdmin(admin.ModelAdmin):
    list_display = ["nombre", "tipo", "entidad_emisora", "fecha_vencimiento", "estado"]
    list_filter = ["tipo", "estado"]
    search_fields = ["nombre", "entidad_emisora"]
    readonly_fields = ["fecha_registro"]
    inlines = [VersionDocumentoInline]
