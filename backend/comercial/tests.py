"""Tests del modulo comercial.

Cubren los cinco criterios de aceptacion de la spec del Modulo 8 mas las
excepciones de los CU-55 a CU-64.
"""
from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import Rol, Usuario
from configuracion.models import TarifaRecepcion
from mantenedores.models import Cliente, Producto, Vehiculo
from recepcion.models import Recepcion

from .models import Cobro, Cotizacion, Despacho, DocumentoTributario, Venta


class ComercialTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rol_admin = Rol.objects.create(nombre=Rol.ADMINISTRADOR, descripcion="a")
        cls.rol_operador = Rol.objects.create(nombre=Rol.OPERADOR, descripcion="o")
        cls.admin = Usuario.objects.create_user(
            username="admin", password="admin12345",
            nombre_completo="Admin", rol=cls.rol_admin,
        )
        cls.operador = Usuario.objects.create_user(
            username="operador", password="operador12345",
            nombre_completo="Operador", rol=cls.rol_operador,
        )
        cls.cliente = Cliente.objects.create(
            razon_social="Vivero Los Aromos",
            rut="77.123.456-7",
            nombre_contacto="Javier",
            telefono="+56900000000",
            email="contacto@aromos.cl",
            direccion="Quilapilun s/n, Colina",
        )
        cls.producto = Producto.objects.create(
            nombre="Compost premium 40 L",
            tipo=Producto.COMPOST,
            precio=Decimal("4500.00"),
            unidad_de_venta=Producto.SACO,
        )

    def autenticar(self, usuario):
        self.client.force_authenticate(user=usuario)

    def crear_venta(self, cantidad="10"):
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("venta-list"),
            {
                "cliente": self.cliente.pk,
                "detalles": [
                    {"producto": self.producto.pk, "cantidad": cantidad}
                ],
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        return respuesta.data


class CotizacionTests(ComercialTestBase):
    """CU-55, CU-56, CU-57. Criterio de aceptacion 1."""

    def _configurar_costo_km(self, valor):
        """Crea el CostoTransporte de M2 si el modelo ya esta integrado.

        Mientras el Modulo 2 no aporte el modelo, el test verifica la rama
        "sin costo configurado", que es la Excepcion 3 del CU-55.
        """
        from django.apps import apps

        try:
            CostoTransporte = apps.get_model("configuracion", "CostoTransporte")
        except LookupError:
            return None
        return CostoTransporte.objects.create(
            costo_por_km=Decimal(valor), vigente=True, fecha=date.today()
        )

    def test_cotizacion_aplica_ida_y_vuelta_sobre_el_costo_por_km(self):
        costo = self._configurar_costo_km("1000")
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("cotizacion-list"),
            {
                "cliente": self.cliente.pk,
                "servicio": "Triturado in situ",
                "distancia_km": "10",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        if costo is None:
            # Sin el modelo de M2: no calcula y lo informa (Excepcion 3).
            self.assertIsNone(respuesta.data["costo_estimado"])
            self.assertIn("advertencia", respuesta.data)
        else:
            # 10 km ida y vuelta = 20 km x 1000 = 20000.
            self.assertEqual(
                Decimal(respuesta.data["costo_estimado"]), Decimal("20000.00")
            )

    def test_formula_ida_y_vuelta_sin_depender_del_modulo_2(self):
        """La formula del CU-55 con el costo por km simulado.

        El objeto `CostoTransporte` lo construye M2 y todavia no esta
        integrado, asi que se sustituye la lectura del parametro por un doble:
        lo que se verifica aca es la regla de negocio (ida y vuelta por el
        valor vigente), no de donde sale el valor.
        """
        from unittest.mock import patch

        from .services import calcular_costo_cotizacion

        with patch(
            "comercial.services.costo_por_km_vigente",
            return_value=Decimal("1000"),
        ):
            self.assertEqual(
                calcular_costo_cotizacion(Decimal("10")), Decimal("20000.00")
            )
        # Sin costo configurado no calcula (CU-55, Excepcion 3).
        with patch("comercial.services.costo_por_km_vigente", return_value=None):
            self.assertIsNone(calcular_costo_cotizacion(Decimal("10")))

    def test_distancia_no_positiva_es_rechazada(self):
        self.autenticar(self.admin)
        for distancia in ("0", "-5"):
            respuesta = self.client.post(
                reverse("cotizacion-list"),
                {
                    "cliente": self.cliente.pk,
                    "servicio": "Triturado in situ",
                    "distancia_km": distancia,
                },
                format="json",
            )
            self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("distancia_km", respuesta.data)

    def test_exportar_exige_datos_de_contacto_completos(self):
        cliente_incompleto = Cliente.objects.create(razon_social="Sin Datos SpA")
        cotizacion = Cotizacion.objects.create(
            cliente=cliente_incompleto,
            distancia_km=Decimal("10"),
            servicio="Triturado in situ",
        )
        self.autenticar(self.admin)
        respuesta = self.client.get(
            reverse("cotizacion-exportar", args=[cotizacion.pk])
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("faltantes", respuesta.data)

    def test_exportar_devuelve_el_documento_con_cliente_completo(self):
        cotizacion = Cotizacion.objects.create(
            cliente=self.cliente,
            distancia_km=Decimal("10"),
            servicio="Triturado in situ",
            costo_estimado=Decimal("20000.00"),
        )
        self.autenticar(self.admin)
        respuesta = self.client.get(
            reverse("cotizacion-exportar", args=[cotizacion.pk])
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            respuesta.data["cliente"]["razon_social"], "Vivero Los Aromos"
        )
        self.assertEqual(respuesta.data["servicio"], "Triturado in situ")

    def test_historial_filtra_por_cliente_sin_coincidencias(self):
        Cotizacion.objects.create(
            cliente=self.cliente,
            distancia_km=Decimal("10"),
            servicio="Triturado in situ",
        )
        otro = Cliente.objects.create(razon_social="Otro Cliente")
        self.autenticar(self.admin)
        respuesta = self.client.get(reverse("cotizacion-list"), {"cliente": otro.pk})
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 0)


class VentaTests(ComercialTestBase):
    """CU-58, CU-59, CU-60. Criterio de aceptacion 2."""

    def test_venta_calcula_total_y_nace_pendiente(self):
        datos = self.crear_venta(cantidad="10")
        self.assertEqual(datos["estado"], Venta.PENDIENTE)
        # 10 sacos x 4500 = 45000.
        self.assertEqual(Decimal(datos["total"]), Decimal("45000.00"))
        self.assertEqual(datos["detalles"][0]["unidad"], Producto.SACO)
        self.assertEqual(
            Decimal(datos["detalles"][0]["precio_unitario"]), Decimal("4500.00")
        )

    def test_cantidad_no_positiva_es_rechazada(self):
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("venta-list"),
            {
                "cliente": self.cliente.pk,
                "detalles": [{"producto": self.producto.pk, "cantidad": "0"}],
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_producto_inactivo_o_sin_precio_es_rechazado(self):
        inactivo = Producto.objects.create(
            nombre="Mulch descontinuado", tipo=Producto.MULCH,
            precio=Decimal("3000.00"), unidad_de_venta=Producto.M3,
            estado=Producto.INACTIVO,
        )
        sin_precio = Producto.objects.create(
            nombre="Lena sin tarifar", tipo=Producto.LENA,
            unidad_de_venta=Producto.M3,
        )
        self.autenticar(self.admin)
        for producto in (inactivo, sin_precio):
            respuesta = self.client.post(
                reverse("venta-list"),
                {
                    "cliente": self.cliente.pk,
                    "detalles": [{"producto": producto.pk, "cantidad": "5"}],
                },
                format="json",
            )
            self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_despacho_pasa_la_venta_a_despachada_y_no_se_duplica(self):
        venta = self.crear_venta()
        self.autenticar(self.operador)
        url = reverse("venta-despachar", args=[venta["id"]])
        respuesta = self.client.post(
            url,
            {"fecha": "2026-09-10", "receptor": "Juan Perez", "direccion": "Colina"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Venta.objects.get(pk=venta["id"]).estado, Venta.DESPACHADA
        )

        # Segundo intento: la Excepcion 2 del CU-60 impide duplicarlo.
        respuesta = self.client.post(
            url,
            {"fecha": "2026-09-11", "receptor": "Otro", "direccion": "Colina"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Despacho.objects.filter(venta_id=venta["id"]).count(), 1)

    def test_despacho_exige_receptor(self):
        venta = self.crear_venta()
        self.autenticar(self.operador)
        respuesta = self.client.post(
            reverse("venta-despachar", args=[venta["id"]]),
            {"fecha": "2026-09-10", "receptor": "  "},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("receptor", respuesta.data)

    def test_totales_del_periodo(self):
        self.crear_venta(cantidad="10")
        self.crear_venta(cantidad="4")
        self.autenticar(self.admin)
        respuesta = self.client.get(reverse("venta-totales"))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["cantidad"], 2)
        # (10 + 4) sacos x 4500 = 63000.
        self.assertEqual(Decimal(respuesta.data["total"]), Decimal("63000.00"))


class CobroTests(ComercialTestBase):
    """CU-61. Criterio de aceptacion 3."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.vehiculo = Vehiculo.objects.create(
            patente="ABCD12", cliente=cls.cliente, capacidad_m3=Decimal("30.00")
        )
        cls.tarifa = TarifaRecepcion.objects.create(
            tramo_min_m3=Decimal("20.00"),
            tramo_max_m3=Decimal("40.00"),
            monto=Decimal("245000.00"),
            vigente=True,
        )
        cls.recepcion = Recepcion.objects.create(
            cliente=cls.cliente,
            vehiculo=cls.vehiculo,
            fecha=date(2026, 9, 1),
            hora="10:00",
        )

    def test_sugerencia_toma_la_tarifa_del_tramo_del_vehiculo(self):
        self.autenticar(self.operador)
        respuesta = self.client.get(
            reverse("cobro-sugerencia"), {"recepcion": self.recepcion.pk}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Decimal(respuesta.data["monto_sugerido"]), Decimal("245000.00")
        )
        self.assertFalse(respuesta.data["cobrada"])

    def test_sin_tarifa_para_el_tramo_no_bloquea_el_cobro(self):
        self.tarifa.delete()
        self.autenticar(self.operador)
        respuesta = self.client.get(
            reverse("cobro-sugerencia"), {"recepcion": self.recepcion.pk}
        )
        self.assertIsNone(respuesta.data["monto_sugerido"])

        respuesta = self.client.post(
            reverse("cobro-list"),
            {
                "recepcion": self.recepcion.pk,
                "cliente": self.cliente.pk,
                "monto": "200000",
                "fecha": "2026-09-01",
                "medio": "efectivo",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

    def test_cobro_de_recepcion_no_se_duplica(self):
        self.autenticar(self.operador)
        datos = {
            "recepcion": self.recepcion.pk,
            "cliente": self.cliente.pk,
            "monto": "245000",
            "fecha": "2026-09-01",
            "medio": "transferencia",
        }
        primera = self.client.post(reverse("cobro-list"), datos, format="json")
        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)

        segunda = self.client.post(reverse("cobro-list"), datos, format="json")
        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Cobro.objects.filter(recepcion=self.recepcion).count(), 1)

    def test_monto_no_positivo_es_rechazado(self):
        self.autenticar(self.operador)
        respuesta = self.client.post(
            reverse("cobro-list"),
            {
                "recepcion": self.recepcion.pk,
                "cliente": self.cliente.pk,
                "monto": "0",
                "fecha": "2026-09-01",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cobro_exige_venta_o_recepcion_pero_no_ambas(self):
        venta = self.crear_venta()
        self.autenticar(self.operador)
        # Ninguna de las dos.
        respuesta = self.client.post(
            reverse("cobro-list"),
            {"cliente": self.cliente.pk, "monto": "1000", "fecha": "2026-09-01"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        # Las dos a la vez.
        respuesta = self.client.post(
            reverse("cobro-list"),
            {
                "venta": venta["id"],
                "recepcion": self.recepcion.pk,
                "cliente": self.cliente.pk,
                "monto": "1000",
                "fecha": "2026-09-01",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)


class CuentaCorrienteTests(ComercialTestBase):
    """CU-62, CU-64. Criterio de aceptacion 4."""

    def test_saldo_es_ventas_menos_cobros_con_detalle_cronologico(self):
        venta = self.crear_venta(cantidad="10")  # 45000
        Cobro.objects.create(
            venta_id=venta["id"],
            cliente=self.cliente,
            monto=Decimal("20000.00"),
            fecha=date(2026, 9, 2),
        )
        self.autenticar(self.admin)
        respuesta = self.client.get(
            reverse("cuenta-corriente", args=[self.cliente.pk])
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(respuesta.data["total_ventas"]), Decimal("45000.00"))
        self.assertEqual(Decimal(respuesta.data["total_cobros"]), Decimal("20000.00"))
        self.assertEqual(Decimal(respuesta.data["saldo"]), Decimal("25000.00"))
        self.assertEqual(len(respuesta.data["movimientos"]), 2)
        fechas = [m["fecha"] for m in respuesta.data["movimientos"]]
        self.assertEqual(fechas, sorted(fechas))

    def test_cliente_sin_movimientos_da_saldo_cero(self):
        otro = Cliente.objects.create(razon_social="Cliente Nuevo")
        self.autenticar(self.admin)
        respuesta = self.client.get(reverse("cuenta-corriente", args=[otro.pk]))
        self.assertEqual(Decimal(respuesta.data["saldo"]), Decimal("0.00"))
        self.assertEqual(respuesta.data["movimientos"], [])

    def test_estado_de_pago_requiere_movimientos_y_valor_valido(self):
        self.autenticar(self.admin)
        url = reverse("cuenta-corriente", args=[self.cliente.pk])

        # Excepcion 1: sin ventas ni cobros no hay nada que conciliar.
        respuesta = self.client.patch(
            url, {"estado_pago": Cliente.CON_DEUDA}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

        self.crear_venta()
        self.autenticar(self.admin)

        # Excepcion 2: guardar sin seleccionar estado.
        respuesta = self.client.patch(url, {}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

        respuesta = self.client.patch(
            url, {"estado_pago": Cliente.CON_DEUDA}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.estado_pago, Cliente.CON_DEUDA)


class DocumentoTributarioTests(ComercialTestBase):
    """CU-63."""

    def test_documento_nace_pendiente_vinculado_a_la_venta(self):
        venta = self.crear_venta()
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("documento-tributario-list"),
            {
                "venta": venta["id"],
                "cliente": self.cliente.pk,
                "tipo": DocumentoTributario.FACTURA,
                "monto": venta["total"],
                "fecha": "2026-09-05",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            respuesta.data["estado"], DocumentoTributario.PENDIENTE
        )

    def test_documento_exige_tipo(self):
        venta = self.crear_venta()
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("documento-tributario-list"),
            {
                "venta": venta["id"],
                "cliente": self.cliente.pk,
                "monto": "1000",
                "fecha": "2026-09-05",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tipo", respuesta.data)


class ConsultasVaciasTests(ComercialTestBase):
    """Excepciones de consulta: listados vacios y filtros sin coincidencias.

    CU-57 exc. 1, CU-59 exc. 1 y 2, CU-64 exc. 2. Ninguna debe romper: el
    sistema muestra el listado vacio conservando el filtro aplicado.
    """

    def test_historial_sin_cotizaciones(self):
        self.autenticar(self.admin)
        respuesta = self.client.get(reverse("cotizacion-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 0)

    def test_periodo_sin_ventas_da_total_cero(self):
        self.autenticar(self.admin)
        rango = {"desde": "2020-01-01", "hasta": "2020-12-31"}
        respuesta = self.client.get(reverse("venta-list"), rango)
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 0)

        respuesta = self.client.get(reverse("venta-totales"), rango)
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["cantidad"], 0)
        self.assertEqual(Decimal(respuesta.data["total"]), Decimal("0"))

    def test_filtro_por_producto_sin_coincidencias(self):
        self.crear_venta()
        otro = Producto.objects.create(
            nombre="Chip decorativo", tipo=Producto.CHIP,
            precio=Decimal("52000.00"), unidad_de_venta=Producto.M3,
        )
        self.autenticar(self.admin)
        respuesta = self.client.get(reverse("venta-list"), {"producto": otro.pk})
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 0)

    def test_cuenta_corriente_con_rango_sin_movimientos(self):
        self.crear_venta()
        self.autenticar(self.admin)
        respuesta = self.client.get(
            reverse("cuenta-corriente", args=[self.cliente.pk]),
            {"desde": "2020-01-01", "hasta": "2020-12-31"},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(respuesta.data["saldo"]), Decimal("0.00"))
        self.assertEqual(respuesta.data["movimientos"], [])


class ParametrosInvalidosTests(ComercialTestBase):
    """Un parametro de consulta con basura no puede terminar en un 500.

    Los filtros por clave foranea y por fecha llegan como texto desde la URL.
    Sin validarlos, `?cliente=abc` levanta ValueError en el ORM y `?desde=hola`
    falla en PostgreSQL. Se descarta el filtro invalido y la consulta responde.
    """

    def test_filtros_con_valores_no_numericos_no_rompen(self):
        self.autenticar(self.admin)
        casos = [
            (reverse("venta-list"), {"cliente": "abc"}),
            (reverse("venta-list"), {"producto": "xyz"}),
            (reverse("cotizacion-list"), {"cliente": "abc"}),
            (reverse("cobro-list"), {"cliente": "nada"}),
            (reverse("cobro-sugerencia"), {"recepcion": "abc"}),
        ]
        for url, params in casos:
            respuesta = self.client.get(url, params)
            self.assertIn(
                respuesta.status_code,
                (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST),
                f"{url} con {params} devolvio {respuesta.status_code}",
            )

    def test_fechas_invalidas_no_rompen(self):
        self.autenticar(self.admin)
        casos = [
            (reverse("venta-list"), {"desde": "hola"}),
            (reverse("venta-totales"), {"hasta": "2026-13-45"}),
            (reverse("cotizacion-list"), {"desde": "///"}),
            (
                reverse("cuenta-corriente", args=[self.cliente.pk]),
                {"desde": "hola", "hasta": "chao"},
            ),
        ]
        for url, params in casos:
            respuesta = self.client.get(url, params)
            self.assertEqual(
                respuesta.status_code,
                status.HTTP_200_OK,
                f"{url} con {params} devolvio {respuesta.status_code}",
            )


class CatalogoVacioTests(ComercialTestBase):
    """CU-58 exc. 2: no hay productos activos para vender."""

    def test_venta_con_producto_inexistente_es_rechazada(self):
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("venta-list"),
            {"cliente": self.cliente.pk, "detalles": [{"producto": 9999, "cantidad": "1"}]},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_venta_sin_lineas_es_rechazada(self):
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("venta-list"),
            {"cliente": self.cliente.pk, "detalles": []},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_venta_sin_cliente_es_rechazada(self):
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("venta-list"),
            {"detalles": [{"producto": self.producto.pk, "cantidad": "1"}]},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cliente", respuesta.data)

    def test_cotizacion_sin_cliente_es_rechazada(self):
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("cotizacion-list"),
            {"servicio": "Triturado in situ", "distancia_km": "10"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cliente", respuesta.data)

    def test_documento_con_monto_no_positivo_es_rechazado(self):
        """CU-63 exc. 1: el origen sin monto obliga a ingresarlo a mano."""
        venta = self.crear_venta()
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("documento-tributario-list"),
            {
                "venta": venta["id"],
                "cliente": self.cliente.pk,
                "tipo": DocumentoTributario.BOLETA,
                "monto": "0",
                "fecha": "2026-09-05",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("monto", respuesta.data)


class PermisosTests(ComercialTestBase):
    """Criterio de aceptacion 5: el operador no cotiza ni ve cuenta corriente."""

    def test_operador_no_puede_cotizar(self):
        self.autenticar(self.operador)
        respuesta = self.client.get(reverse("cotizacion-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

        respuesta = self.client.post(
            reverse("cotizacion-list"),
            {
                "cliente": self.cliente.pk,
                "servicio": "Triturado in situ",
                "distancia_km": "10",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_operador_no_ve_la_cuenta_corriente(self):
        self.autenticar(self.operador)
        respuesta = self.client.get(
            reverse("cuenta-corriente", args=[self.cliente.pk])
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_operador_no_registra_documentos_tributarios(self):
        self.autenticar(self.operador)
        respuesta = self.client.get(reverse("documento-tributario-list"))
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_operador_si_registra_ventas_y_cobros(self):
        self.autenticar(self.operador)
        respuesta = self.client.post(
            reverse("venta-list"),
            {
                "cliente": self.cliente.pk,
                "detalles": [{"producto": self.producto.pk, "cantidad": "2"}],
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

    def test_venta_no_se_borra_fisicamente(self):
        venta = self.crear_venta()
        self.autenticar(self.admin)
        respuesta = self.client.delete(reverse("venta-detail", args=[venta["id"]]))
        self.assertEqual(
            respuesta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertTrue(Venta.objects.filter(pk=venta["id"]).exists())


class TrazabilidadVentaTests(ComercialTestBase):
    """CU-68 (Modulo 9, Parte A): enlace Venta -> Pila y cadena trazable.

    Criterio de aceptacion 4 de la spec M9: una venta con pila de origen
    devuelve la cadena; sin pila, informa "sin trazabilidad".
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from inventario.models import ComposicionPila, Pila
        from mantenedores.models import Material

        cls.rama = Material.objects.create(
            nombre="Ramas de poda", categoria=Material.SECA,
            densidad_kg_m3=Decimal("220.00"),
            factor_reduccion_chip=Decimal("3.00"), admite_chip=True,
        )
        cls.pasto = Material.objects.create(
            nombre="Hojas y cesped", categoria=Material.VERDE,
            densidad_kg_m3=Decimal("350.00"),
        )
        cls.pila_cerrada = Pila.objects.create(
            codigo="P-0901", fecha_inicio=date(2026, 6, 1), estado=Pila.CERRADA,
        )
        ComposicionPila.objects.create(
            pila=cls.pila_cerrada, material=cls.rama, volumen_m3=Decimal("40.00"),
        )
        ComposicionPila.objects.create(
            pila=cls.pila_cerrada, material=cls.pasto, volumen_m3=Decimal("20.00"),
        )
        cls.pila_en_proceso = Pila.objects.create(
            codigo="P-0902", fecha_inicio=date(2026, 8, 1), estado=Pila.EN_PROCESO,
        )
        # Origen de la composicion de la pila cerrada (propuesta Inc 3): los
        # 40 m3 de rama salieron de una descarga recibida del cliente.
        from datetime import time

        from inventario.models import AporteRecepcionPila
        from recepcion.models import DetalleRecepcion

        cls.recepcion_origen = Recepcion.objects.create(
            cliente=cls.cliente, fecha=date(2026, 5, 20), hora=time(8, 0),
            estado=Recepcion.RECIBIDA, conductor="Origen",
        )
        cls.detalle_origen = DetalleRecepcion.objects.create(
            recepcion=cls.recepcion_origen, material=cls.rama,
            volumen_m3=Decimal("40.00"), peso_derivado_kg=Decimal("8800.00"),
        )
        AporteRecepcionPila.objects.create(
            pila=cls.pila_cerrada, detalle_recepcion=cls.detalle_origen,
            volumen_m3=Decimal("40.00"),
        )

    def _vender(self, pila=None, cantidad="10"):
        self.autenticar(self.admin)
        linea = {"producto": self.producto.pk, "cantidad": cantidad}
        if pila is not None:
            linea["pila"] = pila.pk
        respuesta = self.client.post(
            reverse("venta-list"),
            {"cliente": self.cliente.pk, "detalles": [linea]},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        return respuesta.data

    def _trazar(self, venta_id):
        return self.client.get(reverse("venta-trazabilidad", args=[venta_id]))

    def test_la_linea_de_venta_guarda_la_pila_de_origen(self):
        venta = self._vender(pila=self.pila_cerrada)
        linea = venta["detalles"][0]
        self.assertEqual(linea["pila"], self.pila_cerrada.pk)
        self.assertEqual(linea["pila_codigo"], "P-0901")

    def test_la_pila_es_opcional(self):
        venta = self._vender()
        self.assertIsNone(venta["detalles"][0]["pila"])
        self.assertIsNone(venta["detalles"][0]["pila_codigo"])

    def test_pila_inexistente_se_rechaza(self):
        self.autenticar(self.admin)
        respuesta = self.client.post(
            reverse("venta-list"),
            {
                "cliente": self.cliente.pk,
                "detalles": [
                    {"producto": self.producto.pk, "cantidad": "5", "pila": 99999}
                ],
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Venta.objects.count(), 0)

    def test_venta_con_pila_cerrada_devuelve_la_cadena(self):
        venta = self._vender(pila=self.pila_cerrada)
        respuesta = self._trazar(venta["id"])
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertTrue(respuesta.data["trazable"])
        self.assertEqual(respuesta.data["advertencias"], [])
        pila = respuesta.data["lineas"][0]["pila"]
        self.assertEqual(pila["codigo"], "P-0901")
        self.assertTrue(pila["composicion_definitiva"])
        self.assertEqual(pila["volumen_total_m3"], "60.00")
        materiales = {c["material"]: c["volumen_m3"] for c in pila["composicion"]}
        self.assertEqual(
            materiales,
            {"Ramas de poda": "40.00", "Hojas y cesped": "20.00"},
        )
        # La cadena llega hasta la descarga de origen y su cliente.
        self.assertEqual(len(pila["recepciones_origen"]), 1)
        origen = pila["recepciones_origen"][0]
        self.assertEqual(origen["recepcion"], self.recepcion_origen.pk)
        self.assertEqual(origen["cliente"], "Vivero Los Aromos")
        self.assertEqual(origen["material"], "Ramas de poda")
        self.assertEqual(origen["volumen_m3"], "40.00")

    def test_pila_sin_descargas_de_origen_lo_advierte(self):
        """Propuesta Inc 3: sin aportes registrados, la cadena para en la composicion."""
        from inventario.models import ComposicionPila, Pila

        sin_origen = Pila.objects.create(
            codigo="P-0903", fecha_inicio=date(2026, 7, 1), estado=Pila.CERRADA,
        )
        ComposicionPila.objects.create(
            pila=sin_origen, material=self.pasto, volumen_m3=Decimal("10.00"),
        )
        venta = self._vender(pila=sin_origen)
        respuesta = self._trazar(venta["id"])
        self.assertTrue(respuesta.data["trazable"])
        self.assertEqual(respuesta.data["lineas"][0]["pila"]["recepciones_origen"], [])
        self.assertIn("no tiene descargas de origen", respuesta.data["advertencias"][0])

    def test_venta_sin_pila_informa_sin_trazabilidad(self):
        """CU-68, Excepcion 1."""
        venta = self._vender()
        respuesta = self._trazar(venta["id"])
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertFalse(respuesta.data["trazable"])
        self.assertIn("no cuenta con trazabilidad", respuesta.data["advertencias"][0])

    def test_pila_en_proceso_advierte_composicion_no_definitiva(self):
        """CU-68, Excepcion 2: se muestra lo disponible, con advertencia."""
        venta = self._vender(pila=self.pila_en_proceso)
        respuesta = self._trazar(venta["id"])
        self.assertTrue(respuesta.data["trazable"])
        self.assertFalse(respuesta.data["lineas"][0]["pila"]["composicion_definitiva"])
        self.assertIn("aun no es definitiva", respuesta.data["advertencias"][0])

    def test_solo_el_administrador_consulta_la_trazabilidad(self):
        venta = self._vender(pila=self.pila_cerrada)
        self.autenticar(self.operador)
        self.assertEqual(
            self._trazar(venta["id"]).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_una_pila_con_ventas_no_se_puede_borrar(self):
        """PROTECT: la pila vendida es evidencia de trazabilidad."""
        from django.db.models import ProtectedError

        self._vender(pila=self.pila_cerrada)
        with self.assertRaises(ProtectedError):
            self.pila_cerrada.delete()
