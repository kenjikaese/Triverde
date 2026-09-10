from django.db import transaction
from django.utils import timezone

from .models import Alerta


@transaction.atomic
def activar_alerta(*, origen, clave, nivel, mensaje, mantencion=None):
    """Crea o actualiza una alerta activa sin duplicarla.

    La clave es responsabilidad del dominio que genera la alerta. M11 usa
    ``mantencion:<id>``; M6 puede usar ``mezcla:pila:<id>:<categoria>`` cuando
    el modelo Pila se integre desde M5.
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
    """Resuelve una alerta conservándola como historial."""
    if alerta.estado == Alerta.RESUELTA:
        return alerta
    alerta.estado = Alerta.RESUELTA
    alerta.fecha_resuelta = timezone.now()
    alerta.resuelta_por = usuario
    alerta.save(update_fields=["estado", "fecha_resuelta", "resuelta_por"])
    return alerta
