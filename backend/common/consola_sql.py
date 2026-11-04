"""Consola de demostracion: el recorrido de cada solicitud, como una secuencia.

Con `TRIVERDE_CONSOLA_SQL=1`, cada llamada a la API imprime su recorrido por
las capas: que pidio la Vista, que Controlador la atendio y que sentencias
llego a ejecutar sobre las tablas fisicas, en el orden de los diagramas de
secuencia. Sin esa variable el middleware se descarta al arrancar y no tiene
ningun costo. Se ve con `docker compose logs -f --no-log-prefix --tail 0 web`.
"""
import os
import re
import time

from django.core.exceptions import MiddlewareNotUsed
from django.db import connection

LARGO_MAXIMO = 170
# Ruido que no aporta a la secuencia del caso de uso.
IGNORADAS = ("authtoken_token", "acceso_rol", "SAVEPOINT")


def compactar_sql(sql, params=None):
    """Deja una sentencia legible: sin lista de columnas ni comillas."""
    texto = sql
    if params:
        try:
            texto = sql % tuple(
                f"'{p}'" if isinstance(p, str) else p for p in params
            )
        except (TypeError, ValueError):
            pass
    texto = texto.replace('"', "")
    texto = re.sub(r"^SELECT .*? FROM ", "SELECT ... FROM ", texto, flags=re.S)
    texto = re.sub(r"^INSERT INTO (\S+) \(.*?\) VALUES", r"INSERT INTO \1 VALUES", texto, flags=re.S)
    texto = re.sub(r"\S+\.(\w+)", r"\1", texto) if texto.startswith("SELECT") else texto
    if len(texto) > LARGO_MAXIMO:
        return texto[: LARGO_MAXIMO - 3] + "..."
    return texto


def nombre_controlador(view_func):
    """Nombre canonico del controlador (`C_...` del docstring) y su accion."""
    clase = getattr(view_func, "cls", None)
    if clase is None:
        return getattr(view_func, "__name__", "vista")
    canonico = re.search(r"C_\w+", clase.__doc__ or "")
    return canonico.group(0) if canonico else clase.__name__


class ConsolaSqlMiddleware:
    def __init__(self, get_response):
        if os.environ.get("TRIVERDE_CONSOLA_SQL") != "1":
            raise MiddlewareNotUsed
        self.get_response = get_response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.path.startswith("/api/") or request.method == "OPTIONS":
            return None
        acciones = getattr(view_func, "actions", None) or {}
        accion = acciones.get(request.method.lower(), request.method.lower())
        print(f"    C   {nombre_controlador(view_func)}.{accion}()", flush=True)
        return None

    def __call__(self, request):
        if not request.path.startswith("/api/") or request.method == "OPTIONS":
            return self.get_response(request)

        print(f"\nV -> {request.method} {request.path}", flush=True)
        contador = {"sql": 0}

        def trazar(execute, sql, params, many, context):
            if not any(ignorada in sql for ignorada in IGNORADAS):
                contador["sql"] += 1
                print(f"    BD  {compactar_sql(sql, params)}", flush=True)
            return execute(sql, params, many, context)

        inicio = time.perf_counter()
        with connection.execute_wrapper(trazar):
            respuesta = self.get_response(request)
        milisegundos = (time.perf_counter() - inicio) * 1000
        print(
            f"V <- {respuesta.status_code} "
            f"({contador['sql']} sentencias, {milisegundos:.0f} ms)",
            flush=True,
        )
        return respuesta
