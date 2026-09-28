"""Modulo 12 - Parte F: alertas de vencimiento, tablero e historial (CU-90 a CU-92).

Consume los objetos de la Parte E (`DocumentoLegal`, `VersionDocumento`) y la
`Alerta` compartida, que ya trae su FK `documento`. No modifica la app `mezcla`:
las alertas de este origen se crean y se mantienen desde aca, igual que hace el
modulo 6 con las suyas, apoyandose en la restriccion
`alerta_documento_activa_unica`.

La derivacion del estado no se reimplementa: se reusa `services.calcular_estado`,
la misma regla que aplica la Parte E al registrar la vigencia (CU-88). Si cada
mitad calculara el estado por su cuenta, el tablero y la ficha del documento
podrian terminar diciendo cosas distintas.
"""
from django.db import transaction
from django.utils import timezone

from common.trazas import traza
from mezcla.models import Alerta

from . import services
from .models import DocumentoLegal

# La urgencia de la alerta sigue al estado del documento.
NIVEL_POR_ESTADO = {
    DocumentoLegal.POR_VENCER: Alerta.ADVERTENCIA,
    DocumentoLegal.VENCIDO: Alerta.CRITICA,
}


def _clave(documento):
    """Identificador estable de la alerta, como `mantencion:<id>` en el M11."""
    return f"documento:{documento.pk}"


def _mensaje(documento, dias):
    vencimiento = documento.fecha_vencimiento.strftime("%d-%m-%Y")
    if documento.estado == DocumentoLegal.VENCIDO:
        return (
            f"{documento.nombre} ({documento.entidad_emisora}) vencio hace "
            f"{abs(dias)} dia(s), el {vencimiento}."
        )
    return (
        f"{documento.nombre} ({documento.entidad_emisora}) vence en {dias} dia(s), "
        f"el {vencimiento}."
    )


@transaction.atomic
def revisar_vencimientos(hoy=None):
    """CU-90: revisa las vigencias y genera o mantiene la alerta de cada documento.

    Excepcion 1: sin umbral configurado, `services.umbral_dias()` aplica el valor
    por defecto y la revision sigue su curso.
    Excepcion 2: si el documento ya tiene una alerta activa, se actualiza en vez
    de crear una segunda.
    Excepcion 3: un documento renovado vuelve a `vigente` y la Parte E resuelve su
    alerta al renovar, asi que deja de aparecer en esta revision.

    Devuelve un resumen para el command y para las pruebas.
    """
    hoy = hoy or timezone.localdate()
    umbral = services.umbral_dias()
    resumen = {
        "revisados": 0,
        "por_vencer": 0,
        "vencidos": 0,
        "alertas_creadas": 0,
        "alertas_mantenidas": 0,
    }

    # El CU nombra los estados "vigente" y "por vencer", pero un documento puede
    # nacer vencido: si se registra con una vigencia ya pasada, CU-88 lo deriva
    # a "vencido" en el acto y nunca pasaria por aca. Se incluye para que tenga
    # su alerta igual (criterio de aceptacion 2 del spec).
    documentos = DocumentoLegal.objects.filter(
        estado__in=[
            DocumentoLegal.VIGENTE,
            DocumentoLegal.POR_VENCER,
            DocumentoLegal.VENCIDO,
        ],
        fecha_vencimiento__isnull=False,
    ).order_by("fecha_vencimiento", "id")

    for documento in documentos:
        resumen["revisados"] += 1
        estado_anterior = documento.estado
        documento.estado = services.calcular_estado(
            documento.fecha_vencimiento, hoy, umbral
        )
        if documento.estado != estado_anterior:
            documento.save(update_fields=["estado"])
            traza(
                "CU-90",
                "documento.estado",
                documento=documento.pk,
                transicion=f"{estado_anterior}->{documento.estado}",
            )

        nivel = NIVEL_POR_ESTADO.get(documento.estado)
        if nivel is None:
            # Sigue lejos de vencer: no corresponde alertar.
            continue

        dias = (documento.fecha_vencimiento - hoy).days
        mensaje = _mensaje(documento, dias)
        if documento.estado == DocumentoLegal.VENCIDO:
            resumen["vencidos"] += 1
        else:
            resumen["por_vencer"] += 1

        alerta = Alerta.objects.filter(
            origen=Alerta.DOCUMENTO, documento=documento, estado=Alerta.ACTIVA
        ).first()
        if alerta is None:
            Alerta.objects.create(
                origen=Alerta.DOCUMENTO,
                clave=_clave(documento),
                documento=documento,
                nivel=nivel,
                mensaje=mensaje,
            )
            resumen["alertas_creadas"] += 1
            traza(
                "CU-90", "alerta.generada", documento=documento.pk, nivel=nivel, dias=dias
            )
        else:
            # Excepcion 2: la que ya existe se mantiene; solo se pone al dia su
            # urgencia y su texto (un "por vencer" puede haber pasado a vencido).
            if alerta.nivel != nivel or alerta.mensaje != mensaje:
                alerta.nivel = nivel
                alerta.mensaje = mensaje
                alerta.save(update_fields=["nivel", "mensaje"])
            resumen["alertas_mantenidas"] += 1
            traza(
                "CU-90", "alerta.mantenida", documento=documento.pk, nivel=nivel, dias=dias
            )

    return resumen


def _fila(documento, hoy, alertas):
    alerta = alertas.get(documento.pk)
    return {
        "id": documento.pk,
        "nombre": documento.nombre,
        "tipo": documento.tipo,
        "tipo_display": documento.get_tipo_display(),
        "entidad_emisora": documento.entidad_emisora,
        "fecha_vencimiento": (
            documento.fecha_vencimiento.isoformat()
            if documento.fecha_vencimiento
            else None
        ),
        "dias_restantes": (
            (documento.fecha_vencimiento - hoy).days
            if documento.fecha_vencimiento
            else None
        ),
        "estado": documento.estado,
        "estado_display": documento.get_estado_display(),
        "alerta_nivel": alerta.nivel if alerta else None,
    }


def armar_tablero(tipo=None):
    """CU-91: resumen por estado y detalle priorizado. Solo lectura.

    Excepcion 1: sin documentos registrados, el resumen viene en cero.
    Excepcion 2: si no hay ninguno por vencer ni vencido, esas categorias van en
    cero igual; no es un error.
    Excepcion 3: los documentos sin vigencia definida van en su propia lista y no
    entran en los conteos de vigente / por vencer / vencido.
    """
    hoy = timezone.localdate()
    documentos = DocumentoLegal.objects.all()
    if tipo:
        documentos = documentos.filter(tipo=tipo)

    alertas = {
        alerta.documento_id: alerta
        for alerta in Alerta.objects.filter(
            origen=Alerta.DOCUMENTO, estado=Alerta.ACTIVA
        )
    }

    resumen = {estado: 0 for estado, _ in DocumentoLegal.ESTADO_CHOICES}
    pendientes = []
    sin_vigencia = []
    for documento in documentos:
        resumen[documento.estado] = resumen.get(documento.estado, 0) + 1
        fila = _fila(documento, hoy, alertas)
        if documento.estado == DocumentoLegal.SIN_VIGENCIA:
            sin_vigencia.append(fila)
        elif documento.estado in NIVEL_POR_ESTADO:
            pendientes.append(fila)

    # Por proximidad de vencimiento: primero lo mas atrasado. El orden se hace
    # aca y no en la consulta porque cada motor ordena los nulos distinto.
    pendientes.sort(key=lambda fila: fila["dias_restantes"])
    sin_vigencia.sort(key=lambda fila: fila["nombre"])

    return {
        "resumen": resumen,
        "total": sum(resumen.values()),
        "umbral_dias": services.umbral_dias(),
        "pendientes": pendientes,
        "sin_vigencia": sin_vigencia,
    }


def historial(documento):
    """CU-92: versiones de la mas reciente a la mas antigua."""
    return documento.versiones.select_related("usuario").order_by("-version")
