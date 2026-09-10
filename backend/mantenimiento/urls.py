from rest_framework.routers import DefaultRouter

from .views import MaquinariaViewSet, MantencionViewSet, RegistroUsoViewSet

router = DefaultRouter()
router.register("maquinaria", MaquinariaViewSet, basename="maquinaria")
router.register("registros-uso", RegistroUsoViewSet, basename="registro-uso")
router.register("mantenciones", MantencionViewSet, basename="mantencion")

urlpatterns = router.urls
