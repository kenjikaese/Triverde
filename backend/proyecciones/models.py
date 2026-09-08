from django.db import models
from django.conf import settings

class ProyeccionSemanal(models.Model):
    semana = models.CharField(max_length=10, unique=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    chip_estimado_kg = models.FloatField()
    compost_estimado_kg = models.FloatField()
    chip_real_kg = models.FloatField(null=True, blank=True)
    compost_real_kg = models.FloatField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'proyecciones_semanales'
        ordering = ['-semana']
    
    def __str__(self):
        return f"Semana {self.semana}"

class ProyeccionMensual(models.Model):
    mes = models.CharField(max_length=7, unique=True)
    chip_estimado_kg = models.FloatField()
    compost_estimado_kg = models.FloatField()
    chip_real_kg = models.FloatField(null=True, blank=True)
    compost_real_kg = models.FloatField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'proyecciones_mensuales'
        ordering = ['-mes']
    
    def __str__(self):
        return f"Mes {self.mes}"
