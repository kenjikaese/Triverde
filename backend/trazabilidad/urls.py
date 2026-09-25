from rest_framework.routers import DefaultRouter

from .views import (
    CertificadoTrazabilidadViewSet,
    DeclaracionSinaderViewSet,
    IndicadorAmbientalViewSet,
)

router = DefaultRouter()
router.register(
    r"indicador-ambiental",
    IndicadorAmbientalViewSet,
    basename="indicador-ambiental",
)
# Parte A (CU-65 a CU-67): C_Certificados y C_Sinader.
router.register(r"certificados", CertificadoTrazabilidadViewSet, basename="certificado")
router.register(
    r"declaraciones-sinader", DeclaracionSinaderViewSet, basename="declaracion-sinader"
)

urlpatterns = []

