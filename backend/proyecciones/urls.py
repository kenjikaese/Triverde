from rest_framework.routers import DefaultRouter
from .views import ProyeccionViewSet

router = DefaultRouter()
router.register(r'proyecciones', ProyeccionViewSet, basename='proyecciones')

urlpatterns = [
    # Las rutas se registran en el router principal (config/urls.py)
]

# Exportar el router para que se pueda importar en config/urls.py
app_name = 'proyecciones'
