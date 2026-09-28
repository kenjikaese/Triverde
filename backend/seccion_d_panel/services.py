from decimal import Decimal

from django.db.models import Sum

from comercial.models import DetalleVenta
from inventario.models import Inventario
from produccion.models import Pila

from .models import PanelControl

INDICADORES_VALIDOS = {"inventario", "produccion", "ventas"}


def _decimal(valor):
    return valor if valor is not None else Decimal("0")


def _indicadores_activos(usuario):
    panel = PanelControl.objects.filter(usuario=usuario).first()
    if panel and panel.indicadores_visibles:
        return panel.indicadores_visibles
    return list(PanelControl.DEFECTO)


def _bloque_inventario():
    filas = Inventario.objects.values("material__nombre", "estado").annotate(
        cantidad_kg=Sum("cantidad_kg")
    )
    return [
        {
            "material": f["material__nombre"],
            "estado": f["estado"],
            "cantidad_kg": str(_decimal(f["cantidad_kg"])),
        }
        for f in filas
    ]


def _bloque_produccion():
    pilas = Pila.objects.all().order_by("-fecha_inicio")[:20]
    return [
        {
            "pila_id": p.pk,
            "material": p.material.nombre,
            "peso_kg": str(p.peso_kg),
            "estado": "en_proceso" if p.estado == Pila.EN_PROCESO else "procesada",
        }
        for p in pilas
    ]


def _bloque_ventas():
    recientes = DetalleVenta.objects.order_by("-venta__fecha")[:20]
    total = _decimal(recientes.aggregate(m=Sum("monto"))["m"])
    return {"total_reciente": str(total)}


CONSTRUCTORES_BLOQUE = {
    "inventario": _bloque_inventario,
    "produccion": _bloque_produccion,
    "ventas": _bloque_ventas,
}


def armar_panel(usuario):
    indicadores = _indicadores_activos(usuario)
    panel = {}
    for clave in indicadores:
        constructor = CONSTRUCTORES_BLOQUE.get(clave)
        panel[clave] = constructor() if constructor else ([] if clave != "ventas" else {"total_reciente": "0"})
    return {"indicadores_visibles": indicadores, "bloques": panel}


class SinIndicadores(ValueError):
    pass


def guardar_preferencias(usuario, indicadores_visibles, configuracion=None):
    if not indicadores_visibles:
        raise SinIndicadores("Debe seleccionar al menos un indicador")

    panel, creado = PanelControl.objects.get_or_create(
        usuario=usuario,
        defaults={"indicadores_visibles": indicadores_visibles, "configuracion": configuracion or {}},
    )
    if creado:
        return panel, True

    sin_cambios = (
        list(panel.indicadores_visibles) == list(indicadores_visibles)
        and (configuracion is None or panel.configuracion == configuracion)
    )
    if sin_cambios:
        return panel, False

    panel.indicadores_visibles = indicadores_visibles
    if configuracion is not None:
        panel.configuracion = configuracion
    panel.save()
    return panel, True
