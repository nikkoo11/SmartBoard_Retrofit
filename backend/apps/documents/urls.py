from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import health, dashboard_summary, camera_status, BoardRecordViewSet, upload_image, analytics

router = DefaultRouter()
router.register(r'records', BoardRecordViewSet, basename='record')

urlpatterns = [
    path('health/', health, name='health'),
    path('dashboard/summary/', dashboard_summary, name='dashboard-summary'),
    path('camera/status/', camera_status, name='camera-status'),
    path('images/upload/', upload_image, name='image-upload'),
    path('analytics/', analytics, name='analytics'),
    path('', include(router.urls)),
]
