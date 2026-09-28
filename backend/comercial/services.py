"""Logica de negocio del modulo comercial.

Vive aca y no en las vistas (patron por capas: las derivaciones y las
transiciones de estado se calculan en el servidor, nunca en el navegador).
"""
from decimal import Decimal

from django.apps import apps

from common.trazas import traza
from configuracion.models import ParametroConversion, TarifaRecepcion


def costo_por_km_vigente():
    """Devuelve el costo por kilometro vigente, o None si no hay ninguno.

    Busca en dos lugares, en este orden:

    1. `CostoTransporte`, el objeto que aporta el Modulo 2 (CU-12). Se resuelve
       por el registry de Django en vez de importarlo directo, para que este
       modulo compile y se pueda probar aunque M2 todavia no lo haya integrado.
    2. El `ParametroConversion` de clave `costo_por_km`, que ya existe desde el
       Incremento 1 con el valor de docs/02. Es el mismo dato en su forma
       previa, asi que sirve de respaldo mientras M2 no cierre: el cotizador
       funciona hoy y pasa solo al objeto nuevo cuando aparezca.

    Si no hay ninguno de los dos, devuelve None, que es la Excepcion 3 del
    CU-55 (falta el parametro y no se calcula).
    """
    try:
        CostoTransporte = apps.get_model("configuracion", "CostoTransporte")
    except LookupError:
        pass
    else:
        costo = CostoTransporte.objects.filter(vigente=True).order_by("-id").first()
        if costo:
            return costo.costo_por_km

    parametro = ParametroConversion.objects.filter(clave="costo_por_km").first()
    if parametro:
        traza("CU-55", "costo_km.desde_parametro", valor=parametro.valor)
        return parametro.valor
    return None


def calcular_costo_cotizacion(distancia_km):
    """Costo de una cotizacion: ida y vuelta por el costo indexado por km.

    Devuelve None si no hay costo por kilometro configurado (CU-55, Excepcion
    3: el sistema informa que falta el parametro y no calcula).
    """
    costo_km = costo_por_km_vigente()
    if costo_km is None:
        traza("CU-55", "cotizacion.sin_costo_km", distancia=distancia_km)
        return None
    recorrido = Decimal(str(distancia_km)) * Decimal("2")
    costo = (recorrido * costo_km).quantize(Decimal("0.01"))
    traza(
        "CU-55",
        "cotizacion.calculada",
        distancia=distancia_km,
        recorrido=recorrido,
        costo_km=costo_km,
        costo=costo,
    )
    return costo


def tarifa_sugerida(recepcion):
    """Monto sugerido para el cobro de una recepcion (CU-61).

    Busca la `TarifaRecepcion` vigente cuyo tramo contiene la capacidad del
    vehiculo de la recepcion. Devuelve None si la recepcion no tiene vehiculo,
    si el vehiculo no tiene capacidad configurada o si ningun tramo la cubre;
    en ese caso el operador ingresa el monto a mano y el cobro no se bloquea
    (CU-61, Excepcion 1).
    """
    vehiculo = recepcion.vehiculo
    if vehiculo is None or vehiculo.capacidad_m3 is None:
        traza("CU-61", "cobro.sin_capacidad", recepcion=recepcion.pk)
        return None
    tarifa = (
        TarifaRecepcion.objects.filter(
            vigente=True,
            tramo_min_m3__lte=vehiculo.capacidad_m3,
            tramo_max_m3__gte=vehiculo.capacidad_m3,
        )
        .order_by("tramo_min_m3")
        .first()
    )
    if tarifa is None:
        traza(
            "CU-61",
            "cobro.sin_tarifa",
            recepcion=recepcion.pk,
            capacidad=vehiculo.capacidad_m3,
        )
        return None
    traza(
        "CU-61",
        "cobro.tarifa_sugerida",
        recepcion=recepcion.pk,
        capacidad=vehiculo.capacidad_m3,
        tramo=f"{tarifa.tramo_min_m3}-{tarifa.tramo_max_m3}",
        monto=tarifa.monto,
    )
    return tarifa.monto


def cuenta_corriente(cliente, desde=None, hasta=None):
    """Saldo y movimientos de un cliente (CU-64).

    Calculada, no almacenada: saldo = suma de ventas - suma de cobros, con el
    detalle cronologico de cada movimiento. El rango de fechas es opcional y
    filtra ambos lados por igual.
    """
    Venta = apps.get_model("comercial", "Venta")
    Cobro = apps.get_model("comercial", "Cobro")

    ventas = Venta.objects.filter(cliente=cliente)
    cobros = Cobro.objects.filter(cliente=cliente)
    if desde:
        ventas = ventas.filter(fecha__gte=desde)
        cobros = cobros.filter(fecha__gte=desde)
    if hasta:
        ventas = ventas.filter(fecha__lte=hasta)
        cobros = cobros.filter(fecha__lte=hasta)

    movimientos = []
    total_ventas = Decimal("0.00")
    total_cobros = Decimal("0.00")

    for venta in ventas:
        total_ventas += venta.total
        movimientos.append(
            {
                "tipo": "venta",
                "id": venta.pk,
                "fecha": venta.fecha,
                "detalle": f"Venta {venta.pk}",
                "monto": venta.total,
            }
        )
    for cobro in cobros:
        total_cobros += cobro.monto
        origen = (
            f"recepcion {cobro.recepcion_id}"
            if cobro.recepcion_id
            else f"venta {cobro.venta_id}"
        )
        movimientos.append(
            {
                "tipo": "cobro",
                "id": cobro.pk,
                "fecha": cobro.fecha,
                "detalle": f"Cobro de {origen}",
                "monto": cobro.monto,
            }
        )

    movimientos.sort(key=lambda m: (m["fecha"], m["id"]))
    traza(
        "CU-64",
        "cuenta_corriente.calculada",
        cliente=cliente.pk,
        ventas=total_ventas,
        cobros=total_cobros,
        saldo=total_ventas - total_cobros,
        movimientos=len(movimientos),
    )
    return {
        "cliente": cliente.pk,
        "razon_social": cliente.razon_social,
        "estado_pago": cliente.estado_pago,
        "total_ventas": total_ventas,
        "total_cobros": total_cobros,
        "saldo": total_ventas - total_cobros,
        "movimientos": movimientos,
    }


def trazabilidad_venta(venta):
    """Cadena trazable de un lote entregado (CU-68): Venta -> Pila -> composicion.

    Recorre cada linea de la venta. Si la linea tiene pila de origen, devuelve
    la pila (codigo, estado, fecha de inicio) y su composicion por material y
    volumen. Si ninguna linea tiene pila, la venta queda "sin trazabilidad"
    (CU-68, Excepcion 1). Si la pila no esta cerrada, se advierte que su
    composicion aun no es definitiva (CU-68, Excepcion 2).

    Las recepciones de origen salen de `AporteRecepcionPila` (propuesta Inc 3):
    que descarga aporto material a la pila y cuanto. Si la pila no tiene
    aportes registrados, la cadena se detiene en la composicion y se advierte.
    """
    Pila = apps.get_model("inventario", "Pila")

    lineas = []
    for detalle in venta.detalles.select_related("producto", "pila").all():
        linea = {
            "detalle": detalle.pk,
            "producto": detalle.producto.nombre,
            "cantidad": f"{detalle.cantidad:.2f}",
            "unidad": detalle.unidad,
            "pila": None,
        }
        pila = detalle.pila
        if pila is not None:
            composicion = [
                {
                    "material": item.material.nombre,
                    "volumen_m3": f"{item.volumen_m3:.2f}",
                }
                for item in pila.composiciones.select_related("material").all()
            ]
            recepciones_origen = [
                {
                    "recepcion": aporte.detalle_recepcion.recepcion_id,
                    "cliente": aporte.detalle_recepcion.recepcion.cliente.razon_social,
                    "fecha": aporte.detalle_recepcion.recepcion.fecha,
                    "material": aporte.detalle_recepcion.material.nombre,
                    "volumen_m3": f"{aporte.volumen_m3:.2f}",
                }
                for aporte in pila.aportes.select_related(
                    "detalle_recepcion__recepcion__cliente", "detalle_recepcion__material"
                ).order_by("detalle_recepcion__recepcion__fecha", "id")
            ]
            linea["pila"] = {
                "id": pila.pk,
                "codigo": pila.codigo,
                "estado": pila.estado,
                "fecha_inicio": pila.fecha_inicio,
                "volumen_total_m3": f"{pila.volumen_composicion():.2f}",
                "composicion": composicion,
                "composicion_definitiva": pila.estado == Pila.CERRADA,
                "recepciones_origen": recepciones_origen,
            }
        lineas.append(linea)

    con_pila = [linea for linea in lineas if linea["pila"] is not None]
    advertencias = []
    if not con_pila:
        advertencias.append(
            "Este lote no cuenta con trazabilidad de compostaje registrada: "
            "ninguna linea de la venta tiene pila de origen."
        )
    for linea in con_pila:
        if not linea["pila"]["composicion_definitiva"]:
            advertencias.append(
                f"La pila {linea['pila']['codigo']} sigue en estado "
                f"'{linea['pila']['estado']}'; su composicion aun no es definitiva."
            )
        if not linea["pila"]["recepciones_origen"]:
            advertencias.append(
                f"La pila {linea['pila']['codigo']} no tiene descargas de origen "
                "registradas; la cadena llega hasta su composicion."
            )

    traza(
        "CU-68",
        "venta.trazabilidad",
        venta=venta.pk,
        lineas=len(lineas),
        con_pila=len(con_pila),
        recepciones=sum(len(l["pila"]["recepciones_origen"]) for l in con_pila),
    )
    return {
        "venta": venta.pk,
        "cliente": venta.cliente.razon_social,
        "fecha": venta.fecha,
        "estado": venta.estado,
        "trazable": bool(con_pila),
        "lineas": lineas,
        "advertencias": advertencias,
    }
