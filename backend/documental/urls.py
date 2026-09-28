from rest_framework.routers import DefaultRouter

from .views import DocumentoLegalViewSet
from .views_cumplimiento import CumplimientoDocumentalViewSet

router = DefaultRouter()
router.register(r"documentos-legales", DocumentoLegalViewSet, basename="documento-legal")
router.register(r"cumplimiento", CumplimientoDocumentalViewSet, basename="cumplimiento")

urlpatterns = []
