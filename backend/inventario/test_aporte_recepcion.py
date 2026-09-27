"""Tests de la propuesta Inc 3: origen de la composicion de una pila.

`AporteRecepcionPila` guarda que descarga aporto material a la pila y cuanto.
Se registra desde la accion de composicion (CU-36) con el campo opcional
`detalle_recepcion`, y lo consume la trazabilidad del lote (CU-68).
"""
from datetime import time
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from mantenedores.models import Cliente
from recepcion.models import DetalleRecepcion, Recepcion

from . import services
from .models import AporteRecepcionPila, Pila
from .tests import InventarioTestBase


class AporteRecepcionPilaBase(InventarioTestBase):
    """Datos y ayudas comunes a las pruebas de aportes."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.cliente = Cliente.objects.create(razon_social="Forestal Calle Calle")

    def setUp(self):
        self.autenticar(self.operador)
        self.pila = self.crear_pila()
        # Stock disponible en la etapa de origen, como exige el CU-36.
        self.sembrar(self.pasto, services.etapa_origen_para_pila(self.pasto), 100)

    def descarga(self, material=None, volumen="12.00", estado=Recepcion.RECIBIDA):
        recepcion = Recepcion.objects.create(
            cliente=self.cliente,
            fecha=timezone.localdate(),
            hora=time(9, 0),
            estado=estado,
        )
        return DetalleRecepcion.objects.create(
            recepcion=recepcion,
            material=material or self.pasto,
            volumen_m3=Decimal(volumen),
            peso_derivado_kg=Decimal(volumen) * (material or self.pasto).densidad_kg_m3,
        )

    def componer(self, pila=None, **datos):
        cuerpo = {"material": self.pasto.pk, "volumen_m3": "5.00", **datos}
        return self.client.post(
            reverse("pila-composicion", args=[(pila or self.pila).pk]), cuerpo, format="json"
        )


class AporteRecepcionPilaTests(AporteRecepcionPilaBase):
    def test_sin_detalle_la_composicion_sigue_igual_que_antes(self):
        respuesta = self.componer()
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.pila.composiciones.count(), 1)
        self.assertEqual(AporteRecepcionPila.objects.count(), 0)

    def test_con_detalle_registra_el_origen_y_suma_la_composicion(self):
        detalle = self.descarga()
        respuesta = self.componer(detalle_recepcion=detalle.pk)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        aporte = AporteRecepcionPila.objects.get()
        self.assertEqual(aporte.pila, self.pila)
        self.assertEqual(aporte.detalle_recepcion, detalle)
        self.assertEqual(aporte.volumen_m3, Decimal("5.00"))
        self.assertEqual(self.pila.composiciones.get().volumen_m3, Decimal("5.00"))

    def test_repetir_la_misma_descarga_suma_en_vez_de_duplicar(self):
        detalle = self.descarga()
        self.componer(detalle_recepcion=detalle.pk, volumen_m3="5.00")
        respuesta = self.componer(detalle_recepcion=detalle.pk, volumen_m3="4.00")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(AporteRecepcionPila.objects.count(), 1)
        self.assertEqual(AporteRecepcionPila.objects.get().volumen_m3, Decimal("9.00"))
        self.assertEqual(self.pila.composiciones.get().volumen_m3, Decimal("9.00"))

    def test_no_se_aporta_mas_de_lo_que_trajo_la_descarga(self):
        detalle = self.descarga(volumen="12.00")
        otra_pila = self.crear_pila()
        self.assertEqual(
            self.componer(pila=otra_pila, detalle_recepcion=detalle.pk, volumen_m3="8.00").status_code,
            status.HTTP_201_CREATED,
        )
        # Quedan 4 m3 de esa descarga: pedir 5 se rechaza y no deja rastro.
        respuesta = self.componer(detalle_recepcion=detalle.pk, volumen_m3="5.00")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("no alcanza", str(respuesta.data["detalle_recepcion"]))
        self.assertEqual(self.pila.composiciones.count(), 0)
        self.assertEqual(AporteRecepcionPila.objects.filter(pila=self.pila).count(), 0)

    def test_la_descarga_debe_estar_recibida(self):
        detalle = self.descarga(estado=Recepcion.EN_CURSO)
        respuesta = self.componer(detalle_recepcion=detalle.pk)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("recibida", str(respuesta.data["detalle_recepcion"]))

    def test_el_material_debe_coincidir_con_el_de_la_descarga(self):
        detalle = self.descarga(material=self.rama)
        respuesta = self.componer(detalle_recepcion=detalle.pk)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Ramas de poda", str(respuesta.data["detalle_recepcion"]))

    def test_una_descarga_que_alimento_una_pila_no_se_borra(self):
        from django.db.models import ProtectedError

        detalle = self.descarga()
        self.componer(detalle_recepcion=detalle.pk)
        with self.assertRaises(ProtectedError):
            detalle.recepcion.delete()

    def test_solo_una_pila_en_formacion_acepta_origen(self):
        detalle = self.descarga()
        cerrada = self.crear_pila(estado=Pila.CERRADA)
        respuesta = self.componer(pila=cerrada, detalle_recepcion=detalle.pk)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AporteRecepcionPila.objects.count(), 0)


class AporteChipTests(AporteRecepcionPilaBase):
    """La rama entra a la pila como chip: el aporte se mide contra el chip que produjo la descarga."""

    def setUp(self):
        super().setUp()
        self.sembrar(self.rama, services.etapa_origen_para_pila(self.rama), 100)

    def descarga_rama(self, volumen="12.00", chip="4.00"):
        detalle = self.descarga(material=self.rama, volumen=volumen)
        detalle.chip_derivado_m3 = Decimal(chip) if chip is not None else None
        detalle.save(update_fields=["chip_derivado_m3"])
        return detalle

    def test_el_chip_aportado_no_supera_el_chip_derivado_de_la_descarga(self):
        detalle = self.descarga_rama(volumen="12.00", chip="4.00")
        respuesta = self.componer(material=self.rama.pk, volumen_m3="5.00", detalle_recepcion=detalle.pk)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detalle_recepcion", respuesta.data)
        self.assertEqual(AporteRecepcionPila.objects.count(), 0)
        dentro = self.componer(material=self.rama.pk, volumen_m3="4.00", detalle_recepcion=detalle.pk)
        self.assertEqual(dentro.status_code, status.HTTP_201_CREATED)

    def test_descarga_sin_chip_calculado_no_puede_ser_origen(self):
        detalle = self.descarga_rama(chip=None)
        respuesta = self.componer(material=self.rama.pk, volumen_m3="1.00", detalle_recepcion=detalle.pk)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detalle_recepcion", respuesta.data)
