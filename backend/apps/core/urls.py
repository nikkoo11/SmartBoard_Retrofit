from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import CourseViewSet, LessonSessionViewSet, CaptureViewSet, PdfDocumentViewSet

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'sessions', LessonSessionViewSet)
router.register(r'captures', CaptureViewSet)
router.register(r'pdfs', PdfDocumentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

