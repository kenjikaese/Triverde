"""Sincronizacion offline de los procesos de pila (CU-33 + CU-37 a CU-42).

El operador registra los procesos en el patio, donde la senal es intermitente,
asi que `ProcesoPila` hereda de `SincronizableModel` igual que la recepcion del
Incremento 1. Este modulo es el equivalente de `_sincronizar_recepcion`: recibe
una operacion de la cola local y la aplica una sola vez.

La idempotencia se apoya en el `id_local` (UUID generado en el dispositivo):
reenviar el mismo lote no vuelve a mover el inventario. Vive aqui, y no en
`recepcion/views.py`, para que el modulo 4 solo tenga que despachar por tipo.
"""
from .models import ProcesoPila
from .serializers import ProcesoPilaSerializer


def sincronizar_proceso_pila(id_local, datos, request=None):
    """Aplica una operacion 'proceso_pila' de la cola offline.

    Devuelve el mismo diccionario de resultado que usa la recepcion, para que
    el endpoint responda igual sin importar el tipo de operacion.
    """
    existente = ProcesoPila.objects.filter(id_local=id_local).first()
    if existente is not None:
        if existente.estado_sincronizacion == ProcesoPila.SINCRONIZADA:
            # Ya estaba aplicado: no se mueve el inventario de nuevo.
            return {
                "id_local": str(id_local),
                "estado": "sincronizada",
                "id_servidor": existente.pk,
            }
        existente.estado_sincronizacion = ProcesoPila.EN_CONFLICTO
        existente.save(update_fields=["estado_sincronizacion"])
        return {
            "id_local": str(id_local),
            "estado": "en conflicto",
            "motivo": "El proceso ya existe en el servidor en un estado "
            "incompatible con la sincronizacion.",
        }

    datos_serializer = dict(datos)
    datos_serializer.setdefault("id_local", str(id_local))
    serializer = ProcesoPilaSerializer(
        data=datos_serializer, context={"request": request}
    )
    serializer.is_valid(raise_exception=True)
    operador = getattr(request, "user", None)
    proceso = serializer.save(
        operador=operador if operador is not None and operador.is_authenticated else None
    )
    proceso.estado_sincronizacion = ProcesoPila.SINCRONIZADA
    proceso.save(update_fields=["estado_sincronizacion"])
    return {
        "id_local": str(id_local),
        "estado": "sincronizada",
        "id_servidor": proceso.pk,
    }
