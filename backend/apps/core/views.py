from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.core.files.base import ContentFile
from .models import Course, LessonSession, Capture, PdfDocument
from .serializers import CourseSerializer, LessonSessionSerializer, CaptureSerializer, PdfDocumentSerializer
from .pdf_service import build_session_pdf


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().order_by('code')
    serializer_class = CourseSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code', 'section']


class LessonSessionViewSet(viewsets.ModelViewSet):
    queryset = LessonSession.objects.select_related('course').order_by('-date', '-created_at')
    serializer_class = LessonSessionSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['title', 'notes']
    filterset_fields = ['course', 'status']

    @action(detail=True, methods=['post'], url_path='generate-pdf')
    def generate_pdf(self, request, pk=None):
        session = self.get_object()
        if session.captures.count() == 0:
            return Response({'detail': 'This session has no captures yet.'}, status=status.HTTP_400_BAD_REQUEST)
        pdf_bytes = build_session_pdf(session)
        filename = 'session_%s.pdf' % session.id
        pdf_doc = PdfDocument(session=session)
        pdf_doc.file.save(filename, ContentFile(pdf_bytes))
        pdf_doc.save()
        serializer = PdfDocumentSerializer(pdf_doc, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CaptureViewSet(viewsets.ModelViewSet):
    queryset = Capture.objects.select_related('session').order_by('-created_at')
    serializer_class = CaptureSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['session']


class PdfDocumentViewSet(viewsets.ModelViewSet):
    queryset = PdfDocument.objects.select_related('session', 'session__course').order_by('-created_at')
    serializer_class = PdfDocumentSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['session__title', 'session__course__name']
    filterset_fields = ['session']