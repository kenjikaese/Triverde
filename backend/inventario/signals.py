"""CU-44 - Entrada del material recibido al inventario.

El inventario se deriva de las recepciones y de los procesos (CU-34). Los
procesos lo mueven desde `serializers.py`; lo que entra por porteria lo
incorpora este disparador, para no tener que tocar el modulo de recepcion.

Se dispara al crear un `DetalleRecepcion` (la linea material+volumen de un
camion) y deja el material en la etapa 'por triturar', que es donde queda todo
lo descargado hasta que se tritura o se incorpora a una pila. El material que
va a venta directa no entra al circuito de compostaje y no se inventaria.
"""
from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from recepcion.models import DetalleRecepcion, Recepcion

from . import services
from .models import Inventario

CERO = Decimal("0.00")


@receiver(post_save, sender=DetalleRecepcion, dispatch_uid="inventario_ingreso_recepcion")
def ingresar_material_recibido(sender, instance, created, **kwargs):
    """Incorpora al inventario el material de una linea de recepcion recien creada."""
    if not created:
        # Solo el alta mueve stock: editar una linea ya contabilizada exigiria
        # revertir el movimiento anterior, que hoy no esta en el alcance.
        return
    if instance.destino_sugerido == DetalleRecepcion.A_VENTA_DIRECTA:
        return
    if instance.recepcion.estado == Recepcion.RECHAZADA:
        # Lo rechazado no se descarga: no entra al inventario.
        return
    # CU-44 Excepcion 1: sin material o sin cantidad valida no se actualiza.
    if instance.material_id is None or instance.volumen_m3 is None:
        return
    if instance.volumen_m3 <= CERO:
        return
    services.ingresar(
        instance.material, Inventario.POR_TRITURAR, instance.volumen_m3
    )
