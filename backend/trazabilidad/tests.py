from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import Rol, Usuario
from configuracion.models import ParametroConversion
from inventario.models import ComposicionPila, Pila, ProcesoPila
from mantenedores.models import Cliente, Material
from recepcion.models import DetalleRecepcion, Recepcion

from .models import IndicadorAmbiental
from .services import CLAVE_CO2_CAMION, CLAVE_CO2_COMPOSTAJE


class IndicadorAmbientalTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rol_admin = Rol.objects.create(nombre=Rol.ADMINISTRADOR)
        cls.rol_operador = Rol.objects.create(nombre=Rol.OPERADOR)
        cls.rol_transportista = Rol.objects.create(nombre=Rol.TRANSPORTISTA)
        cls.admin = Usuario.objects.create_user(
            username="admin-m9", password="clave-segura", rol=cls.rol_admin,
            nombre_completo="Admin M9",
        )
        cls.operador = Usuario.objects.create_user(
            username="operador-m9", password="clave-segura", rol=cls.rol_operador,
            nombre_completo="Operador M9",
        )
        cls.transportista = Usuario.objects.create_user(
            username="transportista-m9", password="clave-segura",
            rol=cls.rol_transportista, nombre_completo="Transportista M9",
        )
        cls.cliente = Cliente.objects.create(razon_social="Cliente Ambiental")
        cls.material = Material.objects.create(
            nombre="Rama M9",
            categoria=Material.VERDE,
            densidad_kg_m3=Decimal("250.00"),
            admite_chip=False,
        )

    def crear_factor(self, clave, valor):
        return ParametroConversion.objects.create(
            clave=clave,
            nombre=clave.replace("_", " ").title(),
            valor=Decimal(valor),
            unidad="kg CO2e/kg",
        )

    def crear_recepcion(self, estado=Recepcion.EN_CURSO, fecha=None):
        return Recepcion.objects.create(
            cliente=self.cliente,
            fecha=fecha or timezone.localdate(),
            hora=timezone.now().time(),
            estado=estado,
        )

    def agregar_detalle(self, recepcion, volumen="4.00", peso="1000.00"):
        return DetalleRecepcion.objects.create(
            recepcion=recepcion,
            material=self.material,
            volumen_m3=Decimal(volumen),
            peso_derivado_kg=Decimal(peso),
        )

    def crear_pila_cerrada(self, codigo="P-M9-01", volumen="4.00"):
        pila = Pila.objects.create(
            codigo=codigo,
            fecha_inicio=timezone.localdate() - timedelta(days=30),
        )
        ComposicionPila.objects.create(
            pila=pila, material=self.material, volumen_m3=Decimal(volumen)
        )
        ProcesoPila.objects.create(
            pila=pila,
            tipo=ProcesoPila.ENSACADO,
            fecha=timezone.now(),
            volumen_m3=Decimal(volumen),
        )
        pila.estado = Pila.CERRADA
        pila.save(update_fields=["estado"])
        return pila


class CalculoRecepcionTests(IndicadorAmbientalTestBase):
    def test_recepcion_recibida_calcula_co2_desde_el_peso(self):
        self.crear_factor(CLAVE_CO2_CAMION, "0.50")
        recepcion = self.crear_recepcion()
        self.agregar_detalle(recepcion, peso="1000.00")

        recepcion.estado = Recepcion.RECIBIDA
        recepcion.save(update_fields=["estado"])

        indicador = IndicadorAmbiental.objects.get(recepcion=recepcion)
        self.assertEqual(indicador.origen, IndicadorAmbiental.RECEPCION)
        self.assertEqual(indicador.co2_evitado_kg, Decimal("500.00"))
        self.assertEqual(indicador.fecha, recepcion.fecha)

    def test_sin_factor_no_inventa_valor_y_api_lo_senala_pendiente(self):
        recepcion = self.crear_recepcion(estado=Recepcion.RECIBIDA)
        self.agregar_detalle(recepcion)
        self.assertFalse(IndicadorAmbiental.objects.filter(recepcion=recepcion).exists())

        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(reverse("indicador-ambiental-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data["pendientes"]), 1)
        self.assertIn(CLAVE_CO2_CAMION, respuesta.data["pendientes"][0]["motivo"])

    def test_crear_factor_reintenta_calculo_pendiente(self):
        recepcion = self.crear_recepcion(estado=Recepcion.RECIBIDA)
        self.agregar_detalle(recepcion, peso="800.00")
        self.assertFalse(IndicadorAmbiental.objects.filter(recepcion=recepcion).exists())

        self.crear_factor(CLAVE_CO2_CAMION, "0.25")

        indicador = IndicadorAmbiental.objects.get(recepcion=recepcion)
        self.assertEqual(indicador.co2_evitado_kg, Decimal("200.00"))

    def test_corregir_peso_recalcula_sin_duplicar(self):
        self.crear_factor(CLAVE_CO2_CAMION, "0.50")
        recepcion = self.crear_recepcion(estado=Recepcion.RECIBIDA)
        detalle = self.agregar_detalle(recepcion, peso="1000.00")
        indicador = IndicadorAmbiental.objects.get(recepcion=recepcion)
        identificador = indicador.pk

        detalle.peso_derivado_kg = Decimal("1200.00")
        detalle.save(update_fields=["peso_derivado_kg"])

        indicador.refresh_from_db()
        self.assertEqual(indicador.pk, identificador)
        self.assertEqual(indicador.co2_evitado_kg, Decimal("600.00"))
        self.assertEqual(IndicadorAmbiental.objects.filter(recepcion=recepcion).count(), 1)

    def test_rechazar_recepcion_descarta_indicador(self):
        self.crear_factor(CLAVE_CO2_CAMION, "0.50")
        recepcion = self.crear_recepcion(estado=Recepcion.RECIBIDA)
        self.agregar_detalle(recepcion)
        self.assertTrue(IndicadorAmbiental.objects.filter(recepcion=recepcion).exists())

        recepcion.estado = Recepcion.RECHAZADA
        recepcion.save(update_fields=["estado"])

        self.assertFalse(IndicadorAmbiental.objects.filter(recepcion=recepcion).exists())


class CalculoPilaTests(IndicadorAmbientalTestBase):
    def test_pila_cerrada_calcula_peso_por_densidad_y_co2(self):
        self.crear_factor(CLAVE_CO2_COMPOSTAJE, "0.30")
        pila = self.crear_pila_cerrada(volumen="4.00")

        indicador = IndicadorAmbiental.objects.get(pila=pila)
        self.assertEqual(indicador.origen, IndicadorAmbiental.PILA)
        self.assertEqual(indicador.co2_evitado_kg, Decimal("300.00"))

    def test_pila_sin_factor_queda_pendiente(self):
        pila = self.crear_pila_cerrada()
        self.assertFalse(IndicadorAmbiental.objects.filter(pila=pila).exists())

        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(reverse("indicador-ambiental-list"))
        self.assertEqual(len(respuesta.data["pendientes"]), 1)
        self.assertIn(CLAVE_CO2_COMPOSTAJE, respuesta.data["pendientes"][0]["motivo"])

    def test_cambio_de_composicion_recalcula_sin_duplicar(self):
        self.crear_factor(CLAVE_CO2_COMPOSTAJE, "0.30")
        pila = self.crear_pila_cerrada()
        indicador = IndicadorAmbiental.objects.get(pila=pila)
        identificador = indicador.pk
        segundo_material = Material.objects.create(
            nombre="Pasto M9", densidad_kg_m3=Decimal("100.00"), admite_chip=False
        )

        ComposicionPila.objects.create(
            pila=pila, material=segundo_material, volumen_m3=Decimal("2.00")
        )

        indicador.refresh_from_db()
        self.assertEqual(indicador.pk, identificador)
        self.assertEqual(indicador.co2_evitado_kg, Decimal("360.00"))
        self.assertEqual(IndicadorAmbiental.objects.filter(pila=pila).count(), 1)

    def test_sin_densidad_no_inventa_peso(self):
        self.crear_factor(CLAVE_CO2_COMPOSTAJE, "0.30")
        material = Material.objects.create(nombre="Sin densidad", admite_chip=False)
        pila = Pila.objects.create(
            codigo="P-M9-SD", fecha_inicio=timezone.localdate(), estado=Pila.CERRADA
        )
        ComposicionPila.objects.create(
            pila=pila, material=material, volumen_m3=Decimal("2.00")
        )

        self.assertFalse(IndicadorAmbiental.objects.filter(pila=pila).exists())


class ConsultaIndicadorTests(IndicadorAmbientalTestBase):
    def setUp(self):
        self.crear_factor(CLAVE_CO2_CAMION, "0.50")
        self.crear_factor(CLAVE_CO2_COMPOSTAJE, "0.30")

    def test_administrador_consulta_acumulado_desglosado(self):
        recepcion = self.crear_recepcion(
            estado=Recepcion.RECIBIDA, fecha=date(2026, 9, 10)
        )
        self.agregar_detalle(recepcion, peso="1000.00")
        self.crear_pila_cerrada(volumen="4.00")

        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(reverse("indicador-ambiental-list"))

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["total_co2_evitado_kg"], "800.00")
        self.assertEqual(respuesta.data["recepciones_co2_evitado_kg"], "500.00")
        self.assertEqual(respuesta.data["pilas_co2_evitado_kg"], "300.00")
        self.assertEqual(respuesta.data["cantidad_recepciones"], 1)
        self.assertEqual(respuesta.data["cantidad_pilas"], 1)

    def test_filtro_por_periodo_acota_resultados(self):
        antigua = self.crear_recepcion(
            estado=Recepcion.RECIBIDA, fecha=date(2026, 8, 15)
        )
        reciente = self.crear_recepcion(
            estado=Recepcion.RECIBIDA, fecha=date(2026, 9, 15)
        )
        self.agregar_detalle(antigua, peso="100.00")
        self.agregar_detalle(reciente, peso="200.00")

        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("indicador-ambiental-list"),
            {"desde": "2026-09-01", "hasta": "2026-09-30"},
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["total_co2_evitado_kg"], "100.00")
        self.assertEqual(len(respuesta.data["resultados"]), 1)
        self.assertEqual(respuesta.data["resultados"][0]["recepcion"], reciente.pk)

    def test_periodo_invalido_es_rechazado(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("indicador-ambiental-list"),
            {"desde": "2026-10-01", "hasta": "2026-09-01"},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operador_y_transportista_no_pueden_consultar(self):
        for usuario in (self.operador, self.transportista):
            self.client.force_authenticate(usuario)
            respuesta = self.client.get(reverse("indicador-ambiental-list"))
            self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_indicador_exige_exactamente_un_origen(self):
        indicador = IndicadorAmbiental(
            origen=IndicadorAmbiental.RECEPCION,
            co2_evitado_kg=Decimal("1.00"),
            metodo="prueba",
            fecha=timezone.localdate(),
        )
        with self.assertRaises(ValidationError):
            indicador.full_clean()

