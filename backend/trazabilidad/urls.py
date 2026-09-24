from rest_framework.routers import DefaultRouter

from .views import IndicadorAmbientalViewSet

router = DefaultRouter()
router.register(
    r"indicador-ambiental",
    IndicadorAmbientalViewSet,
    basename="indicador-ambiental",
)

urlpatterns = []

