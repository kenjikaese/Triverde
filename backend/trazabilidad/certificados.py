"""Certificados de trazabilidad del Modulo 9, Parte A (CU-65 y CU-66).

La logica vive aca y no en la vista: compilar los datos de una descarga o de
un periodo, validar que se puedan certificar y emitir el objeto
`CertificadoTrazabilidad` con su folio. El controlador solo orquesta,
resuelve permisos y audita.
"""
from collections import OrderedDict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from common.trazas import traza
from recepcion.models import Recepcion

from .models import CertificadoTrazabilidad

CERO = Decimal("0.00")


class CertificadoNoGenerable(Exception):
    """La descarga o el periodo no cumplen las precondiciones del CU."""

    def __init__(self, motivo, datos=None):
        super().__init__(motivo)
        self.motivo = motivo
        self.datos = datos or {}


class ConsolidadoPrevio(Exception):
    """CU-66, Excepcion 2: ya existe un consolidado para cliente + periodo."""

    def __init__(self, previo):
        super().__init__("Existe un consolidado previo para el periodo.")
        self.previo = previo


def _dec(valor):
    return f"{(valor if valor is not None else CERO):.2f}"


def _datos_cliente(cliente):
    return {
        "id": cliente.pk,
        "razon_social": cliente.razon_social,
        "rut": cliente.rut,
        "direccion": cliente.direccion,
    }


def compilar_descarga(recepcion):
    """Arma el contenido del certificado por descarga (CU-65).

    Precondiciones del CU: la recepcion esta `recibida` y cada linea tiene su
    peso calculado. Si no se cumplen, no se emite nada (Excepciones 1 y 2).
    """
    if recepcion.estado != Recepcion.RECIBIDA:
        raise CertificadoNoGenerable(
            "Solo se certifican descargas en estado 'recibida'; esta descarga "
            f"esta '{recepcion.estado}'.",
            {"estado": recepcion.estado},
        )
    detalles = list(recepcion.detalles.select_related("material"))
    if not detalles:
        raise CertificadoNoGenerable(
            "La descarga no tiene material registrado; no hay nada que certificar."
        )
    # El peso se deriva al registrar la linea y la columna no admite nulos;
    # "sin peso calculado" es entonces un peso en cero (densidad o volumen
    # no informados), que no sirve para certificar.
    sin_peso = [
        d.material.nombre
        for d in detalles
        if d.peso_derivado_kg is None or d.peso_derivado_kg <= CERO
    ]
    if sin_peso:
        raise CertificadoNoGenerable(
            "Falta el peso calculado del material; complete la conversion a "
            "peso antes de certificar.",
            {"sin_peso": sin_peso},
        )

    lineas = []
    total_volumen = CERO
    total_peso = CERO
    for detalle in detalles:
        lineas.append(
            {
                "material": detalle.material.nombre,
                "volumen_m3": _dec(detalle.volumen_m3),
                "peso_kg": _dec(detalle.peso_derivado_kg),
            }
        )
        total_volumen += detalle.volumen_m3
        total_peso += detalle.peso_derivado_kg

    return {
        "tipo": CertificadoTrazabilidad.DESCARGA,
        "recepcion": recepcion.pk,
        "cliente": _datos_cliente(recepcion.cliente),
        "transportista": recepcion.transportista.nombre if recepcion.transportista else None,
        "vehiculo": recepcion.vehiculo.patente if recepcion.vehiculo else None,
        "conductor": recepcion.conductor,
        "fecha": recepcion.fecha.isoformat(),
        "hora": recepcion.hora.strftime("%H:%M"),
        "materiales": lineas,
        "totales": {"volumen_m3": _dec(total_volumen), "peso_kg": _dec(total_peso)},
    }


def generar_certificado_descarga(recepcion):
    """Emite el certificado por descarga (CU-65).

    Una descarga se certifica una sola vez: si ya tiene certificado, se
    devuelve el existente (`creado=False`) en vez de duplicar el folio.
    """
    existente = (
        CertificadoTrazabilidad.objects.filter(
            tipo=CertificadoTrazabilidad.DESCARGA, recepcion=recepcion
        )
        .order_by("-id")
        .first()
    )
    if existente:
        traza("CU-65", "certificado.existente", recepcion=recepcion.pk, codigo=existente.codigo)
        return existente, False

    contenido = compilar_descarga(recepcion)
    with transaction.atomic():
        certificado = CertificadoTrazabilidad.objects.create(
            tipo=CertificadoTrazabilidad.DESCARGA,
            cliente=recepcion.cliente,
            recepcion=recepcion,
            codigo=CertificadoTrazabilidad.generar_codigo(timezone.localdate().year),
            contenido=contenido,
        )
        certificado.contenido["codigo"] = certificado.codigo
        certificado.contenido["fecha_emision"] = certificado.fecha_emision.isoformat()
        certificado.save(update_fields=["contenido"])
    traza(
        "CU-65",
        "certificado.emitido",
        recepcion=recepcion.pk,
        codigo=certificado.codigo,
        peso_kg=contenido["totales"]["peso_kg"],
    )
    return certificado, True


def compilar_consolidado(cliente, periodo_inicio, periodo_fin):
    """Agrupa las descargas recibidas del cliente en el periodo (CU-66).

    Suma volumen y peso por tipo de material. Sin descargas recibidas en el
    periodo, no hay consolidado que emitir (Excepcion 1).
    """
    recepciones = (
        Recepcion.objects.filter(
            cliente=cliente,
            estado=Recepcion.RECIBIDA,
            fecha__gte=periodo_inicio,
            fecha__lte=periodo_fin,
        )
        .prefetch_related("detalles__material")
        .order_by("fecha", "id")
    )
    if not recepciones.exists():
        raise CertificadoNoGenerable(
            "El cliente no tiene descargas recibidas en el periodo indicado."
        )

    por_material = OrderedDict()
    total_volumen = CERO
    total_peso = CERO
    ids = []
    for recepcion in recepciones:
        ids.append(recepcion.pk)
        for detalle in recepcion.detalles.all():
            grupo = por_material.setdefault(
                detalle.material.nombre,
                {"volumen": CERO, "peso": CERO, "descargas": set()},
            )
            grupo["volumen"] += detalle.volumen_m3
            grupo["peso"] += detalle.peso_derivado_kg or CERO
            grupo["descargas"].add(recepcion.pk)
            total_volumen += detalle.volumen_m3
            total_peso += detalle.peso_derivado_kg or CERO

    return {
        "tipo": CertificadoTrazabilidad.CONSOLIDADO,
        "cliente": _datos_cliente(cliente),
        "periodo": {"inicio": periodo_inicio.isoformat(), "fin": periodo_fin.isoformat()},
        "materiales": [
            {
                "material": nombre,
                "volumen_m3": _dec(g["volumen"]),
                "peso_kg": _dec(g["peso"]),
                "descargas": len(g["descargas"]),
            }
            for nombre, g in por_material.items()
        ],
        "totales": {
            "volumen_m3": _dec(total_volumen),
            "peso_kg": _dec(total_peso),
            "descargas": len(ids),
        },
        "recepciones": ids,
    }


def generar_consolidado(cliente, periodo_inicio, periodo_fin, confirmar=False):
    """Emite el consolidado mensual del cliente (CU-66).

    Si ya existe uno para el mismo cliente y periodo, se exige confirmacion
    (Excepcion 2). Al confirmar se emite una nueva version: la anterior se
    conserva en el historial, nunca se borra.
    """
    previos = CertificadoTrazabilidad.objects.filter(
        tipo=CertificadoTrazabilidad.CONSOLIDADO,
        cliente=cliente,
        periodo_inicio=periodo_inicio,
        periodo_fin=periodo_fin,
    ).order_by("-id")
    previo = previos.first()
    if previo and not confirmar:
        traza("CU-66", "consolidado.previo", cliente=cliente.pk, codigo=previo.codigo)
        raise ConsolidadoPrevio(previo)

    contenido = compilar_consolidado(cliente, periodo_inicio, periodo_fin)
    contenido["version"] = previos.count() + 1
    with transaction.atomic():
        certificado = CertificadoTrazabilidad.objects.create(
            tipo=CertificadoTrazabilidad.CONSOLIDADO,
            cliente=cliente,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            codigo=CertificadoTrazabilidad.generar_codigo(timezone.localdate().year),
            contenido=contenido,
        )
        certificado.contenido["codigo"] = certificado.codigo
        certificado.contenido["fecha_emision"] = certificado.fecha_emision.isoformat()
        certificado.save(update_fields=["contenido"])
    traza(
        "CU-66",
        "consolidado.emitido",
        cliente=cliente.pk,
        codigo=certificado.codigo,
        version=contenido["version"],
        descargas=contenido["totales"]["descargas"],
    )
    return certificado
