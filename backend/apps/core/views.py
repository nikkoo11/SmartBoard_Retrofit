from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.http import JsonResponse
from django.db import transaction
import logging
import os
import time
import cv2
from .models import Course, CourseMeeting, LessonSession, Capture, PdfDocument, CameraState
from .serializers import (CourseSerializer, CourseMeetingSerializer, LessonSessionSerializer,
                          CaptureSerializer, PdfDocumentSerializer)
from .pdf_service import build_session_pdf, build_capture_pdf
from .ocr_service import run_ocr, run_gemini_ocr
from .cleaning_service import clean_for_ocr, clean_board_image, find_text_region

logger = logging.getLogger(__name__)

from django.middleware.csrf import CsrfViewMiddleware


def _enforce_login_csrf(request):
    """Explicitly enforce Django CSRF checks for the anonymous login endpoint."""
    middleware = CsrfViewMiddleware(lambda req: None)
    return middleware.process_view(request, lambda req: None, (), {})

# ---------------------------------------------------------------- device auth


def _device_token_ok(request):
    """Constant-time check of the shared device token from the Authorization header."""
    import hmac
    expected = getattr(settings, 'DEVICE_TOKEN', '')
    if not expected:
        return False  # no token configured -> device endpoints disabled
    header = request.META.get('HTTP_AUTHORIZATION', '')
    supplied = header[6:] if header.startswith('Token ') else header
    return bool(supplied) and hmac.compare_digest(supplied, expected)


def _device_forbidden():
    return Response({'detail': 'Invalid or missing device token.'},
                    status=status.HTTP_401_UNAUTHORIZED)


def _enforce_csrf(request):
    """Enforce Django CSRF validation on a DRF view.

    DRF's ``@api_view`` wraps every view in ``csrf_exempt`` (see
    ``APIView.as_view``), so Django's middleware-level CSRF check never runs
    on DRF routes. DRF's own ``SessionAuthentication.enforce_csrf`` only runs
    when a user is *already* authenticated, which leaves the anonymous login
    endpoint unprotected.

    This reuses DRF's supported ``CSRFCheck`` helper (a ``CsrfViewMiddleware``
    subclass) so behavior stays consistent with the rest of the framework.
    Raises ``rest_framework.exceptions.PermissionDenied`` (HTTP 403) when the
    request lacks a valid CSRF token.
    """
    from rest_framework.authentication import CSRFCheck

    def dummy_get_response(request):
        return None

    check = CSRFCheck(dummy_get_response)
    # process_request populates request.META['CSRF_COOKIE'] used by process_view
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        from rest_framework import exceptions
        raise exceptions.PermissionDenied('CSRF Failed: %s' % reason)


def _get_camera_state():
    state, _ = CameraState.objects.get_or_create(pk=1)
    return state


def _armed_session(state, now=None):
    """Return the armed LessonSession if the state is valid and unexpired, else None."""
    if state.armed_session_id is None:
        return None
    now = now or timezone.now()
    if state.expires_at is not None and state.expires_at <= now:
        return None
    return state.armed_session


def _clear_camera_state(state, save=True):
    state.armed_session = None
    state.armed_at = None
    state.expires_at = None
    if save:
        state.save()


def _validate_jpeg_upload(file_obj):
    """Validate an uploaded camera image. Returns (ok, error_detail)."""
    if file_obj is None:
        return False, 'No image provided.'
    max_bytes = getattr(settings, 'DEVICE_UPLOAD_MAX_BYTES', 10 * 1024 * 1024)
    if file_obj.size > max_bytes:
        return False, 'File too large.'
    if file_obj.size < 1024:
        return False, 'File too small to be a valid image.'
    content_type = getattr(file_obj, 'content_type', '') or ''
    if content_type not in ('image/jpeg', 'image/jpg'):
        return False, 'Only JPEG images are accepted.'
    data = file_obj.read()
    file_obj.seek(0)
    if not data.startswith(b'\xff\xd8'):
        return False, 'File is not a valid JPEG.'
    import numpy as np
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False, 'Image could not be decoded.'
    return True, None


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().order_by('code')
    serializer_class = CourseSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code', 'section']

class CourseMeetingViewSet(viewsets.ModelViewSet):
    queryset = CourseMeeting.objects.select_related('course').order_by('course', 'weekday', 'start_time')
    serializer_class = CourseMeetingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['course']


class LessonSessionViewSet(viewsets.ModelViewSet):
    queryset = LessonSession.objects.select_related('course').order_by('-date', '-created_at')
    serializer_class = LessonSessionSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['title', 'notes']
    filterset_fields = ['course', 'status']

    @action(detail=False, methods=['post'], url_path='start-now')
    def start_now(self, request):
        """Create (or resume) today's session for the class that is scheduled now.
 
        - Optional body: {"course": <id>} to choose a course by hand.
        - Without a course, the weekly meetings (CourseMeeting) are checked.
        - A meeting counts as "now" from 15 minutes before it starts until it ends.
        - If the same course already has an open session from today, that session
          is returned (resume). If the open session is from an older day, the
          teacher must finalize it first.
        This only creates the session (status "draft"). The camera is armed
        with the existing /sessions/<id>/arm/ endpoint.
        """
        now = timezone.now()
        if timezone.is_aware(now):
            now = timezone.localtime(now)
        today = now.date()
 
        course_id = request.data.get('course')
        if course_id:
            try:
                course = Course.objects.get(pk=course_id)
            except (Course.DoesNotExist, ValueError, TypeError):
                return Response({'detail': 'Course not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            soon = (now + timedelta(minutes=15)).time()
            current = now.time()
            meetings = CourseMeeting.objects.select_related('course').filter(
                weekday=now.weekday(), start_time__lte=soon, end_time__gte=current)
            courses = {}
            for m in meetings:
                courses[m.course_id] = m.course
            if not courses:
                return Response(
                    {'detail': 'No class is scheduled right now. Please choose a course.'},
                    status=status.HTTP_404_NOT_FOUND)
            if len(courses) > 1:
                return Response({
                    'detail': 'More than one class is scheduled now. Please choose one.',
                    'choices': [{'id': c.id, 'code': c.code, 'name': c.name, 'section': c.section}
                                for c in courses.values()],
                }, status=status.HTTP_409_CONFLICT)
            course = list(courses.values())[0]
 
        existing = LessonSession.objects.filter(
            course=course, status__in=LessonSession.OPEN_STATUSES
        ).order_by('-date', '-created_at').first()
        if existing is not None:
            if existing.date == today:
                return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
            return Response({
                'detail': 'Session "%s" (%s) is still open for this class. Finalize it first.'
                          % (existing.title, existing.date),
                'open_session': existing.id,
            }, status=status.HTTP_409_CONFLICT)
 
        session = LessonSession.objects.create(
            course=course,
            title='%s - %s' % (course.code, now.strftime('%a %b %d')),
            date=today,
            status='draft',
            started_at=now,
        )
        return Response(self.get_serializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='generate-pdf')
    def generate_pdf(self, request, pk=None):
        session = self.get_object()
        if session.captures.count() == 0:
            return Response({'detail': 'This session has no captures yet.'}, status=status.HTTP_400_BAD_REQUEST)
        pdf_bytes = build_session_pdf(session)
        if not pdf_bytes:
            return Response({'detail': 'PDF generation failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        with transaction.atomic():
            locked_session = LessonSession.objects.select_for_update().get(pk=session.pk)
            pdf_doc = PdfDocument.objects.filter(session=locked_session).order_by('-created_at').first()
            created = pdf_doc is None
            if created:
                pdf_doc = PdfDocument(session=locked_session)
            filename = 'session_%s.pdf' % locked_session.id
            pdf_doc.file.save(filename, ContentFile(pdf_bytes), save=False)
            pdf_doc.save()
        serializer = PdfDocumentSerializer(pdf_doc, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='arm')
    def arm(self, request, pk=None):
        """Explicitly arm this session for the camera."""
        session = self.get_object()
        if session.status == 'finalized':
            return Response({'detail': 'Cannot arm a finalized session.'},
                            status=status.HTTP_409_CONFLICT)
        state = _get_camera_state()
        current = _armed_session(state)
        if current is not None and current.pk != session.pk:
            return Response(
                {'detail': 'Another session (%s) is currently armed. Disarm it first.'
                    % current.pk},
                status=status.HTTP_409_CONFLICT)
        minutes = getattr(settings, 'DEVICE_SESSION_TIMEOUT_MINUTES', 120)
        try:
            minutes = int(request.data.get('timeout_minutes', minutes))
        except (TypeError, ValueError):
            minutes = getattr(settings, 'DEVICE_SESSION_TIMEOUT_MINUTES', 120)
        minutes = max(1, min(minutes, 24 * 60))
        now = timezone.now()
        state.armed_session = session
        state.armed_at = now
        state.expires_at = now + timedelta(minutes=minutes)
        state.save()
        if session.status != 'capturing':
            session.status = 'capturing'
            session.save(update_fields=['status'])
        return Response({
            'id': session.id, 'status': session.status, 'armed': True,
            'expires_at': state.expires_at,
        })

    @action(detail=True, methods=['post'], url_path='disarm')
    def disarm(self, request, pk=None):
        """Safely disarm this session (teacher-initiated)."""
        session = self.get_object()
        state = _get_camera_state()
        if state.armed_session_id != session.pk:
            return Response({'detail': 'This session is not the armed session.'},
                            status=status.HTTP_409_CONFLICT)
        _clear_camera_state(state)
        if session.status == 'capturing':
            session.status = 'processing'
            session.save(update_fields=['status'])
        return Response({'id': session.id, 'status': session.status, 'armed': False})


class CaptureViewSet(viewsets.ModelViewSet):
    queryset = Capture.objects.select_related('session').order_by('-created_at')
    serializer_class = CaptureSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['session']

    @action(detail=True, methods=['post'], url_path='clean')
    def clean(self, request, pk=None):
        capture = self.get_object()
        if not capture.image:
            capture.status = 'failed'
            capture.error_message = 'Capture has no image file.'
            capture.save(update_fields=['status', 'error_message'])
            return Response({'detail': 'Capture has no image file.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        capture.status = 'processing'
        capture.error_message = ''
        capture.save(update_fields=['status', 'error_message'])
        input_path = capture.image.path
        if not os.path.exists(input_path):
            capture.status = 'failed'
            capture.error_message = 'Original image file is missing.'
            capture.save(update_fields=['status', 'error_message'])
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
            capture.status = 'failed'
            capture.error_message = str(exc)[:500]
            capture.save(update_fields=['status', 'error_message'])
            return Response({'detail': 'Could not clean image: %s' % exc}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elapsed_ms = int((time.time() - start) * 1000)
        with open(output_path, 'rb') as f:
            capture.cleaned_image.save(filename, ContentFile(f.read()), save=False)
        capture.clean_ms = elapsed_ms
        capture.status = 'done'
        from django.utils import timezone
        capture.processed_at = timezone.now()
        capture.save()
        serializer = CaptureSerializer(capture, context={'request': request})
        data = serializer.data
        data['cropped'] = bool(result.get('cropped')) if isinstance(result, dict) else False
        data['crop_note'] = result.get('crop_note') if isinstance(result, dict) else None
        data['strength'] = strength
        return Response(data, status=status.HTTP_200_OK)


    @action(detail=True, methods=['post'], url_path='generate-pdf')
    def generate_pdf(self, request, pk=None):
        capture = self.get_object()
        if not capture.extracted_text or not capture.extracted_text.strip():
            return Response({'detail': 'Capture has no extracted text.'}, status=status.HTTP_400_BAD_REQUEST)
        pdf_bytes = build_capture_pdf(capture)
        if not pdf_bytes:
            return Response({'detail': 'PDF generation failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        with transaction.atomic():
            pdf_doc = PdfDocument.objects.filter(capture=capture).order_by('-created_at').first()
            created = pdf_doc is None
            if created:
                pdf_doc = PdfDocument(session=capture.session, capture=capture)
            filename = 'capture_%s.pdf' % capture.id
            pdf_doc.file.save(filename, ContentFile(pdf_bytes), save=False)
            pdf_doc.save()
        serializer = PdfDocumentSerializer(pdf_doc, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='ocr')
    def ocr(self, request, pk=None):
        capture = self.get_object()
        capture.status = 'processing'
        capture.error_message = ''
        capture.save(update_fields=['status', 'error_message'])
        source = request.query_params.get('source', None)
        psm = int(request.query_params.get('psm', 6))
        save = request.query_params.get('save', '0') == '1'
        crop = request.query_params.get('crop', '0') == '1'
        try:
            min_conf = int(request.query_params.get('min_conf', 0))
        except (TypeError, ValueError):
            min_conf = 0
        min_conf = max(0, min(90, min_conf))
        filt = request.query_params.get('filter', 'line')
        if filt not in ('word', 'line'):
            return Response({'detail': 'Invalid filter.'}, status=status.HTTP_400_BAD_REQUEST)
        if psm not in (3, 4, 6, 11):
            return Response({'detail': 'Invalid psm.'}, status=status.HTTP_400_BAD_REQUEST)
        if not capture.image:
            capture.status = 'failed'
            capture.error_message = 'Capture has no image.'
            capture.save(update_fields=['status', 'error_message'])
            return Response({'detail': 'Capture has no image.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if source is None:
            source = 'cleaned' if (capture.cleaned_image and os.path.exists(capture.cleaned_image.path)) else 'original'
        if source not in ('original', 'cleaned', 'threshold'):
            return Response({'detail': 'Invalid source.'}, status=status.HTTP_400_BAD_REQUEST)
        cropped = False
        engine = request.query_params.get('engine', 'tesseract')
        if engine not in ('tesseract', 'gemini'):
            return Response({'detail': 'Invalid engine.'}, status=status.HTTP_400_BAD_REQUEST)
        if engine == 'gemini':
            if source == 'threshold':
                return Response({'detail': 'Threshold source is not supported by Gemini OCR.'}, status=status.HTTP_400_BAD_REQUEST)
            if source == 'cleaned':
                if not (capture.cleaned_image and os.path.exists(capture.cleaned_image.path)):
                    capture.status = 'failed'
                    capture.error_message = 'No cleaned image available.'
                    capture.save(update_fields=['status', 'error_message'])
                    return Response({'detail': 'No cleaned image available for this capture.'}, status=status.HTTP_400_BAD_REQUEST)
                image_path = capture.cleaned_image.path
            else:
                if not capture.image or not os.path.exists(capture.image.path):
                    capture.status = 'failed'
                    capture.error_message = 'Capture original image file is missing.'
                    capture.save(update_fields=['status', 'error_message'])
                    return Response({'detail': 'Capture original image file is missing.'}, status=status.HTTP_400_BAD_REQUEST)
                image_path = capture.image.path

            start_gemini = time.time()
            try:
                model_param = request.query_params.get('model')
                kwargs = {'model': model_param} if model_param else {}
                result = run_gemini_ocr(image_path, **kwargs)
            except Exception as exc:
                logger.error('Gemini OCR failed for capture %s: %s', capture.id, exc, exc_info=True)
                capture.status = 'failed'
                capture.ocr_engine = 'gemini'
                capture.error_message = str(exc)[:500]
                capture.save(update_fields=['status', 'ocr_engine', 'error_message'])
                return Response({'detail': f'Gemini OCR failed: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)

            elapsed_ms = int((time.time() - start_gemini) * 1000)
            if save and result['text'].strip():
                capture.extracted_text = result['text']
                capture.save()
            saved = bool(save and result['text'].strip())
            payload = {
                'source': source,
                'psm': None,
                'filter': None,
                'text': result['text'],
                'confidence': None,
                'ms': elapsed_ms,
                'saved': saved,
                'cropped': False,
                'min_conf': min_conf,
                'chars': len(result['text']),
                'words_dropped': 0,
                'lines_kept': 0,
                'lines_dropped': 0,
                'engine': result.get('engine', 'gemini'),
                'model': result.get('model', 'gemini'),
            }
            if not result['text'].strip():
                payload['detail'] = 'No text was detected.'
            capture.status = 'done'
            capture.ocr_engine = result.get('engine', 'gemini')
            from django.utils import timezone
            capture.processed_at = timezone.now()
            capture.error_message = ''
            capture.save()
            return Response(payload, status=status.HTTP_200_OK)
        try:
            if source == 'original':
                img = cv2.imread(capture.image.path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    raise ValueError('Cannot read image')
            elif source == 'cleaned':
                if not (capture.cleaned_image and os.path.exists(capture.cleaned_image.path)):
                    capture.status = 'failed'
                    capture.error_message = 'No cleaned image available.'
                    capture.save(update_fields=['status', 'error_message'])
                    return Response({'detail': 'No cleaned image.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                img = cv2.imread(capture.cleaned_image.path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    raise ValueError('Cannot read image')
            else:
                img = clean_for_ocr(capture.image.path)
            if crop:
                img, box = find_text_region(img)
                cropped = box is not None
                # upscale
                try:
                    h, w = img.shape[:2]
                    if w < 2000:
                        factor = min(3.0, 2000.0 / max(1, w))
                        if factor > 1.0:
                            img = cv2.resize(img, (int(w * factor), int(h * factor)), interpolation=cv2.INTER_CUBIC)
                except Exception:
                    pass
        except Exception as exc:
            capture.status = 'failed'
            capture.ocr_engine = 'tesseract'
            capture.error_message = str(exc)[:500]
            capture.save(update_fields=['status', 'ocr_engine', 'error_message'])
            return Response({'detail': 'Could not prepare image: %s' % exc}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            result = run_ocr(img, psm=psm, min_conf=min_conf, filter=filt)
        except Exception as exc:
            capture.status = 'failed'
            capture.ocr_engine = 'tesseract'
            capture.error_message = str(exc)[:500]
            capture.save(update_fields=['status', 'ocr_engine', 'error_message'])
            return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if save and result['text'].strip():
            capture.extracted_text = result['text']
            capture.save()
        saved = bool(save and result['text'].strip())
        payload = {'source': source, 'psm': psm, 'filter': filt, 'text': result['text'], 'confidence': result['confidence'], 'ms': result['ms'], 'saved': saved, 'cropped': cropped, 'min_conf': min_conf, 'chars': len(result['text']), 'words_dropped': result.get('words_dropped', 0), 'lines_kept': result.get('lines_kept', 0), 'lines_dropped': result.get('lines_dropped', 0)}
        if not result['text'].strip():
            payload['detail'] = 'No text was detected.'
        capture.status = 'done'
        capture.ocr_engine = result.get('engine', 'tesseract')
        from django.utils import timezone
        capture.processed_at = timezone.now()
        capture.error_message = ''
        capture.save()
        return Response(payload, status=status.HTTP_200_OK)

class PdfDocumentViewSet(viewsets.ModelViewSet):
    queryset = PdfDocument.objects.select_related('session', 'session__course').order_by('-created_at')
    serializer_class = PdfDocumentSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['session__title', 'session__course__name']
    filterset_fields = ['session']


# ------------------------------------------------------------ device endpoints


@api_view(['GET'])
@permission_classes([AllowAny])
def device_status(request):
    """Camera polls this to learn whether (and which) session is armed."""
    if not _device_token_ok(request):
        return _device_forbidden()
    state = _get_camera_state()
    session = _armed_session(state)
    if session is None:
        return Response({'armed': False})
    return Response({
        'armed': True,
        'session_id': session.id,
        'session_title': session.title,
        'expires_at': state.expires_at,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def device_capture(request):
    """Receive a JPEG from the camera and attach it to the armed session.

    The session is resolved server-side; the camera never sends a session id.
    """
    if not _device_token_ok(request):
        return _device_forbidden()
    state = _get_camera_state()
    session = _armed_session(state)
    if session is None:
        return Response({'detail': 'No session is armed.'},
                        status=status.HTTP_409_CONFLICT)
    file_obj = request.FILES.get('image')
    ok, error = _validate_jpeg_upload(file_obj)
    if not ok:
        return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
    capture = Capture(session=session, image=file_obj)
    capture.save()
    return Response({
        'capture_id': capture.id,
        'session_id': session.id,
        'status': session.status,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def device_end_session(request):
    """Long-press on the camera ends the armed session (capturing -> processing)."""
    if not _device_token_ok(request):
        return _device_forbidden()
    state = _get_camera_state()
    session = _armed_session(state)
    if session is None:
        return Response({'detail': 'No session is armed.'},
                        status=status.HTTP_409_CONFLICT)
    _clear_camera_state(state)
    if session.status == 'capturing':
        session.status = 'processing'
        session.save(update_fields=['status'])
    return Response({
        'ended': True,
        'session_id': session.id,
        'status': session.status,
        'capture_count': session.captures.count(),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def device_finalize(request):
    """Long-press finalization: generate one cumulative session PDF."""
    if not _device_token_ok(request):
        return _device_forbidden()
    state = _get_camera_state()
    session = _armed_session(state)
    if session is None:
        return Response({'detail': 'No session is armed.'}, status=status.HTTP_409_CONFLICT)
    _clear_camera_state(state)
    if session.captures.count() == 0:
        if session.status == 'capturing':
            session.status = 'processing'
            session.save(update_fields=['status'])
        return Response({'detail': 'No captures to finalize.', 'session_id': session.id, 'status': session.status}, status=status.HTTP_400_BAD_REQUEST)
    locked_session = LessonSession.objects.select_for_update().get(pk=session.pk)
    pdf_bytes = build_session_pdf(locked_session)
    if not pdf_bytes:
        return Response({'detail': 'PDF generation failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    with transaction.atomic():
        pdf_doc = PdfDocument.objects.filter(session=locked_session).order_by('-created_at').first()
        created = pdf_doc is None
        if created:
            pdf_doc = PdfDocument(session=locked_session)
        filename = 'session_%s.pdf' % locked_session.id
        pdf_doc.file.save(filename, ContentFile(pdf_bytes), save=False)
        pdf_doc.save()
        if locked_session.status == 'capturing':
            locked_session.status = 'processing'
            locked_session.save(update_fields=['status'])
    serializer = PdfDocumentSerializer(pdf_doc, context={'request': request})
    return Response({'finalized': True, 'pdf': serializer.data, 'session_id': session.id, 'status': locked_session.status}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


# ---------------------------------------------------------------- teacher auth

def _safe_username(user):
    """Return a display-friendly username, falling back to the account id."""
    username = getattr(user, 'username', '') or ''
    if username:
        return username
    return 'user_%s' % getattr(user, 'pk', '')


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_login(request):
    """Authenticate a teacher and establish a Django session.

    Accepts ``username`` and ``password``. Returns a generic error for any
    invalid credential so callers cannot enumerate registered accounts.

    CSRF is enforced explicitly by ``_enforce_csrf`` because DRF's
    ``@api_view`` wraps this view in ``csrf_exempt`` and DRF's own
    session-auth CSRF check only runs for already-authenticated users.
    """
    _enforce_csrf(request)
    username = (request.data.get('username') or '').strip()
    password = request.data.get('password') or ''

    if not username or not password:
        return Response({'detail': 'Username and password are required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=username, password=password)
    if user is None:
        # Generic message: do not reveal whether the username exists.
        return Response({'detail': 'Invalid credentials.'},
                        status=status.HTTP_401_UNAUTHORIZED)

    django_login(request, user)
    return Response({
        'authenticated': True,
        'user': {
            'id': user.pk,
            'username': _safe_username(user),
            'display_name': _safe_username(user),
        },
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    """End the authenticated teacher's session."""
    django_logout(request)
    return Response({'logged_out': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auth_me(request):
    """Return safe information about the currently authenticated teacher."""
    user = request.user
    return Response({
        'id': user.pk,
        'username': _safe_username(user),
        'display_name': _safe_username(user),
        'is_authenticated': True,
    })


@ensure_csrf_cookie
def csrf_token(request):
    """Issue a CSRF cookie for anonymous browser clients.

    DRF's ``@api_view`` wraps every view in ``csrf_exempt``, so Django's
    middleware never sets the CSRF cookie on DRF routes. This plain Django
    view (not a DRF view) uses ``@ensure_csrf_cookie`` so the cookie is
    written to the response. The browser then sends it back on the login
    POST, where ``_enforce_csrf`` validates it.
    """
    return JsonResponse({'detail': 'CSRF cookie set.'})