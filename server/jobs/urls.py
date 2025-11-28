from rest_framework.routers import DefaultRouter

from .views import AppViewSet, JobViewSet

router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'apps', AppViewSet, basename='app')

urlpatterns = router.urls

