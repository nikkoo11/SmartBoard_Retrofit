from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.core.files.base import ContentFile
from django.conf import settings
import os
import time
from .models import Course, LessonSession, Capture, PdfDocument
from .serializers import CourseSerializer, LessonSessionSerializer, CaptureSerializer, PdfDocumentSerializer
from .pdf_service import build_session_pdf
from .cleaning_service import clean_board_image


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

    @action(detail=True, methods=['post'], url_path='clean')
    def clean(self, request, pk=None):
        capture = self.get_object()
        if not capture.image:
            return Response({'detail': 'Capture has no image file.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        input_path = capture.image.path
        if not os.path.exists(input_path):
            return Response({'detail': 'Original image file is missing.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        media_root = settings.MEDIA_ROOT
        output_dir = os.path.join(media_root, 'board_cleaned')
        os.makedirs(output_dir, exist_ok=True)
        filename = 'cleaned_%s.png' % capture.id
        output_path = os.path.join(output_dir, filename)
        start = time.time()
        try:
            clean_board_image(input_path, output_path)
        except Exception as exc:
            return Response({'detail': 'Could not clean image: %s' % exc}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elapsed_ms = int((time.time() - start) * 1000)
        with open(output_path, 'rb') as f:
            capture.cleaned_image.save(filename, ContentFile(f.read()), save=False)
        capture.clean_ms = elapsed_ms
        capture.save()
        serializer = CaptureSerializer(capture, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PdfDocumentViewSet(viewsets.ModelViewSet):
    queryset = PdfDocument.objects.select_related('session', 'session__course').order_by('-created_at')
    serializer_class = PdfDocumentSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['session__title', 'session__course__name']
    filterset_fields = ['session']