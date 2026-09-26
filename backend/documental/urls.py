from rest_framework.routers import DefaultRouter
from .views import DocumentoLegalViewSet, VersionDocumentoViewSet

router = DefaultRouter()
router.register(r'documentos', DocumentoLegalViewSet, basename='documento')
router.register(r'versiones-documento', VersionDocumentoViewSet, basename='version-documento')

urlpatterns = [
    # Las rutas se registran en el router principal (config/urls.py)
]

app_name = 'documental'
