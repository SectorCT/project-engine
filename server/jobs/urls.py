from rest_framework.routers import DefaultRouter

from .views import AppViewSet, JobMessageViewSet, JobViewSet, TicketViewSet

router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'apps', AppViewSet, basename='app')
router.register(r'job-messages', JobMessageViewSet, basename='job-message')
router.register(r'tickets', TicketViewSet, basename='ticket')

urlpatterns = router.urls

