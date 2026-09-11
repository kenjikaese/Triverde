from decimal import Decimal

from django.utils import timezone

from configuracion.models import ParametroConversion
from mezcla.models import Alerta
from mezcla.services import activar_alerta, resolver_alerta

from .models import Mantencion


CLAVE_ANTICIPACION_DIAS = "alerta_mantenimiento_dias"
CLAVE_ANTICIPACION_HORAS = "alerta_mantenimiento_horas"
ANTICIPACION_DIAS_POR_DEFECTO = 7
ANTICIPACION_HORAS_POR_DEFECTO = Decimal("50")


def obtener_umbrales_anticipacion():
    """Obtiene umbrales editables; usa los valores acordados si aún no existen."""
    valores = dict(
        ParametroConversion.objects.filter(
            clave__in=[CLAVE_ANTICIPACION_DIAS, CLAVE_ANTICIPACION_HORAS]
        ).values_list("clave", "valor")
    )
    dias = valores.get(CLAVE_ANTICIPACION_DIAS, Decimal(ANTICIPACION_DIAS_POR_DEFECTO))
    horas = valores.get(CLAVE_ANTICIPACION_HORAS, ANTICIPACION_HORAS_POR_DEFECTO)
    if dias <= 0:
        dias = Decimal(ANTICIPACION_DIAS_POR_DEFECTO)
    if horas <= 0:
        horas = ANTICIPACION_HORAS_POR_DEFECTO
    return int(dias), horas


def revisar_alertas_mantenimiento():
    """Genera o actualiza alertas proximas/vencidas sin duplicarlas (CU-84)."""
    hoy = timezone.localdate()
    anticipacion_dias, anticipacion_horas = obtener_umbrales_anticipacion()
    revisadas = 0
    for mantencion in Mantencion.objects.select_related("maquinaria", "vehiculo").filter(
        tipo=Mantencion.PREVENTIVA, estado=Mantencion.PROGRAMADA
    ):
        activo = mantencion.activo
        vencida = False
        proxima = False
        detalle = ""
        if mantencion.criterio == Mantencion.POR_FECHA and mantencion.fecha_programada:
            dias = (mantencion.fecha_programada - hoy).days
            vencida = dias < 0
            proxima = dias <= anticipacion_dias
            detalle = f"fecha {mantencion.fecha_programada:%d-%m-%Y}"
        elif mantencion.criterio == Mantencion.POR_HORAS and mantencion.umbral_horas is not None:
            restantes = mantencion.umbral_horas - activo.horometro
            vencida = restantes <= 0
            proxima = restantes <= anticipacion_horas
            detalle = f"umbral {mantencion.umbral_horas} h"

        clave = f"mantencion:{mantencion.pk}"
        alerta = Alerta.objects.filter(
            origen=Alerta.MANTENCION, clave=clave, estado=Alerta.ACTIVA
        ).first()
        if proxima:
            nivel = Alerta.CRITICA if vencida else Alerta.ADVERTENCIA
            condicion = "vencida" if vencida else "proxima"
            mensaje = f"Mantencion {condicion} de {activo}: {detalle}."
            activar_alerta(
                origen=Alerta.MANTENCION, clave=clave, nivel=nivel,
                mensaje=mensaje, mantencion=mantencion,
            )
            revisadas += 1
        elif alerta:
            resolver_alerta(alerta)
    return revisadas
