"""Disparadores automaticos y recálculos del indicador ambiental."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from configuracion.models import ParametroConversion
from inventario.models import ComposicionPila, Pila
from recepcion.models import DetalleRecepcion, Recepcion

from .services import (
    CLAVE_CO2_CAMION,
    CLAVE_CO2_COMPOSTAJE,
    recalcular_pila,
    recalcular_por_parametro,
    recalcular_recepcion,
)


@receiver(post_save, sender=Recepcion, dispatch_uid="m09_indicador_recepcion")
def recepcion_actualizada(sender, instance, **kwargs):
    recalcular_recepcion(instance)


@receiver(
    [post_save, post_delete],
    sender=DetalleRecepcion,
    dispatch_uid="m09_indicador_detalle_recepcion",
)
def detalle_recepcion_actualizado(sender, instance, **kwargs):
    recalcular_recepcion(instance.recepcion)


@receiver(post_save, sender=Pila, dispatch_uid="m09_indicador_pila")
def pila_actualizada(sender, instance, **kwargs):
    recalcular_pila(instance)


@receiver(
    [post_save, post_delete],
    sender=ComposicionPila,
    dispatch_uid="m09_indicador_composicion_pila",
)
def composicion_actualizada(sender, instance, **kwargs):
    recalcular_pila(instance.pila)


@receiver(
    [post_save, post_delete],
    sender=ParametroConversion,
    dispatch_uid="m09_indicador_parametro",
)
def parametro_ambiental_actualizado(sender, instance, **kwargs):
    if instance.clave in {CLAVE_CO2_CAMION, CLAVE_CO2_COMPOSTAJE}:
        recalcular_por_parametro(instance.clave)

