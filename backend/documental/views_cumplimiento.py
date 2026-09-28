"""C_CumplimientoDocumental (docs/13): Parte F del modulo 12 (CU-91).

Solo lectura: consultar el tablero no modifica ningun documento. La consulta es
de Administrador, igual que el resto de la gestion documental.

Vive en su propio archivo, separado de `views.py` (Parte E), para que las dos
mitades del modulo puedan avanzar sin pisarse.
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsAdministrador
from common.trazas import traza

from . import cumplimiento


class CumplimientoDocumentalViewSet(viewsets.ViewSet):
    """Tablero de cumplimiento documental."""

    permission_classes = [IsAdministrador]

    @action(detail=False, methods=["get"])
    def tablero(self, request):
        """CU-91: resumen por estado, detalle priorizado y pendientes de vigencia.

        Acepta `?tipo=` para acotar por tipo de documento.
        """
        tipo = request.query_params.get("tipo")
        datos = cumplimiento.armar_tablero(tipo)
        traza(
            "CU-91",
            "tablero.consultado",
            tipo=tipo or "todos",
            total=datos["total"],
            pendientes=len(datos["pendientes"]),
            sin_vigencia=len(datos["sin_vigencia"]),
        )
        return Response(datos)
