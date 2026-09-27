"""Pruebas del Modulo 12, Parte E (CU-86 a CU-89)."""
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from acceso.models import BitacoraAuditoria, Rol, Usuario
from configuracion.models import ParametroConversion
from mezcla.models import Alerta

from . import services
from .models import DocumentoLegal, VersionDocumento

MEDIA_TEMPORAL = tempfile.mkdtemp()
URL = "/api/v1/documentos-legales/"


def pdf(nombre="permiso.pdf", tamano=1024):
    return SimpleUploadedFile(nombre, b"%PDF-1.4 " + b"x" * tamano, "application/pdf")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class DocumentalTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        rol_admin = Rol.objects.create(nombre=Rol.ADMINISTRADOR)
        rol_operador = Rol.objects.create(nombre=Rol.OPERADOR)
        cls.admin = Usuario.objects.create_user(
            username="admin-m12", password="clave-segura", rol=rol_admin,
            nombre_completo="Admin M12",
        )
        cls.operador = Usuario.objects.create_user(
            username="operador-m12", password="clave-segura", rol=rol_operador,
            nombre_completo="Operador M12",
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        self.client.force_authenticate(self.admin)
        self.hoy = timezone.localdate()

    def crear_documento(self, **extra):
        datos = {
            "nombre": "Resolucion sanitaria",
            "tipo": DocumentoLegal.RESOLUCION,
            "entidad_emisora": "SEREMI de Salud",
        }
        datos.update(extra)
        return DocumentoLegal.objects.create(**datos)


class RegistroDocumentoTests(DocumentalTestBase):
    """CU-86."""

    def test_registrar_con_nombre_y_entidad_crea_sin_vigencia(self):
        respuesta = self.client.post(
            URL,
            {"nombre": "Permiso municipal", "tipo": "permiso", "entidad_emisora": "Municipalidad de Colina"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        documento = DocumentoLegal.objects.get(pk=respuesta.data["id"])
        self.assertEqual(documento.estado, DocumentoLegal.SIN_VIGENCIA)
        self.assertIsNone(respuesta.data["version_vigente"])
        self.assertTrue(
            BitacoraAuditoria.objects.filter(
                entidad_afectada="DocumentoLegal", id_objeto=str(documento.pk)
            ).exists()
        )

    def test_sin_nombre_no_se_crea(self):
        respuesta = self.client.post(
            URL, {"nombre": "  ", "tipo": "permiso", "entidad_emisora": "SAG"}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nombre", respuesta.data)
        self.assertFalse(DocumentoLegal.objects.exists())

    def test_sin_entidad_emisora_no_se_crea(self):
        respuesta = self.client.post(URL, {"nombre": "Seguro", "tipo": "seguro"}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("entidad_emisora", respuesta.data)

    def test_tipo_otro_exige_descripcion_libre(self):
        sin_detalle = self.client.post(
            URL, {"nombre": "Acta", "tipo": "otro", "entidad_emisora": "Notaria"}, format="json"
        )
        self.assertEqual(sin_detalle.status_code, status.HTTP_400_BAD_REQUEST)
        con_detalle = self.client.post(
            URL,
            {"nombre": "Acta", "tipo": "otro", "tipo_detalle": "Acta notarial", "entidad_emisora": "Notaria"},
            format="json",
        )
        self.assertEqual(con_detalle.status_code, status.HTTP_201_CREATED)

    def test_duplicado_advierte_y_permite_continuar_con_confirmacion(self):
        existente = self.crear_documento()
        datos = {
            "nombre": "resolucion sanitaria",
            "tipo": "resolucion",
            "entidad_emisora": "SEREMI DE SALUD",
        }
        advertencia = self.client.post(URL, datos, format="json")
        self.assertEqual(advertencia.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(advertencia.data["duplicados"][0]["id"], existente.pk)
        self.assertEqual(DocumentoLegal.objects.count(), 1)

        confirmado = self.client.post(URL, {**datos, "confirmar": True}, format="json")
        self.assertEqual(confirmado.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DocumentoLegal.objects.count(), 2)

    def test_la_vigencia_no_se_edita_por_el_registro(self):
        documento = self.crear_documento()
        self.client.patch(
            f"{URL}{documento.pk}/",
            {"fecha_vencimiento": "2030-01-01", "estado": "vigente"},
            format="json",
        )
        documento.refresh_from_db()
        self.assertIsNone(documento.fecha_vencimiento)
        self.assertEqual(documento.estado, DocumentoLegal.SIN_VIGENCIA)

    def test_no_se_puede_eliminar(self):
        documento = self.crear_documento()
        respuesta = self.client.delete(f"{URL}{documento.pk}/")
        self.assertEqual(respuesta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class AdjuntoArchivoTests(DocumentalTestBase):
    """CU-87."""

    def test_adjuntar_crea_version_vigente_y_conserva_la_anterior(self):
        documento = self.crear_documento()
        primera = self.client.post(f"{URL}{documento.pk}/versiones/", {"archivo": pdf("v1.pdf")})
        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)
        segunda = self.client.post(f"{URL}{documento.pk}/versiones/", {"archivo": pdf("v2.pdf")})
        self.assertEqual(segunda.status_code, status.HTTP_201_CREATED)

        versiones = list(documento.versiones.order_by("version"))
        self.assertEqual([v.version for v in versiones], [1, 2])
        self.assertEqual([v.vigente for v in versiones], [False, True])
        self.assertEqual(versiones[1].usuario, self.admin)
        self.assertEqual(versiones[1].nombre_archivo, "v2.pdf")

    def test_formato_no_soportado_se_rechaza(self):
        documento = self.crear_documento()
        archivo = SimpleUploadedFile("script.exe", b"MZ", "application/octet-stream")
        respuesta = self.client.post(f"{URL}{documento.pk}/versiones/", {"archivo": archivo})
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("archivo", respuesta.data)
        self.assertFalse(VersionDocumento.objects.exists())

    def test_archivo_que_excede_el_tamano_configurado_se_rechaza(self):
        ParametroConversion.objects.create(
            clave=services.CLAVE_TAMANO_MAX_MB, nombre="Tamano maximo", valor=Decimal("0.001")
        )
        documento = self.crear_documento()
        respuesta = self.client.post(
            f"{URL}{documento.pk}/versiones/", {"archivo": pdf(tamano=4096)}
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(VersionDocumento.objects.exists())

    def test_documento_inexistente_responde_404(self):
        respuesta = self.client.post(f"{URL}999/versiones/", {"archivo": pdf()})
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)


class VigenciaTests(DocumentalTestBase):
    """CU-88."""

    def registrar(self, documento, emision, vencimiento):
        return self.client.post(
            f"{URL}{documento.pk}/vigencia/",
            {"fecha_emision": emision, "fecha_vencimiento": vencimiento},
            format="json",
        )

    def test_vencimiento_lejano_deja_vigente(self):
        documento = self.crear_documento()
        respuesta = self.registrar(
            documento, self.hoy.isoformat(), (self.hoy + timedelta(days=365)).isoformat()
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["estado"], DocumentoLegal.VIGENTE)

    def test_vencimiento_dentro_del_umbral_deja_por_vencer(self):
        ParametroConversion.objects.create(
            clave=services.CLAVE_UMBRAL_DIAS, nombre="Umbral", valor=Decimal("60")
        )
        documento = self.crear_documento()
        respuesta = self.registrar(
            documento, self.hoy.isoformat(), (self.hoy + timedelta(days=45)).isoformat()
        )
        self.assertEqual(respuesta.data["estado"], DocumentoLegal.POR_VENCER)

    def test_vencimiento_pasado_deja_vencido(self):
        documento = self.crear_documento()
        respuesta = self.registrar(
            documento,
            (self.hoy - timedelta(days=400)).isoformat(),
            (self.hoy - timedelta(days=1)).isoformat(),
        )
        self.assertEqual(respuesta.data["estado"], DocumentoLegal.VENCIDO)

    def test_vencimiento_anterior_a_emision_se_rechaza(self):
        documento = self.crear_documento()
        respuesta = self.registrar(documento, "2026-06-01", "2026-05-01")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_vencimiento", respuesta.data)
        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoLegal.SIN_VIGENCIA)

    def test_fecha_incompleta_o_invalida_se_rechaza(self):
        documento = self.crear_documento()
        respuesta = self.registrar(documento, "hola", "2026-05-01")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_emision", respuesta.data)


class RenovacionTests(DocumentalTestBase):
    """CU-89."""

    def documento_por_vencer(self):
        return self.crear_documento(
            fecha_emision=self.hoy - timedelta(days=350),
            fecha_vencimiento=self.hoy + timedelta(days=10),
            estado=DocumentoLegal.POR_VENCER,
        )

    def renovar(self, documento, vencimiento, **extra):
        datos = {
            "archivo": pdf("renovado.pdf"),
            "fecha_emision": self.hoy.isoformat(),
            "fecha_vencimiento": vencimiento.isoformat(),
        }
        datos.update(extra)
        return self.client.post(f"{URL}{documento.pk}/renovar/", datos)

    def test_renovar_suma_version_actualiza_fechas_y_deja_vigente(self):
        documento = self.documento_por_vencer()
        services.adjuntar_archivo(documento, pdf("original.pdf"), self.admin)
        nuevo_vencimiento = self.hoy + timedelta(days=365)

        respuesta = self.renovar(documento, nuevo_vencimiento)
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoLegal.VIGENTE)
        self.assertEqual(documento.fecha_vencimiento, nuevo_vencimiento)
        versiones = list(documento.versiones.order_by("version"))
        self.assertEqual(len(versiones), 2)
        self.assertFalse(versiones[0].vigente)
        self.assertTrue(versiones[1].vigente)
        # El historial conserva la vigencia anterior junto a su version.
        self.assertEqual(versiones[0].fecha_vencimiento, self.hoy + timedelta(days=10))
        self.assertEqual(versiones[1].fecha_vencimiento, nuevo_vencimiento)

    def test_vencimiento_no_posterior_a_la_vigencia_actual_se_rechaza(self):
        documento = self.documento_por_vencer()
        respuesta = self.renovar(documento, documento.fecha_vencimiento)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(documento.versiones.exists())

    def test_documento_vigente_pide_confirmacion(self):
        documento = self.crear_documento(
            fecha_emision=self.hoy,
            fecha_vencimiento=self.hoy + timedelta(days=300),
            estado=DocumentoLegal.VIGENTE,
        )
        sin_confirmar = self.renovar(documento, self.hoy + timedelta(days=700))
        self.assertEqual(sin_confirmar.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(sin_confirmar.data["requiere_confirmacion"])

        confirmado = self.renovar(documento, self.hoy + timedelta(days=700), confirmar="true")
        self.assertEqual(confirmado.status_code, status.HTTP_200_OK)

    def test_archivo_invalido_no_renueva(self):
        documento = self.documento_por_vencer()
        respuesta = self.renovar(
            documento,
            self.hoy + timedelta(days=365),
            archivo=SimpleUploadedFile("nota.txt", b"texto", "text/plain"),
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoLegal.POR_VENCER)

    def test_renovar_resuelve_la_alerta_activa_del_documento(self):
        documento = self.documento_por_vencer()
        alerta = Alerta.objects.create(
            origen=Alerta.DOCUMENTO,
            documento=documento,
            nivel="advertencia",
            mensaje="Documento por vencer",
            clave=f"documento:{documento.pk}",
        )
        self.renovar(documento, self.hoy + timedelta(days=365))
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, Alerta.RESUELTA)


class PermisosDocumentalTests(DocumentalTestBase):
    def test_operador_no_accede_a_la_gestion_documental(self):
        self.client.force_authenticate(self.operador)
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_403_FORBIDDEN)
        respuesta = self.client.post(
            URL, {"nombre": "X", "tipo": "permiso", "entidad_emisora": "Y"}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)


class EstadoDerivadoTests(DocumentalTestBase):
    def test_calcular_estado_en_los_bordes_del_umbral(self):
        hoy = self.hoy
        self.assertEqual(services.calcular_estado(None, hoy, 30), DocumentoLegal.SIN_VIGENCIA)
        self.assertEqual(services.calcular_estado(hoy, hoy, 30), DocumentoLegal.POR_VENCER)
        self.assertEqual(
            services.calcular_estado(hoy + timedelta(days=30), hoy, 30), DocumentoLegal.POR_VENCER
        )
        self.assertEqual(
            services.calcular_estado(hoy + timedelta(days=31), hoy, 30), DocumentoLegal.VIGENTE
        )
        self.assertEqual(
            services.calcular_estado(hoy - timedelta(days=1), hoy, 30), DocumentoLegal.VENCIDO
        )
