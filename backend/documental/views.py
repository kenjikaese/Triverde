"""C_DocumentosLegales (docs/13): gestion documental, Parte E (CU-86 a CU-89).

La logica vive en `services.py`; aca se orquesta, se resuelven los permisos y
se audita. Todo es de Administrador. Los documentos no se eliminan (son
evidencia de cumplimiento), por eso el controlador no expone DELETE.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from common.auditoria import registrar_auditoria
from common.permissions import IsAdministrador
from common.trazas import traza
from common.views import fecha_o_none

from . import cumplimiento, services
from .models import DocumentoLegal
from .serializers import DocumentoLegalSerializer, VersionDocumentoSerializer


def _es_verdadero(valor):
    return str(valor).lower() in ("1", "true", "si", "on")


def _error_regla(error):
    cuerpo = {"detalle": error.mensaje}
    if error.campo:
        cuerpo[error.campo] = [error.mensaje]
    return Response(cuerpo, status=status.HTTP_400_BAD_REQUEST)


class DocumentoLegalViewSet(viewsets.ModelViewSet):
    queryset = DocumentoLegal.objects.prefetch_related("versiones__usuario").all()
    serializer_class = DocumentoLegalSerializer
    permission_classes = [IsAdministrador]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "head", "options"]
    search_fields = ["nombre", "entidad_emisora", "tipo_detalle"]
    ordering_fields = ["nombre", "fecha_vencimiento", "fecha_registro"]

    def get_queryset(self):
        queryset = super().get_queryset()
        for campo in ("estado", "tipo"):
            valor = self.request.query_params.get(campo)
            if valor:
                queryset = queryset.filter(**{campo: valor})
        return queryset

    def create(self, request, *args, **kwargs):
        """CU-86: registra el documento; advierte duplicados sin bloquear."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        duplicados = services.posibles_duplicados(
            serializer.validated_data["nombre"],
            serializer.validated_data["entidad_emisora"],
        )
        if duplicados and not _es_verdadero(request.data.get("confirmar")):
            # CU-86, Excepcion 3: sugiere renovar el existente; con `confirmar`
            # el administrador declara que es un documento distinto.
            traza("CU-86", "documento.posible_duplicado", existentes=[d.pk for d in duplicados])
            return Response(
                {
                    "detalle": (
                        "Ya existe un documento con el mismo nombre y entidad emisora. "
                        "Si corresponde al mismo documento, use la renovacion; si es "
                        "distinto, confirme el registro."
                    ),
                    "duplicados": DocumentoLegalSerializer(
                        duplicados, many=True, context=self.get_serializer_context()
                    ).data,
                },
                status=status.HTTP_409_CONFLICT,
            )
        documento = serializer.save()
        registrar_auditoria(
            request.user,
            "Registro de documento legal",
            "DocumentoLegal",
            documento.pk,
            f"{documento.get_tipo_display()}: {documento.nombre} ({documento.entidad_emisora})",
        )
        traza("CU-86", "documento.registrado", documento=documento.pk, tipo=documento.tipo)
        return Response(self.get_serializer(documento).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        documento = serializer.save()
        registrar_auditoria(
            self.request.user,
            "Edicion de documento legal",
            "DocumentoLegal",
            documento.pk,
            f"{documento.nombre} ({documento.entidad_emisora})",
        )

    @action(detail=True, methods=["post"])
    def versiones(self, request, pk=None):
        """CU-87: adjunta un archivo como nueva version vigente (multipart)."""
        documento = self.get_object()
        try:
            version = services.adjuntar_archivo(
                documento, request.FILES.get("archivo"), request.user
            )
        except services.ReglaDocumental as error:
            traza("CU-87", "documento.archivo_rechazado", documento=documento.pk, motivo=error.mensaje)
            return _error_regla(error)
        registrar_auditoria(
            request.user,
            "Adjunto de archivo de documento",
            "DocumentoLegal",
            documento.pk,
            f"Version {version.version}: {version.nombre_archivo}",
        )
        return Response(
            VersionDocumentoSerializer(version, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def historial(self, request, pk=None):
        """CU-92 (Parte F): versiones de la mas reciente a la mas antigua.

        Solo lectura: ni el documento ni sus versiones cambian. Cada version
        trae la URL de su archivo, para poder descargar las anteriores.
        """
        documento = self.get_object()
        versiones = cumplimiento.historial(documento)
        traza(
            "CU-92",
            "historial.consultado",
            documento=documento.pk,
            versiones=versiones.count(),
        )
        return Response(
            {
                "documento": self.get_serializer(documento).data,
                "versiones": VersionDocumentoSerializer(
                    versiones, many=True, context=self.get_serializer_context()
                ).data,
            }
        )

    @action(detail=True, methods=["post"])
    def vigencia(self, request, pk=None):
        """CU-88: registra emision y vencimiento; el estado se deriva."""
        documento = self.get_object()
        try:
            documento = services.registrar_vigencia(
                documento,
                fecha_o_none(request.data.get("fecha_emision")),
                fecha_o_none(request.data.get("fecha_vencimiento")),
            )
        except services.ReglaDocumental as error:
            return _error_regla(error)
        registrar_auditoria(
            request.user,
            "Registro de vigencia de documento",
            "DocumentoLegal",
            documento.pk,
            f"{documento.fecha_emision} a {documento.fecha_vencimiento}: {documento.estado}",
        )
        return Response(self.get_serializer(documento).data)

    @action(detail=True, methods=["post"])
    def renovar(self, request, pk=None):
        """CU-89: nuevo archivo + nueva vigencia; conserva el historial."""
        documento = self.get_object()
        try:
            documento, version = services.renovar(
                documento,
                request.FILES.get("archivo"),
                fecha_o_none(request.data.get("fecha_emision")),
                fecha_o_none(request.data.get("fecha_vencimiento")),
                request.user,
                confirmar=_es_verdadero(request.data.get("confirmar")),
            )
        except services.RenovacionInnecesaria:
            return Response(
                {
                    "detalle": (
                        "El documento esta vigente y no esta proximo a vencer; no es "
                        "necesaria una renovacion. Confirme si desea renovarlo igual."
                    ),
                    "requiere_confirmacion": True,
                },
                status=status.HTTP_409_CONFLICT,
            )
        except services.ReglaDocumental as error:
            return _error_regla(error)
        registrar_auditoria(
            request.user,
            "Renovacion de documento legal",
            "DocumentoLegal",
            documento.pk,
            f"Version {version.version}, vigente hasta {documento.fecha_vencimiento}",
        )
        return Response(self.get_serializer(documento).data)
