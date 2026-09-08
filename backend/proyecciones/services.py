from django.utils import timezone
from datetime import timedelta
from recepcion.models import Recepcion
from mantenedores.models import Vehiculo
from .models import ProyeccionSemanal, ProyeccionMensual
import logging

logger = logging.getLogger(__name__)

class ProyeccionService:
    """
    Servicio de proyecciones - Módulo 7
    Casos de uso: CU-50 a CU-54
    """
    
    # Factores de conversión (se pueden obtener de configuracion luego)
    DENSIDAD_CHIP = 250  # kg/m³
    FACTOR_COMPOST = 0.6  # 60% del chip se convierte en compost
    PRECIO_CHIP = 150     # $ por kg
    PRECIO_COMPOST = 200  # $ por kg
    COSTO_KM = 500        # $ por km
    KM_POR_VIAJE = 10     # km promedio por viaje
    
    @classmethod
    def proyectar_semanal(cls, semanas=4):
        """
        CU-50: Proyección de producción semanal
        Calcula la estimación de chip y compost para las próximas N semanas
        """
        resultados = []
        
        # Obtener recepciones de las últimas 8 semanas
        fecha_limite = timezone.now() - timedelta(weeks=8)
        recepciones = Recepcion.objects.filter(
            fecha__gte=fecha_limite,
            estado='sincronizado'
        )
        
        # Si no hay datos históricos, usar valores por defecto
        if not recepciones.exists():
            return cls._generar_defecto_semanal(semanas)
        
        # Agrupar recepciones por semana
        datos_por_semana = {}
        for recepcion in recepciones:
            semana = recepcion.fecha.isocalendar()[1]
            anio = recepcion.fecha.year
            clave = f"{anio}-W{semana:02d}"
            
            if clave not in datos_por_semana:
                datos_por_semana[clave] = {'chip': 0, 'compost': 0}
            
            # Calcular por cada línea de recepción
            for linea in recepcion.lineas.all():
                chip_kg = linea.chip_m3 * cls.DENSIDAD_CHIP
                compost_kg = chip_kg * cls.FACTOR_COMPOST
                datos_por_semana[clave]['chip'] += chip_kg
                datos_por_semana[clave]['compost'] += compost_kg
        
        if not datos_por_semana:
            return cls._generar_defecto_semanal(semanas)
        
        # Calcular promedios semanales
        total_semanas = len(datos_por_semana)
        prom_chip = sum(d['chip'] for d in datos_por_semana.values()) / total_semanas
        prom_compost = sum(d['compost'] for d in datos_por_semana.values()) / total_semanas
        
        # Generar proyecciones para las próximas N semanas
        fecha_actual = timezone.now()
        for i in range(semanas):
            fecha_semana = fecha_actual + timedelta(weeks=i)
            semana_str = f"{fecha_semana.year}-W{fecha_semana.isocalendar()[1]:02d}"
            
            # Factor estacional
            mes = fecha_semana.month
            if mes in [12, 1, 2]:
                factor = 1.2  # Verano: +20%
            elif mes in [6, 7, 8]:
                factor = 0.8  # Invierno: -20%
            else:
                factor = 1.0
            
            # Crear o actualizar la proyección (evita duplicados)
            proyeccion, created = ProyeccionSemanal.objects.update_or_create(
                semana=semana_str,
                defaults={
                    'fecha_inicio': (fecha_semana - timedelta(days=fecha_semana.weekday())).date(),
                    'fecha_fin': (fecha_semana - timedelta(days=fecha_semana.weekday()) + timedelta(days=6)).date(),
                    'chip_estimado_kg': round(prom_chip * factor, 2),
                    'compost_estimado_kg': round(prom_compost * factor, 2)
                }
            )
            resultados.append(proyeccion)
        
        return resultados
    
    @classmethod
    def proyectar_mensual(cls, meses=6):
        """
        CU-51: Proyección de producción mensual
        Calcula la estimación de chip y compost para los próximos N meses
        """
        resultados = []
        
        # Obtener proyecciones semanales
        proyecciones_semanales = ProyeccionSemanal.objects.all().order_by('semana')[:meses*4]
        
        # Agrupar por mes
        datos_por_mes = {}
        for proy in proyecciones_semanales:
            mes_key = proy.semana[:7]  # YYYY-MM
            if mes_key not in datos_por_mes:
                datos_por_mes[mes_key] = {'chip': 0, 'compost': 0}
            datos_por_mes[mes_key]['chip'] += proy.chip_estimado_kg
            datos_por_mes[mes_key]['compost'] += proy.compost_estimado_kg
        
        # Crear o actualizar proyecciones mensuales
        for mes_key, datos in datos_por_mes.items():
            proyeccion, created = ProyeccionMensual.objects.update_or_create(
                mes=mes_key,
                defaults={
                    'chip_estimado_kg': round(datos['chip'], 2),
                    'compost_estimado_kg': round(datos['compost'], 2)
                }
            )
            resultados.append(proyeccion)
        
        return resultados
    
    @classmethod
    def rendimiento_camion(cls, camion_id, meses=3):
        """
        CU-52: Rendimiento comercial de un camión
        Calcula ventas, costos y utilidad generada por un camión
        """
        try:
            camion = Vehiculo.objects.get(id=camion_id)
        except Vehiculo.DoesNotExist:
            return None
        
        # Obtener recepciones del camión en los últimos N meses
        fecha_limite = timezone.now() - timedelta(days=meses*30)
        recepciones = Recepcion.objects.filter(
            vehiculo_id=camion_id,
            fecha__gte=fecha_limite,
            estado='sincronizado'
        )
        
        # Si no hay recepciones, retornar datos vacíos
        if not recepciones.exists():
            return {
                'camion_id': camion.id,
                'patente': camion.patente,
                'periodo': timezone.now().strftime('%Y-%m'),
                'viajes_realizados': 0,
                'total_m3_recibidos': 0,
                'total_kg_recibidos': 0,
                'total_chip_producido_kg': 0,
                'ventas_totales': 0,
                'costos_operativos': 0,
                'utilidad_neta': 0,
                'rendimiento_por_kg': 0,
                'margen_porcentual': 0
            }
        
        # Calcular métricas
        viajes = recepciones.count()
        total_m3 = 0
        total_kg = 0
        total_chip = 0
        
        for recepcion in recepciones:
            for linea in recepcion.lineas.all():
                total_m3 += linea.volumen_m3
                total_kg += linea.peso_kg
                total_chip += linea.chip_m3 * cls.DENSIDAD_CHIP
        
        # Calcular ventas estimadas
        ventas_chip = total_chip * cls.PRECIO_CHIP
        ventas_compost = (total_chip * cls.FACTOR_COMPOST) * cls.PRECIO_COMPOST
        ventas_totales = ventas_chip + ventas_compost
        
        # Calcular costos operativos
        km_totales = viajes * cls.KM_POR_VIAJE
        costos_operativos = km_totales * cls.COSTO_KM
        
        # Calcular rendimiento
        utilidad = ventas_totales - costos_operativos
        rendimiento = utilidad / total_kg if total_kg > 0 else 0
        margen = (utilidad / ventas_totales * 100) if ventas_totales > 0 else 0
        
        return {
            'camion_id': camion.id,
            'patente': camion.patente,
            'periodo': timezone.now().strftime('%Y-%m'),
            'viajes_realizados': viajes,
            'total_m3_recibidos': round(total_m3, 2),
            'total_kg_recibidos': round(total_kg, 2),
            'total_chip_producido_kg': round(total_chip, 2),
            'ventas_totales': round(ventas_totales, 0),
            'costos_operativos': round(costos_operativos, 0),
            'utilidad_neta': round(utilidad, 0),
            'rendimiento_por_kg': round(rendimiento, 2),
            'margen_porcentual': round(margen, 2)
        }
    
    @classmethod
    def _generar_defecto_semanal(cls, semanas):
        """
        Genera proyecciones por defecto cuando no hay datos históricos
        """
        resultados = []
        fecha_actual = timezone.now()
        
        for i in range(semanas):
            fecha_semana = fecha_actual + timedelta(weeks=i)
            semana_str = f"{fecha_semana.year}-W{fecha_semana.isocalendar()[1]:02d}"
            
            proyeccion, created = ProyeccionSemanal.objects.update_or_create(
                semana=semana_str,
                defaults={
                    'fecha_inicio': (fecha_semana - timedelta(days=fecha_semana.weekday())).date(),
                    'fecha_fin': (fecha_semana - timedelta(days=fecha_semana.weekday()) + timedelta(days=6)).date(),
                    'chip_estimado_kg': 5000.0,
                    'compost_estimado_kg': 3000.0
                }
            )
            resultados.append(proyeccion)
        
        return resultados
