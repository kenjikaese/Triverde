"""Reglas de negocio de la gestion documental, Parte E (CU-86 a CU-89).

La vista solo orquesta: validar el archivo, derivar el estado desde la
vigencia, versionar el archivo y renovar viven aca. Los parametros del modulo
(umbral de proximidad y tamano maximo del archivo) son `ParametroConversion`
configurables; si no existen se usa un valor por defecto.
"""
import os
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from common.trazas import traza
from configuracion.models import ParametroConversion

from .models import DocumentoLegal, VersionDocumento

CLAVE_UMBRAL_DIAS = "alerta_documento_dias"
CLAVE_TAMANO_MAX_MB = "documento_tamano_max_mb"
UMBRAL_DIAS_DEFECTO = 30
TAMANO_MAX_MB_DEFECTO = 10
EXTENSIONES_PERMITIDAS = (".pdf", ".jpg", ".jpeg", ".png")


class ReglaDocumental(Exception):
    """Una regla de los CU impide la operacion; `campo` indica el dato a corregir."""

    def __init__(self, mensaje, campo=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo


class RenovacionInnecesaria(Exception):
    """CU-89, Excepcion 1: el documento esta vigente y lejos de vencer."""

    def __init__(self, documento):
        super().__init__("El documento esta vigente y no requiere renovacion.")
        self.documento = documento


def _parametro(clave, defecto):
    parametro = ParametroConversion.objects.filter(clave=clave).first()
    if parametro is None or parametro.valor <= 0:
        return Decimal(defecto)
    return parametro.valor


def umbral_dias():
    return int(_parametro(CLAVE_UMBRAL_DIAS, UMBRAL_DIAS_DEFECTO))


def tamano_max_mb():
    return _parametro(CLAVE_TAMANO_MAX_MB, TAMANO_MAX_MB_DEFECTO)


def calcular_estado(fecha_vencimiento, hoy=None, umbral=None):
    """Deriva el estado de la vigencia (CU-88).

    Sin vencimiento: sin vigencia. Vencimiento pasado: vencido (Excepcion 3).
    Dentro del umbral de proximidad: por vencer. Si no: vigente.
    """
    if fecha_vencimiento is None:
        return DocumentoLegal.SIN_VIGENCIA
    hoy = hoy or timezone.localdate()
    umbral = umbral_dias() if umbral is None else umbral
    if fecha_vencimiento < hoy:
        return DocumentoLegal.VENCIDO
    if fecha_vencimiento <= hoy + timedelta(days=umbral):
        return DocumentoLegal.POR_VENCER
    return DocumentoLegal.VIGENTE


def posibles_duplicados(nombre, entidad_emisora, excluir_id=None):
    """CU-86, Excepcion 3: mismo nombre y misma entidad emisora."""
    queryset = DocumentoLegal.objects.filter(
        nombre__iexact=nombre.strip(), entidad_emisora__iexact=entidad_emisora.strip()
    )
    if excluir_id:
        queryset = queryset.exclude(pk=excluir_id)
    return list(queryset)


def validar_archivo(archivo):
    """CU-87/CU-89, Excepcion 2: formato soportado y tamano maximo configurado."""
    if archivo is None:
        raise ReglaDocumental("Debe seleccionar un archivo.", "archivo")
    extension = os.path.splitext(archivo.name)[1].lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        raise ReglaDocumental(
            "Formato no soportado. Se aceptan: "
            + ", ".join(e.lstrip(".").upper() for e in EXTENSIONES_PERMITIDAS)
            + ".",
            "archivo",
        )
    maximo = tamano_max_mb()
    if archivo.size > maximo * 1024 * 1024:
        raise ReglaDocumental(
            f"El archivo excede el tamano maximo configurado de {maximo.normalize():f} MB.",
            "archivo",
        )


def validar_rango(fecha_emision, fecha_vencimiento):
    """CU-88, Excepcion 2: ambas fechas y vencimiento no anterior a emision."""
    if fecha_emision is None:
        raise ReglaDocumental(
            "Ingrese una fecha de emision valida (AAAA-MM-DD).", "fecha_emision"
        )
    if fecha_vencimiento is None:
        raise ReglaDocumental(
            "Ingrese una fecha de vencimiento valida (AAAA-MM-DD).", "fecha_vencimiento"
        )
    if fecha_vencimiento < fecha_emision:
        raise ReglaDocumental(
            "La fecha de vencimiento no puede ser anterior a la fecha de emision.",
            "fecha_vencimiento",
        )


def _nueva_version(documento, archivo, usuario):
    """Crea la version vigente y deja la anterior en el historial (CU-87 Exc. 3)."""
    documento.versiones.filter(vigente=True).update(vigente=False)
    siguiente = (documento.versiones.aggregate(maximo=Max("version"))["maximo"] or 0) + 1
    return VersionDocumento.objects.create(
        documento=documento,
        archivo=archivo,
        nombre_archivo=os.path.basename(archivo.name)[:255],
        version=siguiente,
        usuario=usuario if usuario and usuario.is_authenticated else None,
        vigente=True,
        fecha_emision=documento.fecha_emision,
        fecha_vencimiento=documento.fecha_vencimiento,
    )


def adjuntar_archivo(documento, archivo, usuario):
    """CU-87: adjunta el archivo como nueva version vigente."""
    validar_archivo(archivo)
    with transaction.atomic():
        documento = DocumentoLegal.objects.select_for_update().get(pk=documento.pk)
        version = _nueva_version(documento, archivo, usuario)
    traza(
        "CU-87", "documento.archivo_adjuntado", documento=documento.pk, version=version.version
    )
    return version


def registrar_vigencia(documento, fecha_emision, fecha_vencimiento):
    """CU-88: registra las fechas y deriva el estado."""
    validar_rango(fecha_emision, fecha_vencimiento)
    documento.fecha_emision = fecha_emision
    documento.fecha_vencimiento = fecha_vencimiento
    documento.estado = calcular_estado(fecha_vencimiento)
    documento.save(update_fields=["fecha_emision", "fecha_vencimiento", "estado"])
    traza(
        "CU-88",
        "documento.vigencia_registrada",
        documento=documento.pk,
        vencimiento=fecha_vencimiento,
        estado=documento.estado,
    )
    return documento


def _resolver_alerta_de_vencimiento(documento, usuario):
    """Un documento renovado sale de la revision: su alerta activa se resuelve."""
    from mezcla.models import Alerta
    from mezcla.services import resolver_alerta

    for alerta in Alerta.objects.filter(
        origen=Alerta.DOCUMENTO, documento=documento, estado=Alerta.ACTIVA
    ):
        resolver_alerta(alerta, usuario if usuario and usuario.is_authenticated else None)


def renovar(documento, archivo, fecha_emision, fecha_vencimiento, usuario, confirmar=False):
    """CU-89: suma una version con el nuevo archivo y la nueva vigencia."""
    if documento.estado == DocumentoLegal.VIGENTE and not confirmar:
        raise RenovacionInnecesaria(documento)
    validar_archivo(archivo)
    validar_rango(fecha_emision, fecha_vencimiento)
    if documento.fecha_vencimiento and fecha_vencimiento <= documento.fecha_vencimiento:
        raise ReglaDocumental(
            "La nueva fecha de vencimiento debe ser posterior a la vigencia actual "
            f"({documento.fecha_vencimiento.isoformat()}).",
            "fecha_vencimiento",
        )
    with transaction.atomic():
        documento = DocumentoLegal.objects.select_for_update().get(pk=documento.pk)
        documento.fecha_emision = fecha_emision
        documento.fecha_vencimiento = fecha_vencimiento
        documento.estado = calcular_estado(fecha_vencimiento)
        documento.save(update_fields=["fecha_emision", "fecha_vencimiento", "estado"])
        version = _nueva_version(documento, archivo, usuario)
        _resolver_alerta_de_vencimiento(documento, usuario)
    traza(
        "CU-89",
        "documento.renovado",
        documento=documento.pk,
        version=version.version,
        vencimiento=fecha_vencimiento,
        estado=documento.estado,
    )
    return documento, version
