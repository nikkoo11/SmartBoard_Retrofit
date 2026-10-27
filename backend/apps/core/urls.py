from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (CourseViewSet, CourseMeetingViewSet, LessonSessionViewSet, CaptureViewSet, PdfDocumentViewSet,
                    device_status, device_capture, device_end_session, device_finalize,
                    auth_login, auth_logout, auth_me, csrf_token)

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'meetings', CourseMeetingViewSet)
router.register(r'sessions', LessonSessionViewSet)
router.register(r'captures', CaptureViewSet)
router.register(r'pdfs', PdfDocumentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('device/status/', device_status, name='device-status'),
    path('device/capture/', device_capture, name='device-capture'),
    path('device/end-session/', device_end_session, name='device-end-session'),
    path('device/finalize/', device_finalize, name='device-finalize'),
    path('auth/login/', auth_login, name='auth-login'),
    path('auth/logout/', auth_logout, name='auth-logout'),
    path('auth/me/', auth_me, name='auth-me'),
    path('csrf-token/', csrf_token, name='csrf-token'),
]