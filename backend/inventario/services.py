"""CU-44 - Servicio de movimientos de inventario.

Punto unico por donde cambia el `Inventario`. Ningun otro modulo escribe la
tabla directamente: se llama a `aplicar_movimiento()` -o a `ingresar()` para la
entrada del material a la planta-, que validan el saldo antes de mover y nunca
dejan una cantidad en negativo (CU-44 Excepcion 2).

Las funciones asumen que quien llama abrio una transaccion (`transaction.atomic`)
y bloquean la fila con `select_for_update()` para que dos registros simultaneos
no se pisen. En SQLite el bloqueo no aplica y Django lo ignora; en PostgreSQL,
que es la base del proyecto, si toma efecto.
"""
from decimal import Decimal

from rest_framework import serializers

from .models import Inventario

CERO = Decimal("0.00")


def _saldo(material, etapa):
    """Devuelve (creando si falta) la fila de saldo de un material en una etapa.

    Crear la fila en cero es deliberado: CU-34 Excepcion 1 pide mostrar cero
    para las combinaciones sin movimiento, no tratarlas como un error.
    """
    saldo, _ = Inventario.objects.select_for_update().get_or_create(
        material=material, etapa=etapa, defaults={"volumen_m3": CERO}
    )
    return saldo


def _validar_volumen(volumen, campo="volumen_m3"):
    """Exige un volumen numerico y mayor a cero."""
    try:
        cantidad = Decimal(str(volumen))
    except (ArithmeticError, TypeError, ValueError):
        raise serializers.ValidationError(
            {campo: "El volumen debe ser un numero valido."}
        )
    if cantidad <= CERO:
        raise serializers.ValidationError(
            {campo: "El volumen debe ser mayor a cero."}
        )
    return cantidad


def disponible(material, etapa):
    """Volumen disponible de un material en una etapa (sin crear la fila)."""
    saldo = Inventario.objects.filter(material=material, etapa=etapa).first()
    return saldo.volumen_m3 if saldo else CERO


def ingresar(material, etapa, volumen):
    """Incorpora volumen a una etapa. Es la entrada del material al sistema.

    La usa la recepcion de camiones: lo descargado queda disponible en la
    etapa que corresponda (ver `inventario/signals.py`).
    """
    cantidad = _validar_volumen(volumen)
    saldo = _saldo(material, etapa)
    saldo.volumen_m3 = saldo.volumen_m3 + cantidad
    saldo.save(update_fields=["volumen_m3", "actualizado"])
    return saldo


def descontar(material, etapa, volumen):
    """Descuenta volumen de una etapa sin incorporarlo a ninguna otra.

    Se usa cuando el material sale de una etapa pero su destino todavia no se
    puede calcular: el triturado de un material sin factor de reduccion
    configurado (CU-37 Excepcion 3).

    Rechaza el movimiento completo si el saldo no alcanza (CU-44 Excepcion 2):
    no deja cantidades en negativo.
    """
    cantidad = _validar_volumen(volumen)
    saldo = _saldo(material, etapa)
    if saldo.volumen_m3 < cantidad:
        raise serializers.ValidationError(
            f"No hay suficiente '{material.nombre}' en la etapa '{etapa}': "
            f"disponible {saldo.volumen_m3} m3, se intento mover {cantidad} m3."
        )
    saldo.volumen_m3 = saldo.volumen_m3 - cantidad
    saldo.save(update_fields=["volumen_m3", "actualizado"])
    return saldo


def aplicar_movimiento(material, origen, destino, volumen_origen, volumen_destino=None):
    """Mueve material de una etapa a otra (CU-44).

    `volumen_destino` permite que lo que sale y lo que entra no sean iguales:
    en el triturado salen N m3 de rama y entran N/factor m3 de chip. Si se
    omite, entra lo mismo que salio.

    Rechaza el movimiento completo si el origen no alcanza (CU-44 Excepcion 2):
    no deja saldos negativos ni movimientos a medias.
    """
    entrante = (
        _validar_volumen(volumen_origen)
        if volumen_destino is None
        else _validar_volumen(volumen_destino)
    )
    saldo_origen = descontar(material, origen, volumen_origen)
    saldo_destino = _saldo(material, destino)
    saldo_destino.volumen_m3 = saldo_destino.volumen_m3 + entrante
    saldo_destino.save(update_fields=["volumen_m3", "actualizado"])
    return saldo_origen, saldo_destino


def etapa_origen_para_pila(material):
    """Etapa desde la que un material entra a una pila (CU-36).

    El material que se tritura entra a la pila ya convertido en chip; el
    material verde entra directo desde la etapa en que quedo al recibirse.
    """
    return Inventario.CHIP if material.admite_chip else Inventario.POR_TRITURAR
