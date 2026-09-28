from rest_framework.routers import DefaultRouter

from .views import DocumentoLegalViewSet

router = DefaultRouter()
router.register(r"documentos-legales", DocumentoLegalViewSet, basename="documento-legal")

urlpatterns = []
