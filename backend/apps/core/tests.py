"""
Phase 1B tests: device authentication, session arming, camera capture
endpoint, session ending, and manual-upload regression.

Run with:  python manage.py test apps.core
"""
import io
from datetime import timedelta

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Course, LessonSession, Capture, CameraState

DEVICE_TOKEN = 'test-device-token-123'


def _make_jpeg_bytes(size_kb=20):
    """Smallest valid JPEG-ish payload: SOI marker + padding.

    We do NOT rely on real decoding here for rejection tests; for the
    happy-path test we generate a real JPEG with Pillow if available.
    """
    return b'\xff\xd8' + b'\x00' * (size_kb * 1024)


def _real_jpeg_bytes(width=320, height=240):
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (width, height), color=(255, 255, 255)).save(buf, format='JPEG')
    return buf.getvalue()


class _DeviceTestBase(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client = APIClient()
        self.auth = {'HTTP_AUTHORIZATION': 'Token ' + DEVICE_TOKEN}
        # A teacher account used to exercise authenticated teacher endpoints.
        # Password is irrelevant for the test database; we only need a
        # session-authenticated client for the permission checks introduced
        # in Stage C1.
        User = get_user_model()
        self.teacher = User.objects.create_user(
            username='teacher', password='teacher-pass-123')
        self.client.force_login(self.teacher)
        self.course = Course.objects.create(code='CE101', name='Intro')
        self.session = LessonSession.objects.create(
            course=self.course, title='Lecture 1',
            date=timezone.now().date(), status='draft')
        # Reset the singleton camera state between tests.
        CameraState.objects.all().delete()
        CameraState.objects.create(pk=1)


@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)
class DeviceAuthTests(_DeviceTestBase):
    """Requirement: all camera endpoints require a valid device token."""

    def _endpoints(self):
        return [
            ('get', '/api/device/status/'),
            ('post', '/api/device/capture/'),
            ('post', '/api/device/end-session/'),
        ]

    def test_missing_token_returns_401(self):
        for method, url in self._endpoints():
            res = getattr(self.client, method)(url)
            self.assertEqual(res.status_code, 401, url)

    def test_wrong_token_returns_401(self):
        bad = {'HTTP_AUTHORIZATION': 'Token wrong-token'}
        for method, url in self._endpoints():
            res = getattr(self.client, method)(url, **bad)
            self.assertEqual(res.status_code, 401, url)

    def test_no_token_configured_disables_device_endpoints(self):
        with override_settings(DEVICE_TOKEN=''):
            for method, url in self._endpoints():
                res = getattr(self.client, method)(url, **self.auth)
                self.assertEqual(res.status_code, 401, url)


@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)
class ArmDisarmTests(_DeviceTestBase):
    """Requirement: explicit teacher arming, one armed session at a time."""

    def test_arm_sets_capturing_status(self):
        res = self.client.post('/api/sessions/%d/arm/' % self.session.id)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['armed'], True)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'capturing')

    def test_arm_is_persisted_in_camera_state(self):
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        state = CameraState.objects.get(pk=1)
        self.assertEqual(state.armed_session_id, self.session.id)
        self.assertIsNotNone(state.expires_at)

    def test_arm_finalized_session_conflicts(self):
        self.session.status = 'finalized'
        self.session.save()
        res = self.client.post('/api/sessions/%d/arm/' % self.session.id)
        self.assertEqual(res.status_code, 409)

    def test_second_session_cannot_arm_while_one_is_armed(self):
        other = LessonSession.objects.create(
            course=self.course, title='Lecture 2',
            date=timezone.now().date(), status='draft')
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        res = self.client.post('/api/sessions/%d/arm/' % other.id)
        self.assertEqual(res.status_code, 409)
        state = CameraState.objects.get(pk=1)
        self.assertEqual(state.armed_session_id, self.session.id)

    def test_rearming_same_session_is_allowed(self):
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        res = self.client.post('/api/sessions/%d/arm/' % self.session.id)
        self.assertEqual(res.status_code, 200)

    def test_disarm_sets_processing_and_clears_state(self):
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        res = self.client.post('/api/sessions/%d/disarm/' % self.session.id)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'processing')
        state = CameraState.objects.get(pk=1)
        self.assertIsNone(state.armed_session)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'processing')

    def test_disarm_of_non_armed_session_conflicts(self):
        res = self.client.post('/api/sessions/%d/disarm/' % self.session.id)
        self.assertEqual(res.status_code, 409)


@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)
class DeviceStatusTests(_DeviceTestBase):
    def test_status_idle_when_not_armed(self):
        res = self.client.get('/api/device/status/', **self.auth)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['armed'], False)

    def test_status_reports_armed_session(self):
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        res = self.client.get('/api/device/status/', **self.auth)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['armed'], True)
        self.assertEqual(res.data['session_id'], self.session.id)

    def test_expired_arm_reports_idle(self):
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        state = CameraState.objects.get(pk=1)
        state.expires_at = timezone.now() - timedelta(seconds=1)
        state.save()
        res = self.client.get('/api/device/status/', **self.auth)
        self.assertEqual(res.data['armed'], False)


@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)
class DeviceCaptureTests(_DeviceTestBase):
    """Requirement: server resolves the session; uploads rejected when not armed."""

    def _upload(self, data=None, filename='board.jpg'):
        payload = _real_jpeg_bytes() if data is None else data
        return self.client.post(
            '/api/device/capture/',
            {'image': SimpleUploadedFile(filename, payload, content_type='image/jpeg')},
            **self.auth)

    def test_capture_without_armed_session_conflicts(self):
        res = self._upload()
        self.assertEqual(res.status_code, 409)

    def test_capture_attaches_to_armed_session(self):
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        res = self._upload()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['session_id'], self.session.id)
        capture = Capture.objects.get(pk=res.data['capture_id'])
        self.assertEqual(capture.session_id, self.session.id)

    def test_wrong_session_prevention_camera_sends_no_session_field(self):
        """Even if the camera sends a malicious session id it must be ignored."""
        other = LessonSession.objects.create(
            course=self.course, title='Other',
            date=timezone.now().date(), status='draft')
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        res = self.client.post(
            '/api/device/capture/',
            {
                'session': other.id,  # must be ignored
                'image': SimpleUploadedFile('b.jpg', _real_jpeg_bytes(), content_type='image/jpeg'),
            },
            **self.auth)
        self.assertEqual(res.status_code, 201)
        capture = Capture.objects.get(pk=res.data['capture_id'])
        self.assertEqual(capture.session_id, self.session.id)
        self.assertNotEqual(capture.session_id, other.id)

    def test_rejects_non_jpeg_content_type(self):
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        res = self.client.post(
            '/api/device/capture/',
            {'image': SimpleUploadedFile('b.png', _real_jpeg_bytes(), content_type='image/png')},
            **self.auth)
        self.assertEqual(res.status_code, 400)

    def test_rejects_missing_soiviolation(self):
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        res = self._upload(data=b'G' * (64 * 1024))  # not a JPEG
        self.assertEqual(res.status_code, 400)

    def test_rejects_too_small_file(self):
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        res = self._upload(data=b'\xff\xd8\x00')
        self.assertEqual(res.status_code, 400)

    def test_rejects_undecodable_fake_jpeg(self):
        """JPEG magic bytes but garbage body -> decode check rejects it."""
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        res = self._upload(data=_make_jpeg_bytes(30))
        self.assertEqual(res.status_code, 400)

    def test_rejects_oversized_file(self):
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        big = _real_jpeg_bytes(400, 300)
        with override_settings(DEVICE_UPLOAD_MAX_BYTES=1024):
            res = self.client.post(
                '/api/device/capture/',
                {'image': SimpleUploadedFile('b.jpg', big, content_type='image/jpeg')},
                **self.auth)
        self.assertEqual(res.status_code, 400)


@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)
class DeviceEndSessionTests(_DeviceTestBase):
    def test_end_session_sets_processing_and_clears_state(self):
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        res = self.client.post('/api/device/end-session/', **self.auth)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['ended'], True)
        self.assertEqual(res.data['status'], 'processing')
        state = CameraState.objects.get(pk=1)
        self.assertIsNone(state.armed_session)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'processing')

    def test_end_session_when_idle_conflicts(self):
        res = self.client.post('/api/device/end-session/', **self.auth)
        self.assertEqual(res.status_code, 409)


@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)
class ManualUploadRegressionTests(_DeviceTestBase):
    """Requirement: existing manual uploads keep working untouched."""

    def test_manual_multipart_upload_still_works(self):
        res = self.client.post('/api/captures/', {
            'session': self.session.id,
            'image': SimpleUploadedFile('m.jpg', _real_jpeg_bytes(), content_type='image/jpeg'),
        })
        self.assertEqual(res.status_code, 201)
        capture = Capture.objects.get(pk=res.data['id'])
        self.assertEqual(capture.session_id, self.session.id)

    def test_generate_pdf_still_works_after_device_flow(self):
        self.client.post('/api/sessions/%d/arm/' % self.session.id)
        self.client.post(
            '/api/device/capture/',
            {'image': SimpleUploadedFile('b.jpg', _real_jpeg_bytes(), content_type='image/jpeg')},
            **self.auth)
        self.client.post('/api/device/end-session/', **self.auth)
        res = self.client.post('/api/sessions/%d/generate-pdf/' % self.session.id)
        self.assertEqual(res.status_code, 201)
        self.session.refresh_from_db()
        self.assertNotEqual(self.session.status, 'finalized')  # finalize is explicit PATCH only

@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)
class CaptureStatusTests(_DeviceTestBase):
    """Capture processing status fields."""

    def test_new_capture_is_queued(self):
        res = self.client.post('/api/captures/', {
            'session': self.session.id,
            'image': SimpleUploadedFile('m.jpg', _real_jpeg_bytes(), content_type='image/jpeg'),
        })
        self.assertEqual(res.status_code, 201)
        capture = Capture.objects.get(pk=res.data['id'])
        self.assertEqual(capture.status, 'queued')

    def test_clean_sets_done(self):
        res = self.client.post('/api/captures/', {
            'session': self.session.id,
            'image': SimpleUploadedFile('m.jpg', _real_jpeg_bytes(), content_type='image/jpeg'),
        })
        capture = Capture.objects.get(pk=res.data['id'])
        r = self.client.post('/api/captures/%d/clean/' % capture.id)
        self.assertEqual(r.status_code, 200)
        capture.refresh_from_db()
        self.assertEqual(capture.status, 'done')
        self.assertIsNotNone(capture.processed_at)

    def test_ocr_failure_sets_failed(self):
        from unittest.mock import patch
        res = self.client.post('/api/captures/', {
            'session': self.session.id,
            'image': SimpleUploadedFile('m.jpg', _real_jpeg_bytes(), content_type='image/jpeg'),
        })
        capture = Capture.objects.get(pk=res.data['id'])
        self.client.post('/api/captures/%d/clean/' % capture.id)
        with patch('apps.core.views.run_ocr', side_effect=RuntimeError('boom')):
            r = self.client.post('/api/captures/%d/ocr/?engine=tesseract' % capture.id)
        self.assertEqual(r.status_code, 500)
        capture.refresh_from_db()
        self.assertEqual(capture.status, 'failed')
        self.assertIn('boom', capture.error_message)


class AuthTests(_DeviceTestBase):
    """Phase 1C: teacher login, current-user and logout behavior.

    NOTE: the shared ``self.client`` comes from ``_DeviceTestBase.setUp`` and
    is an ``APIClient()`` with the default ``enforce_csrf_checks=False``.
    These tests therefore exercise the login *flow* but do NOT prove that
    login is CSRF-protected. Login CSRF enforcement is covered separately by
    ``CsrfLoginTests``, which uses ``APIClient(enforce_csrf_checks=True)``.
    """

    def test_login_with_valid_credentials(self):
        self.client.logout()

        response = self.client.post(
            '/api/auth/login/',
            {'username': 'teacher', 'password': 'teacher-pass-123'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['authenticated'])
        self.assertEqual(response.data['user']['username'], 'teacher')

        me_response = self.client.get('/api/auth/me/')
        self.assertEqual(me_response.status_code, 200)
        self.assertTrue(me_response.data['is_authenticated'])
        self.assertEqual(me_response.data['username'], 'teacher')

    def test_login_with_invalid_password(self):
        self.client.logout()

        response = self.client.post(
            '/api/auth/login/',
            {'username': 'teacher', 'password': 'wrong-password'},
            format='json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['detail'], 'Invalid credentials.')

    def test_login_with_missing_credentials(self):
        self.client.logout()

        response = self.client.post(
            '/api/auth/login/',
            {'username': 'teacher'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_me_requires_authentication(self):
        self.client.logout()

        response = self.client.get('/api/auth/me/')

        self.assertEqual(response.status_code, 403)

    def test_logout_ends_teacher_session(self):
        response = self.client.post('/api/auth/logout/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['logged_out'])

        me_response = self.client.get('/api/auth/me/')
        self.assertEqual(me_response.status_code, 403)


class PermissionTests(_DeviceTestBase):
    """Phase 1C: anonymous users cannot access teacher-facing APIs."""

    def setUp(self):
        super().setUp()
        self.client.logout()

    def test_anonymous_cannot_list_courses(self):
        response = self.client.get('/api/courses/')
        self.assertIn(response.status_code, (401, 403))

    def test_anonymous_cannot_list_sessions(self):
        response = self.client.get('/api/sessions/')
        self.assertIn(response.status_code, (401, 403))

    def test_anonymous_cannot_list_captures(self):
        response = self.client.get('/api/captures/')
        self.assertIn(response.status_code, (401, 403))

    def test_anonymous_cannot_list_pdfs(self):
        response = self.client.get('/api/pdfs/')
        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_teacher_can_list_courses(self):
        self.client.force_login(self.teacher)

        response = self.client.get('/api/courses/')

        self.assertEqual(response.status_code, 200)


class DevicePermissionRegressionTests(_DeviceTestBase):
    """Phase 1C: device routes remain independent of teacher login."""

    @override_settings(DEVICE_TOKEN=DEVICE_TOKEN)
    def test_device_status_works_without_teacher_login_with_valid_token(self):
        self.client.logout()

        response = self.client.get(
            '/api/device/status/',
            HTTP_AUTHORIZATION='Token ' + DEVICE_TOKEN,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('armed', response.data)

    @override_settings(DEVICE_TOKEN=DEVICE_TOKEN)
    def test_device_status_still_rejects_missing_token(self):
        self.client.logout()

        response = self.client.get('/api/device/status/')

        self.assertEqual(response.status_code, 401)


class CsrfLoginTests(TestCase):
    """Phase 1C: anonymous login must enforce CSRF before credentials are checked.

    DRF's ``@api_view`` wraps every view in ``csrf_exempt``, so Django's
    middleware-level CSRF check never runs on DRF routes. DRF's own
    ``SessionAuthentication.enforce_csrf`` only runs when a user is already
    authenticated, which leaves the anonymous login endpoint unprotected.
    These tests verify that the login view enforces CSRF itself.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.teacher = User.objects.create_user(
            username='teacher', password='teacher-pass-123')

    def test_login_without_csrf_token_is_rejected_with_403(self):
        client = APIClient(enforce_csrf_checks=True)

        response = client.post('/api/auth/login/',
                               {'username': 'teacher', 'password': 'teacher-pass-123'},
                               format='json')

        self.assertEqual(response.status_code, 403)

    def test_login_with_valid_csrf_token_and_invalid_credentials_returns_401(self):
        client = APIClient(enforce_csrf_checks=True)
        # Seed the CSRF cookie via the dedicated endpoint (DRF views are
        # csrf_exempt, so the cookie is not set automatically).
        seed = client.get('/api/csrf-token/')
        from django.middleware.csrf import get_token
        token = get_token(seed.wsgi_request)

        response = client.post('/api/auth/login/',
                               {'username': 'teacher', 'password': 'wrong'},
                               format='json',
                               HTTP_X_CSRFTOKEN=token)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['detail'], 'Invalid credentials.')

    def test_login_with_valid_csrf_token_and_valid_credentials_succeeds(self):
        client = APIClient(enforce_csrf_checks=True)
        seed = client.get('/api/csrf-token/')
        from django.middleware.csrf import get_token
        token = get_token(seed.wsgi_request)

        response = client.post('/api/auth/login/',
                               {'username': 'teacher', 'password': 'teacher-pass-123'},
                               format='json',
                               HTTP_X_CSRFTOKEN=token)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['authenticated'])
        self.assertEqual(response.data['user']['username'], 'teacher')
