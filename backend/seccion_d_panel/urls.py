from rest_framework.routers import DefaultRouter

from .views import C_PanelControl

router = DefaultRouter()
router.register(r"panel", C_PanelControl, basename="panel")

urlpatterns = router.urls
