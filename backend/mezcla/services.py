"""Reglas de negocio del modulo 6 (CU-45, CU-46 y CU-48) y utilidades de alertas.

El servicio concentra el calculo de la mezcla objetivo para que pueda ejecutarse
desde la API y automaticamente cuando cambia una composicion o entra inventario.
Ademas expone ``activar_alerta``/``resolver_alerta``, las utilidades genericas
que el modulo 11 usa para sus propias alertas sobre el objeto Alerta compartido.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from configuracion.models import RecetaMezcla
from inventario.models import ComposicionPila, Inventario, Pila
from mantenedores.models import Material

from .models import Alerta

CERO = Decimal("0.00")
ETAPAS_DISPONIBLES = (Inventario.POR_TRITURAR, Inventario.CHIP)


# ---------------------------------------------------------------------------
# Utilidades genericas de alertas (compartidas con el modulo 11)
# ---------------------------------------------------------------------------
@transaction.atomic
def activar_alerta(*, origen, clave, nivel, mensaje, mantencion=None):
    """Crea o actualiza una alerta activa sin duplicarla.

    La clave es responsabilidad del dominio que genera la alerta. M11 usa
    ``mantencion:<id>``; M6 deduplica sus alertas por pila y categoria mediante
    su propia restriccion, por lo que no necesita apoyarse en esta funcion.
    """
    alerta, creada = Alerta.objects.update_or_create(
        origen=origen,
        clave=clave,
        estado=Alerta.ACTIVA,
        defaults={
            "nivel": nivel,
            "mensaje": mensaje,
            "mantencion": mantencion,
            "fecha_resuelta": None,
            "resuelta_por": None,
        },
    )
    return alerta, creada


def resolver_alerta(alerta, usuario=None):
    """Resuelve una alerta conservandola como historial."""
    if alerta.estado == Alerta.RESUELTA:
        return alerta
    alerta.estado = Alerta.RESUELTA
    alerta.fecha_resuelta = timezone.now()
    alerta.resuelta_por = usuario
    alerta.save(update_fields=["estado", "fecha_resuelta", "resuelta_por"])
    return alerta


# ---------------------------------------------------------------------------
# Calculo de mezcla objetivo (Modulo 6)
# ---------------------------------------------------------------------------
def receta_vigente():
    """Devuelve la receta activa mas recientemente actualizada, si existe."""
    return RecetaMezcla.objects.filter(vigente=True).order_by("-actualizado_en", "-id").first()


def _volumen_disponible(categoria):
    """Suma el material disponible para una categoria en etapas utilizables."""
    total = Inventario.objects.filter(
        material__categoria=categoria, etapa__in=ETAPAS_DISPONIBLES
    ).aggregate(total=Sum("volumen_m3"))["total"]
    return total or CERO


def _composicion_por_categoria(pila):
    """Agrupa por categoria lo que ya fue incorporado a la pila."""
    valores = {Material.SECA: CERO, Material.VERDE: CERO}
    for fila in pila.composiciones.select_related("material"):
        if fila.material.categoria in valores:
            valores[fila.material.categoria] += fila.volumen_m3
    return valores


def _faltantes(actual, receta):
    """Calcula que categoria falta para alcanzar la proporcion de la receta."""
    seca, verde = actual[Material.SECA], actual[Material.VERDE]
    if seca == CERO and verde == CERO:
        return {Material.SECA: CERO, Material.VERDE: CERO}
    proporcion = receta.relacion_seca / receta.relacion_verde
    if seca * receta.relacion_verde >= verde * receta.relacion_seca:
        return {
            Material.SECA: CERO,
            Material.VERDE: max(CERO, seca / proporcion - verde),
        }
    return {
        Material.SECA: max(CERO, verde * proporcion - seca),
        Material.VERDE: CERO,
    }


def _actualizar_alerta(pila, categoria, faltante, disponible):
    """Crea o actualiza una alerta solo cuando el stock no cubre el faltante."""
    activa = Alerta.objects.filter(
        origen=Alerta.MEZCLA, estado=Alerta.ACTIVA, pila=pila, categoria=categoria
    ).first()
    if faltante > disponible:
        mensaje = (
            f"Faltan {faltante.quantize(Decimal('0.01'))} m3 de material {categoria}; "
            f"hay {disponible.quantize(Decimal('0.01'))} m3 disponibles."
        )
        if activa:
            activa.faltante_m3 = faltante
            activa.disponible_m3 = disponible
            activa.mensaje = mensaje
            activa.save(update_fields=["faltante_m3", "disponible_m3", "mensaje"])
        else:
            Alerta.objects.create(
                origen=Alerta.MEZCLA,
                nivel="faltante",
                estado=Alerta.ACTIVA,
                mensaje=mensaje,
                categoria=categoria,
                faltante_m3=faltante,
                disponible_m3=disponible,
                pila=pila,
            )
    elif activa:
        activa.estado = Alerta.RESUELTA
        activa.fecha_resuelta = timezone.now()
        activa.save(update_fields=["estado", "fecha_resuelta"])


def calcular_mezcla(pila, actualizar_alertas=True):
    """Calcula CU-45 y dispara CU-46 para una pila en armado.

    La ausencia de receta es informativa: no bloquea la pila ni crea alertas.
    """
    actual = _composicion_por_categoria(pila)
    disponibles = {
        Material.SECA: _volumen_disponible(Material.SECA),
        Material.VERDE: _volumen_disponible(Material.VERDE),
    }
    if pila.estado != Pila.EN_FORMACION:
        Alerta.objects.filter(
            origen=Alerta.MEZCLA, estado=Alerta.ACTIVA, pila=pila
        ).update(estado=Alerta.RESUELTA, fecha_resuelta=timezone.now())
        return {
            "pila": pila,
            "receta": None,
            "mensaje": "La mezcla objetivo solo aplica a pilas en formacion.",
            "actual": actual,
            "faltantes": {Material.SECA: CERO, Material.VERDE: CERO},
            "disponibles": disponibles,
        }
    receta = receta_vigente()
    if receta is None:
        return {
            "pila": pila,
            "receta": None,
            "mensaje": "No hay una receta vigente; la pila no queda bloqueada.",
            "actual": actual,
            "faltantes": {Material.SECA: CERO, Material.VERDE: CERO},
            "disponibles": disponibles,
        }
    faltantes = _faltantes(actual, receta)
    if actualizar_alertas:
        for categoria in (Material.SECA, Material.VERDE):
            _actualizar_alerta(pila, categoria, faltantes[categoria], disponibles[categoria])
    return {
        "pila": pila,
        "receta": receta,
        "mensaje": None,
        "actual": actual,
        "faltantes": faltantes,
        "disponibles": disponibles,
    }


def recalcular_para_material(material):
    """Recalcula las pilas en formacion afectadas por una categoria."""
    pilas = Pila.objects.filter(
        estado=Pila.EN_FORMACION, composiciones__material__categoria=material.categoria
    ).distinct()
    for pila in pilas:
        calcular_mezcla(pila)


def sugerir_destino(material):
    """Aplica CU-48: pila, chip o venta directa en ese orden de prioridad."""
    alerta = Alerta.objects.filter(
        origen=Alerta.MEZCLA, estado=Alerta.ACTIVA, categoria=material.categoria
    ).order_by("-faltante_m3", "fecha_generada").first()
    if alerta:
        return "a pila"
    if material.admite_chip:
        return "a chip"
    return "a venta directa"
