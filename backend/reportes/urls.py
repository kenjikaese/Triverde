from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("reportes", views.ReporteViewSet, basename="reporte")
router.register("panel", views.PanelControlViewSet, basename="panel")

urlpatterns = router.urls
