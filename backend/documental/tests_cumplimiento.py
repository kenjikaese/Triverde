"""Pruebas del Modulo 12, Parte F (CU-90 a CU-92).

Cubren la revision de vencimientos con sus tres excepciones, el tablero de
cumplimiento y el historial de versiones. Van en su propio archivo para que las
dos mitades del modulo no se pisen; el corredor de Django los descubre igual
(patron `test*.py`).
"""
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import Rol, Usuario
from configuracion.models import ParametroConversion
from mezcla.models import Alerta

from . import cumplimiento, services
from .models import DocumentoLegal, VersionDocumento

MEDIA_TEMPORAL = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CumplimientoTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        rol_admin = Rol.objects.create(nombre=Rol.ADMINISTRADOR)
        rol_operador = Rol.objects.create(nombre=Rol.OPERADOR)
        cls.admin = Usuario.objects.create_user(
            username="admin-parte-f", password="clave-segura", rol=rol_admin,
            nombre_completo="Admin Parte F",
        )
        cls.operador = Usuario.objects.create_user(
            username="operador-parte-f", password="clave-segura", rol=rol_operador,
            nombre_completo="Operador Parte F",
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        self.client.force_authenticate(self.admin)
        self.hoy = timezone.localdate()

    def documento(self, nombre="Resolucion sanitaria", dias_al_vencimiento=None, **extra):
        """Crea un documento; con `dias_al_vencimiento` le registra la vigencia."""
        datos = {
            "nombre": nombre,
            "tipo": DocumentoLegal.RESOLUCION,
            "entidad_emisora": "SEREMI de Salud",
        }
        datos.update(extra)
        documento = DocumentoLegal.objects.create(**datos)
        if dias_al_vencimiento is not None:
            services.registrar_vigencia(
                documento,
                self.hoy - timedelta(days=365),
                self.hoy + timedelta(days=dias_al_vencimiento),
            )
        return documento

    def alerta_de(self, documento):
        return Alerta.objects.filter(
            origen=Alerta.DOCUMENTO, documento=documento, estado=Alerta.ACTIVA
        ).first()


# --- CU-90: alerta de vencimiento -------------------------------------------


class RevisionVencimientosTests(CumplimientoTestBase):
    def test_genera_la_alerta_del_documento_dentro_del_umbral(self):
        documento = self.documento(dias_al_vencimiento=10)
        resumen = cumplimiento.revisar_vencimientos()

        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoLegal.POR_VENCER)
        self.assertEqual(resumen["alertas_creadas"], 1)
        alerta = self.alerta_de(documento)
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta.nivel, Alerta.ADVERTENCIA)
        self.assertIn("vence en 10 dia(s)", alerta.mensaje)

    def test_no_duplica_la_alerta_al_repetir_la_revision(self):
        """CU-90 Excepcion 2."""
        documento = self.documento(dias_al_vencimiento=5)
        cumplimiento.revisar_vencimientos()
        resumen = cumplimiento.revisar_vencimientos()

        self.assertEqual(resumen["alertas_creadas"], 0)
        self.assertEqual(resumen["alertas_mantenidas"], 1)
        self.assertEqual(
            Alerta.objects.filter(origen=Alerta.DOCUMENTO, documento=documento).count(), 1
        )

    def test_el_documento_vencido_queda_vencido_con_alerta_critica(self):
        documento = self.documento(nombre="Patente municipal", dias_al_vencimiento=-3)
        cumplimiento.revisar_vencimientos()

        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoLegal.VENCIDO)
        alerta = self.alerta_de(documento)
        self.assertEqual(alerta.nivel, Alerta.CRITICA)
        self.assertIn("vencio hace 3 dia(s)", alerta.mensaje)

    def test_la_alerta_sube_de_advertencia_a_critica_sin_duplicarse(self):
        documento = self.documento(dias_al_vencimiento=2)
        cumplimiento.revisar_vencimientos()
        self.assertEqual(self.alerta_de(documento).nivel, Alerta.ADVERTENCIA)

        # Tres dias despues el documento ya vencio.
        cumplimiento.revisar_vencimientos(hoy=self.hoy + timedelta(days=3))

        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoLegal.VENCIDO)
        self.assertEqual(
            Alerta.objects.filter(origen=Alerta.DOCUMENTO, documento=documento).count(), 1
        )
        self.assertEqual(self.alerta_de(documento).nivel, Alerta.CRITICA)

    def test_el_documento_lejos_de_vencer_no_genera_alerta(self):
        documento = self.documento(dias_al_vencimiento=200)
        resumen = cumplimiento.revisar_vencimientos()

        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoLegal.VIGENTE)
        self.assertEqual(resumen["alertas_creadas"], 0)
        self.assertIsNone(self.alerta_de(documento))

    def test_sin_umbral_configurado_usa_el_valor_por_defecto(self):
        """CU-90 Excepcion 1: la revision no se interrumpe."""
        ParametroConversion.objects.filter(clave=services.CLAVE_UMBRAL_DIAS).delete()
        documento = self.documento(dias_al_vencimiento=services.UMBRAL_DIAS_DEFECTO - 1)

        cumplimiento.revisar_vencimientos()

        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoLegal.POR_VENCER)
        self.assertIsNotNone(self.alerta_de(documento))

    def test_respeta_el_umbral_configurado(self):
        ParametroConversion.objects.update_or_create(
            clave=services.CLAVE_UMBRAL_DIAS,
            defaults={"nombre": "Aviso de vencimiento documental",
                      "valor": Decimal("5"), "unidad": "dias"},
        )
        documento = self.documento(dias_al_vencimiento=10)

        cumplimiento.revisar_vencimientos()

        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoLegal.VIGENTE)
        self.assertIsNone(self.alerta_de(documento))

    def test_el_command_corre_y_es_idempotente(self):
        documento = self.documento(dias_al_vencimiento=7)
        call_command("revisar_vencimientos_documentales")
        call_command("revisar_vencimientos_documentales")

        self.assertEqual(
            Alerta.objects.filter(origen=Alerta.DOCUMENTO, documento=documento).count(), 1
        )


# --- CU-91: tablero de cumplimiento -----------------------------------------


class TableroCumplimientoTests(CumplimientoTestBase):
    def url(self):
        return reverse("cumplimiento-tablero")

    def test_agrupa_por_estado_y_prioriza_por_proximidad(self):
        self.documento(nombre="Vence pronto", dias_al_vencimiento=3)
        self.documento(nombre="Ya vencido", dias_al_vencimiento=-10)
        self.documento(nombre="Al dia", dias_al_vencimiento=300)
        self.documento(nombre="Sin fechas")
        cumplimiento.revisar_vencimientos()

        respuesta = self.client.get(self.url())
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        datos = respuesta.data

        self.assertEqual(datos["resumen"][DocumentoLegal.VIGENTE], 1)
        self.assertEqual(datos["resumen"][DocumentoLegal.POR_VENCER], 1)
        self.assertEqual(datos["resumen"][DocumentoLegal.VENCIDO], 1)
        self.assertEqual(datos["resumen"][DocumentoLegal.SIN_VIGENCIA], 1)
        # Lo mas atrasado primero.
        self.assertEqual(
            [fila["nombre"] for fila in datos["pendientes"]],
            ["Ya vencido", "Vence pronto"],
        )
        self.assertEqual(datos["pendientes"][0]["dias_restantes"], -10)
        self.assertEqual(datos["pendientes"][0]["alerta_nivel"], Alerta.CRITICA)

    def test_los_sin_vigencia_van_aparte(self):
        """CU-91 Excepcion 3."""
        self.documento(nombre="Sin fechas todavia")

        datos = self.client.get(self.url()).data

        self.assertEqual(datos["pendientes"], [])
        self.assertEqual(len(datos["sin_vigencia"]), 1)
        self.assertEqual(datos["sin_vigencia"][0]["nombre"], "Sin fechas todavia")

    def test_sin_documentos_el_resumen_va_en_cero(self):
        """CU-91 Excepcion 1."""
        datos = self.client.get(self.url()).data

        self.assertEqual(datos["total"], 0)
        self.assertEqual(datos["resumen"][DocumentoLegal.VIGENTE], 0)
        self.assertEqual(datos["pendientes"], [])

    def test_filtra_por_tipo_de_documento(self):
        self.documento(nombre="Resolucion", dias_al_vencimiento=5)
        self.documento(
            nombre="Seguro de la flota", tipo=DocumentoLegal.SEGURO,
            dias_al_vencimiento=5,
        )

        datos = self.client.get(self.url(), {"tipo": DocumentoLegal.SEGURO}).data

        self.assertEqual(datos["total"], 1)
        self.assertEqual(datos["pendientes"][0]["nombre"], "Seguro de la flota")

    def test_el_operador_no_consulta_el_tablero(self):
        self.client.force_authenticate(self.operador)
        respuesta = self.client.get(self.url())
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)


# --- CU-92: historial de versiones ------------------------------------------


class HistorialVersionesTests(CumplimientoTestBase):
    def url(self, documento):
        return reverse("documento-legal-historial", args=[documento.pk])

    def con_versiones(self, cantidad):
        documento = self.documento(dias_al_vencimiento=100)
        for numero in range(1, cantidad + 1):
            documento.versiones.filter(vigente=True).update(vigente=False)
            VersionDocumento.objects.create(
                documento=documento,
                archivo=SimpleUploadedFile(
                    f"permiso-v{numero}.pdf", b"%PDF-1.4 contenido", "application/pdf"
                ),
                nombre_archivo=f"permiso-v{numero}.pdf",
                version=numero,
                usuario=self.admin,
                vigente=True,
            )
        return documento

    def test_lista_de_la_mas_reciente_a_la_mas_antigua(self):
        documento = self.con_versiones(3)

        respuesta = self.client.get(self.url(documento))
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        versiones = respuesta.data["versiones"]

        self.assertEqual([v["version"] for v in versiones], [3, 2, 1])
        self.assertTrue(versiones[0]["vigente"])
        self.assertFalse(any(v["vigente"] for v in versiones[1:]))
        self.assertEqual(versiones[0]["usuario_nombre"], "Admin Parte F")
        self.assertTrue(versiones[0]["archivo"])

    def test_una_sola_version_no_es_un_error(self):
        """CU-92 Excepcion 2."""
        documento = self.con_versiones(1)

        respuesta = self.client.get(self.url(documento))

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data["versiones"]), 1)
        self.assertTrue(respuesta.data["versiones"][0]["vigente"])

    def test_documento_inexistente(self):
        """CU-92 Excepcion 1."""
        respuesta = self.client.get("/api/v1/documentos-legales/9999/historial/")
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_el_operador_no_consulta_el_historial(self):
        documento = self.con_versiones(1)
        self.client.force_authenticate(self.operador)
        respuesta = self.client.get(self.url(documento))
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
