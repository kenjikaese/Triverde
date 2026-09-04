"""Trazas de seguimiento por caso de uso.

Sirven para verificar, desde una prueba end-to-end, que una operacion paso por
donde se espera: que el calculo ocurrio en el servidor y no en el navegador, y
que las transiciones de estado las hizo el servicio y no un atajo.

Una prueba de interfaz puede quedar verde por el camino equivocado --por
ejemplo, si la vista replicara la formula del CU-55 en JavaScript, la pantalla
mostraria el numero correcto pero se estaria violando el patron por capas--.
La traza distingue esos dos casos.

Formato de cada linea, pensado para ser legible y facil de afirmar:

    CU-55 cotizacion.calculada distancia=10 recorrido=20 costo=20000

Se emiten por el logger `triverde.cu`. En desarrollo y en las pruebas e2e
(`TRIVERDE_TRAZAS=1`) van tambien a `logs/trazas-cu.log`; en produccion el
logger no tiene handler de archivo y la llamada es practicamente gratis.
"""
import logging

logger = logging.getLogger("triverde.cu")


def traza(cu, evento, **datos):
    """Registra el paso por un punto de negocio.

    `cu` es el identificador del caso de uso ("CU-55"), `evento` un nombre
    corto en notacion objeto.accion ("cotizacion.calculada") y `datos` los
    valores relevantes para afirmar sobre ellos.
    """
    partes = " ".join(f"{clave}={valor}" for clave, valor in datos.items())
    logger.info("%s %s %s", cu, evento, partes)
