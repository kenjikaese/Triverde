"""Calculos automaticos de huella de carbono del Modulo 9 (CU-69 y CU-70)."""
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from common.trazas import traza
from configuracion.models import ParametroConversion
from inventario.models import Pila, ProcesoPila
from recepcion.models import Recepcion

from .models import IndicadorAmbiental


CLAVE_CO2_CAMION = "co2_evitado_camion"
CLAVE_CO2_COMPOSTAJE = "co2_evitado_compostaje"
CERO = Decimal("0")
CENTESIMA = Decimal("0.01")


@dataclass(frozen=True)
class CalculoPendiente:
    origen: str
    objeto_id: int
    referencia: str
    motivo: str


def _factor(clave):
    parametro = ParametroConversion.objects.filter(clave=clave).first()
    if parametro is None or parametro.valor <= CERO:
        return None
    return parametro.valor


def _fecha_cierre_pila(pila):
    ultimo_ensacado = pila.procesos.filter(
        tipo=ProcesoPila.ENSACADO
    ).order_by("-fecha", "-id").first()
    if ultimo_ensacado is not None:
        return timezone.localtime(ultimo_ensacado.fecha).date()
    return timezone.localdate()


def motivo_pendiente_recepcion(recepcion):
    if recepcion.estado != Recepcion.RECIBIDA:
        return "La recepcion aun no esta confirmada como recibida."
    detalles = list(recepcion.detalles.all())
    if not detalles:
        return "La recepcion no tiene detalles con peso calculado."
    if any(detalle.peso_derivado_kg is None for detalle in detalles):
        return "Falta calcular el peso de uno o mas materiales recibidos."
    if _factor(CLAVE_CO2_CAMION) is None:
        return f"Falta configurar el parametro {CLAVE_CO2_CAMION}."
    return None


def motivo_pendiente_pila(pila):
    if pila.estado != Pila.CERRADA:
        return "La pila aun no concluye su ciclo de compostaje."
    composiciones = list(pila.composiciones.select_related("material"))
    if not composiciones:
        return "La pila no tiene composicion registrada."
    materiales_sin_densidad = [
        composicion.material.nombre
        for composicion in composiciones
        if composicion.material.densidad_kg_m3 is None
    ]
    if materiales_sin_densidad:
        return "Falta densidad para: " + ", ".join(materiales_sin_densidad) + "."
    if _factor(CLAVE_CO2_COMPOSTAJE) is None:
        return f"Falta configurar el parametro {CLAVE_CO2_COMPOSTAJE}."
    return None


@transaction.atomic
def recalcular_recepcion(recepcion):
    """Crea, actualiza o retira el indicador asociado a una recepcion."""
    motivo = motivo_pendiente_recepcion(recepcion)
    if motivo is not None:
        IndicadorAmbiental.objects.filter(recepcion=recepcion).delete()
        return None

    factor = _factor(CLAVE_CO2_CAMION)
    peso_total = sum(
        (detalle.peso_derivado_kg for detalle in recepcion.detalles.all()),
        CERO,
    )
    co2 = (peso_total * factor).quantize(CENTESIMA)
    indicador, _ = IndicadorAmbiental.objects.update_or_create(
        recepcion=recepcion,
        defaults={
            "origen": IndicadorAmbiental.RECEPCION,
            "pila": None,
            "co2_evitado_kg": co2,
            "metodo": (
                f"peso recibido {peso_total} kg x factor "
                f"{CLAVE_CO2_CAMION}={factor}"
            ),
            "fecha": recepcion.fecha,
        },
    )
    traza(
        "CU-69",
        "indicador.recepcion_calculado",
        recepcion=recepcion.pk,
        peso_kg=peso_total,
        factor=factor,
        co2_kg=co2,
    )
    return indicador


@transaction.atomic
def recalcular_pila(pila):
    """Crea, actualiza o retira el indicador asociado a una pila cerrada."""
    motivo = motivo_pendiente_pila(pila)
    if motivo is not None:
        IndicadorAmbiental.objects.filter(pila=pila).delete()
        return None

    factor = _factor(CLAVE_CO2_COMPOSTAJE)
    composiciones = pila.composiciones.select_related("material")
    peso_total = sum(
        (
            composicion.volumen_m3 * composicion.material.densidad_kg_m3
            for composicion in composiciones
        ),
        CERO,
    )
    co2 = (peso_total * factor).quantize(CENTESIMA)
    indicador, _ = IndicadorAmbiental.objects.update_or_create(
        pila=pila,
        defaults={
            "origen": IndicadorAmbiental.PILA,
            "recepcion": None,
            "co2_evitado_kg": co2,
            "metodo": (
                f"peso compostado {peso_total} kg x factor "
                f"{CLAVE_CO2_COMPOSTAJE}={factor}"
            ),
            "fecha": _fecha_cierre_pila(pila),
        },
    )
    traza(
        "CU-70",
        "indicador.pila_calculado",
        pila=pila.pk,
        peso_kg=peso_total,
        factor=factor,
        co2_kg=co2,
    )
    return indicador


def recalcular_por_parametro(clave):
    if clave == CLAVE_CO2_CAMION:
        for recepcion in Recepcion.objects.filter(estado=Recepcion.RECIBIDA):
            recalcular_recepcion(recepcion)
    elif clave == CLAVE_CO2_COMPOSTAJE:
        for pila in Pila.objects.filter(estado=Pila.CERRADA):
            recalcular_pila(pila)


def listar_pendientes():
    pendientes = []
    recepciones_calculadas = IndicadorAmbiental.objects.filter(
        recepcion__isnull=False
    ).values_list("recepcion_id", flat=True)
    for recepcion in Recepcion.objects.filter(
        estado=Recepcion.RECIBIDA
    ).exclude(pk__in=recepciones_calculadas).prefetch_related("detalles"):
        motivo = motivo_pendiente_recepcion(recepcion)
        if motivo:
            pendientes.append(
                CalculoPendiente(
                    IndicadorAmbiental.RECEPCION,
                    recepcion.pk,
                    f"Recepcion #{recepcion.pk}",
                    motivo,
                )
            )

    pilas_calculadas = IndicadorAmbiental.objects.filter(
        pila__isnull=False
    ).values_list("pila_id", flat=True)
    for pila in Pila.objects.filter(estado=Pila.CERRADA).exclude(
        pk__in=pilas_calculadas
    ).prefetch_related("composiciones__material"):
        motivo = motivo_pendiente_pila(pila)
        if motivo:
            pendientes.append(
                CalculoPendiente(
                    IndicadorAmbiental.PILA,
                    pila.pk,
                    pila.codigo,
                    motivo,
                )
            )
    return pendientes

