"""Servicio de calculo del Modulo 7 - Proyecciones.

Los calculos son de servidor y usan los parametros vigentes del sistema
(campos del `Material`) mas los supuestos que acompanan la proyeccion. Si falta
un parametro requerido se senala cual y NO se calcula: no se inventan valores
(spec M07, regla de negocio 1). Ningun calculo modifica la configuracion global;
los supuestos son una copia propia de cada proyeccion (CU-54).
"""
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from .models import Proyeccion


class ParametroFaltante(Exception):
    """Falta un parametro requerido para el calculo (no se inventan valores)."""


def _dec(valor, nombre):
    if valor is None or valor == "":
        raise ParametroFaltante(nombre)
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ParametroFaltante(nombre)


class ProyeccionService:
    @classmethod
    def _resolver_supuestos(cls, material, supuestos):
        """Completa los supuestos con los parametros que el sistema si almacena
        (densidad y factor del material). Devuelve una copia nueva."""
        resueltos = dict(supuestos or {})
        if material is not None:
            if material.densidad_kg_m3 is not None:
                resueltos.setdefault("densidad_kg_m3", str(material.densidad_kg_m3))
            if material.factor_reduccion_chip is not None:
                resueltos.setdefault("factor_reduccion", str(material.factor_reduccion_chip))
        return resueltos

    @classmethod
    def calcular(cls, tipo, material=None, supuestos=None):
        """Devuelve (supuestos_resueltos, valor_proyectado)."""
        supuestos = cls._resolver_supuestos(material, supuestos)
        volumen = _dec(supuestos.get("volumen_entrada_m3"), "volumen_entrada_m3")
        if volumen <= 0:
            raise ParametroFaltante("volumen_entrada_m3 (debe ser mayor a 0)")

        if tipo == Proyeccion.MENSUAL:
            valor = cls._mensual(volumen, supuestos)
        elif tipo == Proyeccion.SEMANAL:
            valor = cls._semanal(volumen, supuestos)
        elif tipo == Proyeccion.COMERCIAL:
            valor = cls._comercial(volumen, supuestos)
        else:
            raise ValueError(f"Tipo de proyeccion desconocido: {tipo}")
        return supuestos, valor

    # --- CU-50: mensual de compost (toneladas, m3, sacos) ---
    @classmethod
    def _mensual(cls, volumen, s):
        densidad = _dec(s.get("densidad_kg_m3"), "densidad_kg_m3")
        rendimiento = _dec(s.get("rendimiento_compost"), "rendimiento_compost")
        sacos_por_m3 = _dec(s.get("sacos_por_m3"), "sacos_por_m3")
        m3_compost = volumen * rendimiento
        return {
            "toneladas_entrada": float(round(volumen * densidad / Decimal(1000), 2)),
            "m3_compost": float(round(m3_compost, 2)),
            "sacos": int((m3_compost * sacos_por_m3).to_integral_value()),
        }

    # --- CU-51: semanal por material (aplica densidad y factor propios) ---
    @classmethod
    def _semanal(cls, volumen, s):
        densidad = _dec(s.get("densidad_kg_m3"), "densidad_kg_m3")
        factor = _dec(s.get("factor_reduccion"), "factor_reduccion")
        if factor <= 0:
            raise ParametroFaltante("factor_reduccion (debe ser mayor a 0)")
        return {
            "m3_procesado": float(round(volumen, 2)),
            "toneladas": float(round(volumen * densidad / Decimal(1000), 2)),
            "chip_m3": float(round(volumen / factor, 2)),
        }

    # --- CU-52: rendimiento comercial (sacos, m3, ingreso) ---
    @classmethod
    def _comercial(cls, volumen, s):
        sacos_por_m3 = _dec(s.get("sacos_por_m3"), "sacos_por_m3")
        precio_saco = _dec(s.get("precio_saco"), "precio_saco")
        sacos = (volumen * sacos_por_m3).to_integral_value()
        return {
            "m3": float(round(volumen, 2)),
            "sacos": int(sacos),
            "ingreso_estimado": float(round(Decimal(sacos) * precio_saco, 0)),
        }

    # --- CU-53: comparar proyectado vs real (solo lectura) ---
    @classmethod
    def comparar(cls, proyeccion):
        from recepcion.models import DetalleRecepcion

        parcial = proyeccion.periodo_fin > timezone.localdate()
        detalles = DetalleRecepcion.objects.filter(
            recepcion__fecha__gte=proyeccion.periodo_inicio,
            recepcion__fecha__lte=proyeccion.periodo_fin,
        ).exclude(recepcion__estado="rechazada")
        if proyeccion.material_id:
            detalles = detalles.filter(material_id=proyeccion.material_id)

        tiene_real = detalles.exists()
        real_volumen = sum((d.volumen_m3 for d in detalles), Decimal(0))
        proyectado = _dec(proyeccion.supuestos.get("volumen_entrada_m3"), "volumen_entrada_m3")

        resultado = {
            "parcial": parcial,
            "proyectado_m3": float(round(proyectado, 2)),
            "real_m3": float(round(real_volumen, 2)) if tiene_real else None,
            "desviacion_m3": None,
            "desviacion_pct": None,
        }
        if tiene_real:
            desviacion = real_volumen - proyectado
            resultado["desviacion_m3"] = float(round(desviacion, 2))
            if proyectado:
                resultado["desviacion_pct"] = float(round(desviacion / proyectado * 100, 1))
        if proyeccion.tipo == Proyeccion.COMERCIAL:
            resultado["ingreso_real"] = cls._ingreso_real(proyeccion)
        return resultado

    @staticmethod
    def _ingreso_real(proyeccion):
        """Ingreso real del periodo si el Modulo 8 (comercial) esta instalado.
        Mientras M8 no este integrado devuelve None (comparacion no disponible)."""
        from django.apps import apps

        try:
            Venta = apps.get_model("comercial", "Venta")
        except LookupError:
            return None
        ventas = Venta.objects.filter(
            fecha__gte=proyeccion.periodo_inicio,
            fecha__lte=proyeccion.periodo_fin,
        )
        if not ventas.exists():
            return None
        total = sum((getattr(v, "total", None) or Decimal(0) for v in ventas), Decimal(0))
        return float(round(total, 0))

    # --- CU-54: ajustar supuestos y recalcular (sin tocar config global) ---
    @classmethod
    def ajustar(cls, proyeccion, nuevos_supuestos):
        supuestos = dict(proyeccion.supuestos)
        if "_escenario_base" not in supuestos:
            supuestos["_escenario_base"] = {
                "supuestos": {k: v for k, v in proyeccion.supuestos.items()
                              if not k.startswith("_")},
                "valor_proyectado": proyeccion.valor_proyectado,
            }
        supuestos.update(nuevos_supuestos or {})
        supuestos, valor = cls.calcular(proyeccion.tipo, proyeccion.material, supuestos)
        proyeccion.supuestos = supuestos
        proyeccion.valor_proyectado = valor
        proyeccion.save(update_fields=["supuestos", "valor_proyectado"])
        return proyeccion
