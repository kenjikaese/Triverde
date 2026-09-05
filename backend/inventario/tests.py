"""Tests del modulo 5 - Inventario, pilas y procesos (CU-34 a CU-44).

Cubren el camino normal de cada caso de uso y, sobre todo, sus excepciones:
que no se pueda triturar mas de lo que hay, que una pila no pase a reposo sin
harneado, que el inventario nunca quede en negativo.
"""
import uuid
from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import Rol, Usuario
from configuracion.models import ParametroConversion
from mantenedores.models import Cliente, Material
from recepcion.models import DetalleRecepcion, Recepcion

from . import services
from .models import ComposicionPila, Inventario, Pila, ProcesoPila


class InventarioTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rol_admin = Rol.objects.create(nombre=Rol.ADMINISTRADOR, descripcion="a")
        cls.rol_operador = Rol.objects.create(nombre=Rol.OPERADOR, descripcion="o")
        cls.rol_transportista = Rol.objects.create(
            nombre=Rol.TRANSPORTISTA, descripcion="t"
        )
        cls.admin = Usuario.objects.create_user(
            username="admin", password="admin12345",
            nombre_completo="Admin", rol=cls.rol_admin,
        )
        cls.operador = Usuario.objects.create_user(
            username="operador", password="operador12345",
            nombre_completo="Operador", rol=cls.rol_operador,
        )
        cls.camionero = Usuario.objects.create_user(
            username="camionero", password="camionero12345",
            nombre_completo="Camionero", rol=cls.rol_transportista,
        )
        # Material seco: se tritura (3 m3 de rama -> 1 m3 de chip).
        cls.rama = Material.objects.create(
            nombre="Ramas de poda", categoria=Material.SECA,
            densidad_kg_m3=Decimal("220.00"),
            factor_reduccion_chip=Decimal("3.00"), admite_chip=True,
        )
        # Material verde: entra directo a la pila, sin triturar.
        cls.pasto = Material.objects.create(
            nombre="Hojas y cesped", categoria=Material.VERDE,
            densidad_kg_m3=Decimal("350.00"), admite_chip=False,
        )
        # Material seco sin factor configurado (CU-37 Excepcion 3).
        cls.tronco = Material.objects.create(
            nombre="Troncos", categoria=Material.SECA,
            densidad_kg_m3=Decimal("400.00"), admite_chip=True,
        )

    def autenticar(self, usuario):
        self.client.force_authenticate(user=usuario)

    def sembrar(self, material, etapa, volumen):
        """Deja stock inicial usando el mismo camino que el resto del sistema."""
        return services.ingresar(material, etapa, Decimal(str(volumen)))

    def saldo(self, material, etapa):
        return services.disponible(material, etapa)

    def crear_pila(self, estado=Pila.EN_FORMACION):
        return Pila.objects.create(
            codigo=Pila.generar_codigo(),
            fecha_inicio=timezone.localdate(),
            estado=estado,
        )

    def registrar_proceso(self, datos):
        return self.client.post(reverse("procesopila-list"), datos, format="json")


# --- CU-34: consulta de inventario ------------------------------------------


class ConsultaInventarioTests(InventarioTestBase):
    def test_lista_muestra_en_cero_las_combinaciones_sin_movimiento(self):
        """CU-34 Excepcion 1: sin movimientos, la cantidad es cero, no un error."""
        self.autenticar(self.operador)
        respuesta = self.client.get(reverse("inventario-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        # 3 materiales x 5 etapas, todas en cero.
        self.assertEqual(len(respuesta.data), 15)
        self.assertTrue(
            all(Decimal(fila["volumen_m3"]) == Decimal("0.00") for fila in respuesta.data)
        )

    def test_filtra_por_material_y_por_etapa(self):
        """CU-34: el filtro acota el listado sin descartarse."""
        self.sembrar(self.rama, Inventario.POR_TRITURAR, 30)
        self.autenticar(self.admin)
        respuesta = self.client.get(
            reverse("inventario-list"),
            {"material": self.rama.pk, "etapa": Inventario.POR_TRITURAR},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 1)
        self.assertEqual(Decimal(respuesta.data[0]["volumen_m3"]), Decimal("30.00"))

    def test_transportista_sin_acceso_al_inventario(self):
        self.autenticar(self.camionero)
        respuesta = self.client.get(reverse("inventario-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)


# --- CU-35: alta de pila -----------------------------------------------------


class AltaPilaTests(InventarioTestBase):
    def test_crea_pila_con_codigo_correlativo_y_estado_en_formacion(self):
        """CU-35: sin codigo declarado, el sistema propone el correlativo."""
        self.autenticar(self.operador)
        respuesta = self.client.post(reverse("pila-list"), {}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["codigo"], "P-0001")
        self.assertEqual(respuesta.data["estado"], Pila.EN_FORMACION)

    def test_correlativo_salta_los_codigos_ya_tomados(self):
        """CU-35 Excepcion 1: si el correlativo choca, se genera otro."""
        Pila.objects.create(
            codigo="P-0001", fecha_inicio=timezone.localdate()
        )
        self.assertNotEqual(Pila.generar_codigo(), "P-0001")

    def test_rechaza_fecha_de_inicio_futura(self):
        """CU-35 Excepcion 2."""
        self.autenticar(self.operador)
        manana = timezone.localdate() + timedelta(days=1)
        respuesta = self.client.post(
            reverse("pila-list"), {"fecha_inicio": manana.isoformat()}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_inicio", respuesta.data)

    def test_pila_no_se_borra(self):
        """La pila es la trazabilidad del lote: se cierra, no se borra."""
        pila = self.crear_pila()
        self.autenticar(self.admin)
        respuesta = self.client.delete(reverse("pila-detail", args=[pila.pk]))
        self.assertEqual(
            respuesta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )


# --- CU-36: composicion inicial ---------------------------------------------


class ComposicionPilaTests(InventarioTestBase):
    def setUp(self):
        self.pila = self.crear_pila()
        self.sembrar(self.rama, Inventario.CHIP, 20)
        self.sembrar(self.pasto, Inventario.POR_TRITURAR, 10)
        self.autenticar(self.operador)

    def test_agrega_material_a_la_pila(self):
        respuesta = self.client.post(
            reverse("pila-composicion", args=[self.pila.pk]),
            {"material": self.rama.pk, "volumen_m3": "8.00"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.pila.composiciones.count(), 1)

    def test_material_repetido_se_suma_en_vez_de_duplicarse(self):
        """CU-36 Excepcion 2."""
        url = reverse("pila-composicion", args=[self.pila.pk])
        self.client.post(url, {"material": self.rama.pk, "volumen_m3": "5.00"}, format="json")
        respuesta = self.client.post(
            url, {"material": self.rama.pk, "volumen_m3": "3.00"}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(self.pila.composiciones.count(), 1)
        composicion = self.pila.composiciones.get()
        self.assertEqual(composicion.volumen_m3, Decimal("8.00"))

    def test_rechaza_mas_volumen_del_disponible(self):
        """CU-36 Excepcion 1: se senala el maximo disponible."""
        respuesta = self.client.post(
            reverse("pila-composicion", args=[self.pila.pk]),
            {"material": self.rama.pk, "volumen_m3": "25.00"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("volumen_m3", respuesta.data)

    def test_confirmar_sin_materiales_no_cambia_el_estado(self):
        """CU-36 Excepcion 3."""
        respuesta = self.client.post(
            reverse("pila-confirmar-composicion", args=[self.pila.pk])
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.pila.refresh_from_db()
        self.assertEqual(self.pila.estado, Pila.EN_FORMACION)

    def test_confirmar_mueve_el_inventario_y_arranca_la_pila(self):
        """CU-36: chip y verde pasan a 'pila en proceso'; la pila queda en proceso."""
        url = reverse("pila-composicion", args=[self.pila.pk])
        self.client.post(url, {"material": self.rama.pk, "volumen_m3": "8.00"}, format="json")
        self.client.post(url, {"material": self.pasto.pk, "volumen_m3": "4.00"}, format="json")

        respuesta = self.client.post(
            reverse("pila-confirmar-composicion", args=[self.pila.pk])
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.pila.refresh_from_db()
        self.assertEqual(self.pila.estado, Pila.EN_PROCESO)
        self.assertEqual(self.saldo(self.rama, Inventario.CHIP), Decimal("12.00"))
        self.assertEqual(self.saldo(self.pasto, Inventario.POR_TRITURAR), Decimal("6.00"))
        self.assertEqual(
            self.saldo(self.rama, Inventario.PILA_EN_PROCESO), Decimal("8.00")
        )
        self.assertEqual(
            self.saldo(self.pasto, Inventario.PILA_EN_PROCESO), Decimal("4.00")
        )


# --- CU-37: triturado --------------------------------------------------------


class TrituradoTests(InventarioTestBase):
    def setUp(self):
        self.sembrar(self.rama, Inventario.POR_TRITURAR, 30)
        self.sembrar(self.tronco, Inventario.POR_TRITURAR, 12)
        self.autenticar(self.operador)

    def test_triturado_descuenta_rama_e_incorpora_chip_derivado(self):
        """CU-37: 9 m3 de rama con factor 3 -> 3 m3 de chip."""
        respuesta = self.registrar_proceso(
            {
                "tipo": ProcesoPila.TRITURADO,
                "material": self.rama.pk,
                "volumen_m3": "9.00",
            }
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.saldo(self.rama, Inventario.POR_TRITURAR), Decimal("21.00")
        )
        self.assertEqual(self.saldo(self.rama, Inventario.CHIP), Decimal("3.00"))

    def test_rechaza_volumen_en_cero(self):
        """CU-37 Excepcion 1."""
        respuesta = self.registrar_proceso(
            {
                "tipo": ProcesoPila.TRITURADO,
                "material": self.rama.pk,
                "volumen_m3": "0.00",
            }
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rechaza_volumen_sobre_el_stock_disponible(self):
        """CU-37 Excepcion 2: no se tritura mas de lo que hay."""
        respuesta = self.registrar_proceso(
            {
                "tipo": ProcesoPila.TRITURADO,
                "material": self.rama.pk,
                "volumen_m3": "31.00",
            }
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.saldo(self.rama, Inventario.POR_TRITURAR), Decimal("30.00")
        )

    def test_sin_factor_configurado_registra_y_deja_el_chip_pendiente(self):
        """CU-37 Excepcion 3: descuenta el volumen, no calcula el chip."""
        respuesta = self.registrar_proceso(
            {
                "tipo": ProcesoPila.TRITURADO,
                "material": self.tronco.pk,
                "volumen_m3": "5.00",
            }
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertTrue(respuesta.data["chip_pendiente"])
        self.assertEqual(
            self.saldo(self.tronco, Inventario.POR_TRITURAR), Decimal("7.00")
        )
        self.assertEqual(self.saldo(self.tronco, Inventario.CHIP), Decimal("0.00"))

    def test_triturado_no_admite_pila(self):
        """CU-37: el triturado ocurre antes de armar la pila."""
        pila = self.crear_pila(estado=Pila.EN_PROCESO)
        respuesta = self.registrar_proceso(
            {
                "tipo": ProcesoPila.TRITURADO,
                "material": self.rama.pk,
                "volumen_m3": "3.00",
                "pila": pila.pk,
            }
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)


# --- CU-38, CU-39, CU-40: volteo, riego y harneado --------------------------


class ProcesosDeMaduracionTests(InventarioTestBase):
    def setUp(self):
        self.pila = self.crear_pila(estado=Pila.EN_PROCESO)
        self.autenticar(self.operador)

    def test_volteo_exige_temperatura(self):
        """CU-38 Excepcion 1."""
        respuesta = self.registrar_proceso(
            {"tipo": ProcesoPila.VOLTEO, "pila": self.pila.pk}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("temperatura", respuesta.data)

    def test_volteo_sobre_el_techo_se_registra_con_advertencia(self):
        """CU-38 Excepcion 2: se registra igual, marcado."""
        ParametroConversion.objects.create(
            clave="temperatura_maxima_pila", nombre="Techo de temperatura",
            valor=Decimal("65.0000"), unidad="C",
        )
        respuesta = self.registrar_proceso(
            {
                "tipo": ProcesoPila.VOLTEO,
                "pila": self.pila.pk,
                "temperatura": "72.00",
            }
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(respuesta.data["advertencia"])

    def test_riego_sin_humedad_es_valido(self):
        """CU-39 Excepcion 1: la humedad es informativa."""
        respuesta = self.registrar_proceso(
            {"tipo": ProcesoPila.RIEGO, "pila": self.pila.pk}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

    def test_rechaza_fecha_futura(self):
        """CU-39 Excepcion 2 / CU-40 Excepcion 1."""
        futuro = (timezone.now() + timedelta(days=1)).isoformat()
        respuesta = self.registrar_proceso(
            {"tipo": ProcesoPila.RIEGO, "pila": self.pila.pk, "fecha": futuro}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_harneado_sobre_pila_que_no_esta_en_proceso(self):
        """CU-40 Excepcion 2."""
        pila_en_reposo = self.crear_pila(estado=Pila.EN_REPOSO)
        respuesta = self.registrar_proceso(
            {"tipo": ProcesoPila.HARNEADO, "pila": pila_en_reposo.pk}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pila", respuesta.data)


# --- CU-41 y CU-42: reposo y ensacado ---------------------------------------


class ReposoYEnsacadoTests(InventarioTestBase):
    def setUp(self):
        self.pila = self.crear_pila(estado=Pila.EN_PROCESO)
        ComposicionPila.objects.create(
            pila=self.pila, material=self.rama, volumen_m3=Decimal("6.00")
        )
        ComposicionPila.objects.create(
            pila=self.pila, material=self.pasto, volumen_m3=Decimal("4.00")
        )
        self.sembrar(self.rama, Inventario.PILA_EN_PROCESO, 6)
        self.sembrar(self.pasto, Inventario.PILA_EN_PROCESO, 4)
        self.autenticar(self.operador)

    def harnear(self):
        ProcesoPila.objects.create(
            pila=self.pila, tipo=ProcesoPila.HARNEADO, fecha=timezone.now()
        )

    def test_reposo_sin_harneado_previo(self):
        """CU-41 Excepcion 1."""
        respuesta = self.registrar_proceso(
            {"tipo": ProcesoPila.REPOSO, "pila": self.pila.pk}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pila", respuesta.data)

    def test_reposo_traslada_el_material_a_curado(self):
        """CU-41: de 'pila en proceso' a 'curado'; la pila queda en reposo."""
        self.harnear()
        respuesta = self.registrar_proceso(
            {"tipo": ProcesoPila.REPOSO, "pila": self.pila.pk}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.pila.refresh_from_db()
        self.assertEqual(self.pila.estado, Pila.EN_REPOSO)
        self.assertEqual(self.saldo(self.rama, Inventario.CURADO), Decimal("6.00"))
        self.assertEqual(self.saldo(self.pasto, Inventario.CURADO), Decimal("4.00"))
        self.assertEqual(
            self.saldo(self.rama, Inventario.PILA_EN_PROCESO), Decimal("0.00")
        )

    def test_reposo_duplicado_se_rechaza(self):
        """CU-41 Excepcion 2."""
        self.harnear()
        self.registrar_proceso({"tipo": ProcesoPila.REPOSO, "pila": self.pila.pk})
        respuesta = self.registrar_proceso(
            {"tipo": ProcesoPila.REPOSO, "pila": self.pila.pk}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ensacado_parcial_deja_la_pila_en_reposo(self):
        """CU-42: queda material curado pendiente."""
        self.harnear()
        self.registrar_proceso({"tipo": ProcesoPila.REPOSO, "pila": self.pila.pk})
        respuesta = self.registrar_proceso(
            {"tipo": ProcesoPila.ENSACADO, "pila": self.pila.pk, "volumen_m3": "5.00"}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.pila.refresh_from_db()
        self.assertEqual(self.pila.estado, Pila.EN_REPOSO)
        # 5 m3 repartidos a prorrata: 3 de rama (60 %) y 2 de pasto (40 %).
        self.assertEqual(self.saldo(self.rama, Inventario.ENSACADO), Decimal("3.00"))
        self.assertEqual(self.saldo(self.pasto, Inventario.ENSACADO), Decimal("2.00"))

    def test_ensacado_total_cierra_la_pila(self):
        """CU-42: agotado el curado, la pila se cierra."""
        self.harnear()
        self.registrar_proceso({"tipo": ProcesoPila.REPOSO, "pila": self.pila.pk})
        respuesta = self.registrar_proceso(
            {"tipo": ProcesoPila.ENSACADO, "pila": self.pila.pk, "volumen_m3": "10.00"}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.pila.refresh_from_db()
        self.assertEqual(self.pila.estado, Pila.CERRADA)
        self.assertEqual(self.saldo(self.rama, Inventario.CURADO), Decimal("0.00"))

    def test_ensacado_sobre_el_curado_disponible_se_rechaza(self):
        """CU-42 Excepcion 2."""
        self.harnear()
        self.registrar_proceso({"tipo": ProcesoPila.REPOSO, "pila": self.pila.pk})
        respuesta = self.registrar_proceso(
            {"tipo": ProcesoPila.ENSACADO, "pila": self.pila.pk, "volumen_m3": "11.00"}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("volumen_m3", respuesta.data)


# --- CU-43: trazabilidad ----------------------------------------------------


class TrazabilidadPilaTests(InventarioTestBase):
    def test_ficha_trae_composicion_y_procesos_en_orden(self):
        """CU-43: composicion + linea de tiempo cronologica."""
        pila = self.crear_pila(estado=Pila.EN_PROCESO)
        ComposicionPila.objects.create(
            pila=pila, material=self.rama, volumen_m3=Decimal("6.00")
        )
        ahora = timezone.now()
        ProcesoPila.objects.create(
            pila=pila, tipo=ProcesoPila.RIEGO,
            fecha=ahora - timedelta(days=1),
        )
        ProcesoPila.objects.create(
            pila=pila, tipo=ProcesoPila.VOLTEO, fecha=ahora,
            temperatura=Decimal("55.00"),
        )
        self.autenticar(self.admin)
        respuesta = self.client.get(reverse("pila-trazabilidad", args=[pila.pk]))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data["composiciones"]), 1)
        tipos = [proceso["tipo"] for proceso in respuesta.data["procesos"]]
        self.assertEqual(tipos, [ProcesoPila.RIEGO, ProcesoPila.VOLTEO])

    def test_pila_recien_creada_no_es_un_error(self):
        """CU-43 Excepcion 2: sin procesos, la ficha se muestra igual."""
        pila = self.crear_pila()
        self.autenticar(self.operador)
        respuesta = self.client.get(reverse("pila-trazabilidad", args=[pila.pk]))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["procesos"], [])


# --- CU-44: actualizacion del inventario ------------------------------------


class MovimientosInventarioTests(InventarioTestBase):
    def test_recepcion_incorpora_el_material_al_inventario(self):
        """CU-44: lo descargado entra en 'por triturar'."""
        cliente = Cliente.objects.create(razon_social="Jardines SpA")
        recepcion = Recepcion.objects.create(
            cliente=cliente, fecha=timezone.localdate(), hora=timezone.now().time()
        )
        DetalleRecepcion.objects.create(
            recepcion=recepcion, material=self.rama,
            volumen_m3=Decimal("20.00"), peso_derivado_kg=Decimal("4400.00"),
        )
        self.assertEqual(
            self.saldo(self.rama, Inventario.POR_TRITURAR), Decimal("20.00")
        )

    def test_material_a_venta_directa_no_entra_al_circuito(self):
        """CU-44: lo que se vende directo no se inventaria como compostable."""
        cliente = Cliente.objects.create(razon_social="Jardines SpA")
        recepcion = Recepcion.objects.create(
            cliente=cliente, fecha=timezone.localdate(), hora=timezone.now().time()
        )
        DetalleRecepcion.objects.create(
            recepcion=recepcion, material=self.rama,
            volumen_m3=Decimal("20.00"), peso_derivado_kg=Decimal("4400.00"),
            destino_sugerido=DetalleRecepcion.A_VENTA_DIRECTA,
        )
        self.assertEqual(
            self.saldo(self.rama, Inventario.POR_TRITURAR), Decimal("0.00")
        )

    def test_no_deja_el_inventario_en_negativo(self):
        """CU-44 Excepcion 2: el movimiento se rechaza entero."""
        self.sembrar(self.rama, Inventario.POR_TRITURAR, 5)
        from rest_framework import serializers as drf_serializers

        with self.assertRaises(drf_serializers.ValidationError):
            services.aplicar_movimiento(
                self.rama, Inventario.POR_TRITURAR, Inventario.CHIP, Decimal("6.00")
            )
        self.assertEqual(
            self.saldo(self.rama, Inventario.POR_TRITURAR), Decimal("5.00")
        )

    def test_transportista_no_registra_procesos(self):
        self.autenticar(self.camionero)
        respuesta = self.registrar_proceso(
            {"tipo": ProcesoPila.RIEGO, "pila": self.crear_pila().pk}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)


# --- Idempotencia y cola offline (spec M5 secs. 4.3 y 5) --------------------


class IdempotenciaProcesoTests(InventarioTestBase):
    """Criterio de aceptacion 6: reenviar un proceso no lo aplica dos veces."""

    def setUp(self):
        self.sembrar(self.rama, Inventario.POR_TRITURAR, 30)
        self.autenticar(self.operador)
        self.id_local = str(uuid.uuid4())

    def cuerpo_triturado(self):
        return {
            "tipo": ProcesoPila.TRITURADO,
            "material": self.rama.pk,
            "volumen_m3": "9.00",
            "id_local": self.id_local,
        }

    def test_reenviar_el_mismo_proceso_no_mueve_dos_veces_el_inventario(self):
        primera = self.registrar_proceso(self.cuerpo_triturado())
        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)
        segunda = self.registrar_proceso(self.cuerpo_triturado())
        self.assertEqual(segunda.status_code, status.HTTP_201_CREATED)

        self.assertEqual(ProcesoPila.objects.filter(id_local=self.id_local).count(), 1)
        # El descuento se aplico una sola vez: 30 - 9, no 30 - 18.
        self.assertEqual(
            self.saldo(self.rama, Inventario.POR_TRITURAR), Decimal("21.00")
        )
        self.assertEqual(self.saldo(self.rama, Inventario.CHIP), Decimal("3.00"))

    def test_cola_offline_acepta_el_tipo_proceso_pila(self):
        """Spec sec. 5: los procesos entran por la misma cola del Incremento 1."""
        respuesta = self.client.post(
            reverse("sincronizacion"),
            {
                "operaciones": [
                    {
                        "id_local": self.id_local,
                        "tipo": "proceso_pila",
                        "capturado_en": timezone.now().isoformat(),
                        "datos": {
                            "tipo": ProcesoPila.TRITURADO,
                            "material": self.rama.pk,
                            "volumen_m3": "9.00",
                        },
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        resultado = respuesta.data["resultados"][0]
        self.assertEqual(resultado["estado"], "sincronizada")
        proceso = ProcesoPila.objects.get(id_local=self.id_local)
        self.assertEqual(proceso.estado_sincronizacion, ProcesoPila.SINCRONIZADA)
        self.assertEqual(
            self.saldo(self.rama, Inventario.POR_TRITURAR), Decimal("21.00")
        )

    def test_reenviar_el_lote_sincronizado_no_duplica_el_movimiento(self):
        """Criterio 6 sobre la cola: el reintento devuelve el mismo resultado."""
        lote = {
            "operaciones": [
                {
                    "id_local": self.id_local,
                    "tipo": "proceso_pila",
                    "capturado_en": timezone.now().isoformat(),
                    "datos": {
                        "tipo": ProcesoPila.TRITURADO,
                        "material": self.rama.pk,
                        "volumen_m3": "9.00",
                    },
                }
            ]
        }
        self.client.post(reverse("sincronizacion"), lote, format="json")
        respuesta = self.client.post(reverse("sincronizacion"), lote, format="json")
        self.assertEqual(respuesta.data["resultados"][0]["estado"], "sincronizada")
        self.assertEqual(ProcesoPila.objects.filter(id_local=self.id_local).count(), 1)
        self.assertEqual(
            self.saldo(self.rama, Inventario.POR_TRITURAR), Decimal("21.00")
        )


class DerivacionChipTests(InventarioTestBase):
    """Spec sec. 4.2: la conversion vive en `Material.derivar_chip`."""

    def test_material_con_factor_deriva_el_chip(self):
        self.assertEqual(self.rama.derivar_chip(Decimal("9.00")), Decimal("3.00"))

    def test_material_sin_factor_no_inventa_un_valor(self):
        self.assertIsNone(self.tronco.derivar_chip(Decimal("9.00")))
