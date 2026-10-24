from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.core.files.base import ContentFile
from django.conf import settings
import os
import time
import cv2
from .models import Course, LessonSession, Capture, PdfDocument
from .serializers import CourseSerializer, LessonSessionSerializer, CaptureSerializer, PdfDocumentSerializer
from .pdf_service import build_session_pdf
from .ocr_service import run_ocr
from .cleaning_service import clean_for_ocr, clean_board_image


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
        try:
            strength = float(request.query_params.get('strength', 0.5))
        except (TypeError, ValueError):
            strength = 0.5
        strength = max(0.0, min(1.0, strength))
        start = time.time()
        try:
            result = clean_board_image(input_path, output_path, strength=strength)
        except Exception as exc:
            return Response({'detail': 'Could not clean image: %s' % exc}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elapsed_ms = int((time.time() - start) * 1000)
        with open(output_path, 'rb') as f:
            capture.cleaned_image.save(filename, ContentFile(f.read()), save=False)
        capture.clean_ms = elapsed_ms
        capture.save()
        serializer = CaptureSerializer(capture, context={'request': request})
        data = serializer.data
        data['cropped'] = bool(result.get('cropped')) if isinstance(result, dict) else False
        data['crop_note'] = result.get('crop_note') if isinstance(result, dict) else None
        data['strength'] = strength
        return Response(data, status=status.HTTP_200_OK)


    @action(detail=True, methods=['post'], url_path='ocr')
    def ocr(self, request, pk=None):
        capture = self.get_object()
        source = request.query_params.get('source', None)
        psm = int(request.query_params.get('psm', 6))
        save = request.query_params.get('save', '0') == '1'
        if psm not in (3, 4, 6, 11):
            return Response({'detail': 'Invalid psm.'}, status=status.HTTP_400_BAD_REQUEST)
        if not capture.image:
            return Response({'detail': 'Capture has no image.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if source is None:
            source = 'cleaned' if (capture.cleaned_image and os.path.exists(capture.cleaned_image.path)) else 'original'
        if source not in ('original', 'cleaned', 'threshold'):
            return Response({'detail': 'Invalid source.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if source == 'original':
                img = cv2.imread(capture.image.path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    raise ValueError('Cannot read image')
            elif source == 'cleaned':
                if not (capture.cleaned_image and os.path.exists(capture.cleaned_image.path)):
                    return Response({'detail': 'No cleaned image.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                img = cv2.imread(capture.cleaned_image.path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    raise ValueError('Cannot read image')
            else:
                img = clean_for_ocr(capture.image.path)
        except Exception as exc:
            return Response({'detail': 'Could not prepare image: %s' % exc}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            result = run_ocr(img, psm=psm)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if save and result['text'].strip():
            capture.extracted_text = result['text']
            capture.save()
        saved = bool(save and result['text'].strip())
        payload = {'source': source, 'psm': psm, 'text': result['text'], 'confidence': result['confidence'], 'ms': result['ms'], 'saved': saved}
        if not result['text'].strip():
            payload['detail'] = 'No text was detected.'
        return Response(payload, status=status.HTTP_200_OK)

class PdfDocumentViewSet(viewsets.ModelViewSet):
    queryset = PdfDocument.objects.select_related('session', 'session__course').order_by('-created_at')
    serializer_class = PdfDocumentSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['session__title', 'session__course__name']
    filterset_fields = ['session']