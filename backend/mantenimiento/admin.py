from django.contrib import admin

from .models import Maquinaria, Mantencion, RegistroUso

admin.site.register(Maquinaria)
admin.site.register(RegistroUso)
admin.site.register(Mantencion)
