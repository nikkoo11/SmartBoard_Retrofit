warning: in the working copy of 'backend/apps/core/tests.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'backend/apps/core/views.py', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/backend/apps/core/tests.py b/backend/apps/core/tests.py[m
[1mindex 7ce503c..bcfeb7d 100644[m
[1m--- a/backend/apps/core/tests.py[m
[1m+++ b/backend/apps/core/tests.py[m
[36m@@ -1,3 +1,395 @@[m
[31m-from django.test import TestCase[m
[32m+[m[32m"""[m
[32m+[m[32mPhase 1B tests: device authentication, session arming, camera capture[m
[32m+[m[32mendpoint, session ending, and manual-upload regression.[m
 [m
[31m-# Create your tests here.[m
[32m+[m[32mRun with:  python manage.py test apps.core[m
[32m+[m[32m"""[m
[32m+[m[32mimport io[m
[32m+[m[32mfrom datetime import timedelta[m
[32m+[m
[32m+[m[32mfrom django.test import TestCase, override_settings[m
[32m+[m[32mfrom django.core.files.uploadedfile import SimpleUploadedFile[m
[32m+[m[32mfrom django.utils import timezone[m
[32m+[m[32mfrom rest_framework.test import APIClient[m
[32m+[m
[32m+[m[32mfrom apps.core.models import Course, LessonSession, Capture, CameraState[m
[32m+[m
[32m+[m[32mDEVICE_TOKEN = 'test-device-token-123'[m
[32m+[m
[32m+[m
[32m+[m[32mdef _make_jpeg_bytes(size_kb=20):[m
[32m+[m[32m    """Smallest valid JPEG-ish payload: SOI marker + padding.[m
[32m+[m
[32m+[m[32m    We do NOT rely on real decoding here for rejection tests; for the[m
[32m+[m[32m    happy-path test we generate a real JPEG with Pillow if available.[m
[32m+[m[32m    """[m
[32m+[m[32m    return b'\xff\xd8' + b'\x00' * (size_kb * 1024)[m
[32m+[m
[32m+[m
[32m+[m[32mdef _real_jpeg_bytes(width=320, height=240):[m
[32m+[m[32m    from PIL import Image[m
[32m+[m[32m    buf = io.BytesIO()[m
[32m+[m[32m    Image.new('RGB', (width, height), color=(255, 255, 255)).save(buf, format='JPEG')[m
[32m+[m[32m    return buf.getvalue()[m
[32m+[m
[32m+[m
[32m+[m[32mclass _DeviceTestBase(TestCase):[m
[32m+[m[32m    def setUp(self):[m
[32m+[m[32m        from django.contrib.auth import get_user_model[m
[32m+[m[32m        self.client = APIClient()[m
[32m+[m[32m        self.auth = {'HTTP_AUTHORIZATION': 'Token ' + DEVICE_TOKEN}[m
[32m+[m[32m        # A teacher account used to exercise authenticated teacher endpoints.[m
[32m+[m[32m        # Password is irrelevant for the test database; we only need a[m
[32m+[m[32m        # session-authenticated client for the permission checks introduced[m
[32m+[m[32m        # in Stage C1.[m
[32m+[m[32m        User = get_user_model()[m
[32m+[m[32m        self.teacher = User.objects.create_user([m
[32m+[m[32m            username='teacher', password='teacher-pass-123')[m
[32m+[m[32m        self.client.force_login(self.teacher)[m
[32m+[m[32m        self.course = Course.objects.create(code='CE101', name='Intro')[m
[32m+[m[32m        self.session = LessonSession.objects.create([m
[32m+[m[32m            course=self.course, title='Lecture 1',[m
[32m+[m[32m            date=timezone.now().date(), status='draft')[m
[32m+[m[32m        # Reset the singleton camera state between tests.[m
[32m+[m[32m        CameraState.objects.all().delete()[m
[32m+[m[32m        CameraState.objects.create(pk=1)[m
[32m+[m
[32m+[m
[32m+[m[32m@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)[m
[32m+[m[32mclass DeviceAuthTests(_DeviceTestBase):[m
[32m+[m[32m    """Requirement: all camera endpoints require a valid device token."""[m
[32m+[m
[32m+[m[32m    def _endpoints(self):[m
[32m+[m[32m        return [[m
[32m+[m[32m            ('get', '/api/device/status/'),[m
[32m+[m[32m            ('post', '/api/device/capture/'),[m
[32m+[m[32m            ('post', '/api/device/end-session/'),[m
[32m+[m[32m        ][m
[32m+[m
[32m+[m[32m    def test_missing_token_returns_401(self):[m
[32m+[m[32m        for method, url in self._endpoints():[m
[32m+[m[32m            res = getattr(self.client, method)(url)[m
[32m+[m[32m            self.assertEqual(res.status_code, 401, url)[m
[32m+[m
[32m+[m[32m    def test_wrong_token_returns_401(self):[m
[32m+[m[32m        bad = {'HTTP_AUTHORIZATION': 'Token wrong-token'}[m
[32m+[m[32m        for method, url in self._endpoints():[m
[32m+[m[32m            res = getattr(self.client, method)(url, **bad)[m
[32m+[m[32m            self.assertEqual(res.status_code, 401, url)[m
[32m+[m
[32m+[m[32m    def test_no_token_configured_disables_device_endpoints(self):[m
[32m+[m[32m        with override_settings(DEVICE_TOKEN=''):[m
[32m+[m[32m            for method, url in self._endpoints():[m
[32m+[m[32m                res = getattr(self.client, method)(url, **self.auth)[m
[32m+[m[32m                self.assertEqual(res.status_code, 401, url)[m
[32m+[m
[32m+[m
[32m+[m[32m@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)[m
[32m+[m[32mclass ArmDisarmTests(_DeviceTestBase):[m
[32m+[m[32m    """Requirement: explicit teacher arming, one armed session at a time."""[m
[32m+[m
[32m+[m[32m    def test_arm_sets_capturing_status(self):[m
[32m+[m[32m        res = self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        self.assertEqual(res.status_code, 200)[m
[32m+[m[32m        self.assertEqual(res.data['armed'], True)[m
[32m+[m[32m        self.session.refresh_from_db()[m
[32m+[m[32m        self.assertEqual(self.session.status, 'capturing')[m
[32m+[m
[32m+[m[32m    def test_arm_is_persisted_in_camera_state(self):[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        state = CameraState.objects.get(pk=1)[m
[32m+[m[32m        self.assertEqual(state.armed_session_id, self.session.id)[m
[32m+[m[32m        self.assertIsNotNone(state.expires_at)[m
[32m+[m
[32m+[m[32m    def test_arm_finalized_session_conflicts(self):[m
[32m+[m[32m        self.session.status = 'finalized'[m
[32m+[m[32m        self.session.save()[m
[32m+[m[32m        res = self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        self.assertEqual(res.status_code, 409)[m
[32m+[m
[32m+[m[32m    def test_second_session_cannot_arm_while_one_is_armed(self):[m
[32m+[m[32m        other = LessonSession.objects.create([m
[32m+[m[32m            course=self.course, title='Lecture 2',[m
[32m+[m[32m            date=timezone.now().date(), status='draft')[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        res = self.client.post('/api/sessions/%d/arm/' % other.id)[m
[32m+[m[32m        self.assertEqual(res.status_code, 409)[m
[32m+[m[32m        state = CameraState.objects.get(pk=1)[m
[32m+[m[32m        self.assertEqual(state.armed_session_id, self.session.id)[m
[32m+[m
[32m+[m[32m    def test_rearming_same_session_is_allowed(self):[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        res = self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        self.assertEqual(res.status_code, 200)[m
[32m+[m
[32m+[m[32m    def test_disarm_sets_processing_and_clears_state(self):[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        res = self.client.post('/api/sessions/%d/disarm/' % self.session.id)[m
[32m+[m[32m        self.assertEqual(res.status_code, 200)[m
[32m+[m[32m        self.assertEqual(res.data['status'], 'processing')[m
[32m+[m[32m        state = CameraState.objects.get(pk=1)[m
[32m+[m[32m        self.assertIsNone(state.armed_session)[m
[32m+[m[32m        self.session.refresh_from_db()[m
[32m+[m[32m        self.assertEqual(self.session.status, 'processing')[m
[32m+[m
[32m+[m[32m    def test_disarm_of_non_armed_session_conflicts(self):[m
[32m+[m[32m        res = self.client.post('/api/sessions/%d/disarm/' % self.session.id)[m
[32m+[m[32m        self.assertEqual(res.status_code, 409)[m
[32m+[m
[32m+[m
[32m+[m[32m@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)[m
[32m+[m[32mclass DeviceStatusTests(_DeviceTestBase):[m
[32m+[m[32m    def test_status_idle_when_not_armed(self):[m
[32m+[m[32m        res = self.client.get('/api/device/status/', **self.auth)[m
[32m+[m[32m        self.assertEqual(res.status_code, 200)[m
[32m+[m[32m        self.assertEqual(res.data['armed'], False)[m
[32m+[m
[32m+[m[32m    def test_status_reports_armed_session(self):[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        res = self.client.get('/api/device/status/', **self.auth)[m
[32m+[m[32m        self.assertEqual(res.status_code, 200)[m
[32m+[m[32m        self.assertEqual(res.data['armed'], True)[m
[32m+[m[32m        self.assertEqual(res.data['session_id'], self.session.id)[m
[32m+[m
[32m+[m[32m    def test_expired_arm_reports_idle(self):[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        state = CameraState.objects.get(pk=1)[m
[32m+[m[32m        state.expires_at = timezone.now() - timedelta(seconds=1)[m
[32m+[m[32m        state.save()[m
[32m+[m[32m        res = self.client.get('/api/device/status/', **self.auth)[m
[32m+[m[32m        self.assertEqual(res.data['armed'], False)[m
[32m+[m
[32m+[m
[32m+[m[32m@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)[m
[32m+[m[32mclass DeviceCaptureTests(_DeviceTestBase):[m
[32m+[m[32m    """Requirement: server resolves the session; uploads rejected when not armed."""[m
[32m+[m
[32m+[m[32m    def _upload(self, data=None, filename='board.jpg'):[m
[32m+[m[32m        payload = _real_jpeg_bytes() if data is None else data[m
[32m+[m[32m        return self.client.post([m
[32m+[m[32m            '/api/device/capture/',[m
[32m+[m[32m            {'image': SimpleUploadedFile(filename, payload, content_type='image/jpeg')},[m
[32m+[m[32m            **self.auth)[m
[32m+[m
[32m+[m[32m    def test_capture_without_armed_session_conflicts(self):[m
[32m+[m[32m        res = self._upload()[m
[32m+[m[32m        self.assertEqual(res.status_code, 409)[m
[32m+[m
[32m+[m[32m    def test_capture_attaches_to_armed_session(self):[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        res = self._upload()[m
[32m+[m[32m        self.assertEqual(res.status_code, 201)[m
[32m+[m[32m        self.assertEqual(res.data['session_id'], self.session.id)[m
[32m+[m[32m        capture = Capture.objects.get(pk=res.data['capture_id'])[m
[32m+[m[32m        self.assertEqual(capture.session_id, self.session.id)[m
[32m+[m
[32m+[m[32m    def test_wrong_session_prevention_camera_sends_no_session_field(self):[m
[32m+[m[32m        """Even if the camera sends a malicious session id it must be ignored."""[m
[32m+[m[32m        other = LessonSession.objects.create([m
[32m+[m[32m            course=self.course, title='Other',[m
[32m+[m[32m            date=timezone.now().date(), status='draft')[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        res = self.client.post([m
[32m+[m[32m            '/api/device/capture/',[m
[32m+[m[32m            {[m
[32m+[m[32m                'session': other.id,  # must be ignored[m
[32m+[m[32m                'image': SimpleUploadedFile('b.jpg', _real_jpeg_bytes(), content_type='image/jpeg'),[m
[32m+[m[32m            },[m
[32m+[m[32m            **self.auth)[m
[32m+[m[32m        self.assertEqual(res.status_code, 201)[m
[32m+[m[32m        capture = Capture.objects.get(pk=res.data['capture_id'])[m
[32m+[m[32m        self.assertEqual(capture.session_id, self.session.id)[m
[32m+[m[32m        self.assertNotEqual(capture.session_id, other.id)[m
[32m+[m
[32m+[m[32m    def test_rejects_non_jpeg_content_type(self):[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        res = self.client.post([m
[32m+[m[32m            '/api/device/capture/',[m
[32m+[m[32m            {'image': SimpleUploadedFile('b.png', _real_jpeg_bytes(), content_type='image/png')},[m
[32m+[m[32m            **self.auth)[m
[32m+[m[32m        self.assertEqual(res.status_code, 400)[m
[32m+[m
[32m+[m[32m    def test_rejects_missing_soiviolation(self):[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        res = self._upload(data=b'G' * (64 * 1024))  # not a JPEG[m
[32m+[m[32m        self.assertEqual(res.status_code, 400)[m
[32m+[m
[32m+[m[32m    def test_rejects_too_small_file(self):[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        res = self._upload(data=b'\xff\xd8\x00')[m
[32m+[m[32m        self.assertEqual(res.status_code, 400)[m
[32m+[m
[32m+[m[32m    def test_rejects_undecodable_fake_jpeg(self):[m
[32m+[m[32m        """JPEG magic bytes but garbage body -> decode check rejects it."""[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        res = self._upload(data=_make_jpeg_bytes(30))[m
[32m+[m[32m        self.assertEqual(res.status_code, 400)[m
[32m+[m
[32m+[m[32m    def test_rejects_oversized_file(self):[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        big = _real_jpeg_bytes(400, 300)[m
[32m+[m[32m        with override_settings(DEVICE_UPLOAD_MAX_BYTES=1024):[m
[32m+[m[32m            res = self.client.post([m
[32m+[m[32m                '/api/device/capture/',[m
[32m+[m[32m                {'image': SimpleUploadedFile('b.jpg', big, content_type='image/jpeg')},[m
[32m+[m[32m                **self.auth)[m
[32m+[m[32m        self.assertEqual(res.status_code, 400)[m
[32m+[m
[32m+[m
[32m+[m[32m@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)[m
[32m+[m[32mclass DeviceEndSessionTests(_DeviceTestBase):[m
[32m+[m[32m    def test_end_session_sets_processing_and_clears_state(self):[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        res = self.client.post('/api/device/end-session/', **self.auth)[m
[32m+[m[32m        self.assertEqual(res.status_code, 200)[m
[32m+[m[32m        self.assertEqual(res.data['ended'], True)[m
[32m+[m[32m        self.assertEqual(res.data['status'], 'processing')[m
[32m+[m[32m        state = CameraState.objects.get(pk=1)[m
[32m+[m[32m        self.assertIsNone(state.armed_session)[m
[32m+[m[32m        self.session.refresh_from_db()[m
[32m+[m[32m        self.assertEqual(self.session.status, 'processing')[m
[32m+[m
[32m+[m[32m    def test_end_session_when_idle_conflicts(self):[m
[32m+[m[32m        res = self.client.post('/api/device/end-session/', **self.auth)[m
[32m+[m[32m        self.assertEqual(res.status_code, 409)[m
[32m+[m
[32m+[m
[32m+[m[32m@override_settings(DEVICE_TOKEN=DEVICE_TOKEN)[m
[32m+[m[32mclass ManualUploadRegressionTests(_DeviceTestBase):[m
[32m+[m[32m    """Requirement: existing manual uploads keep working untouched."""[m
[32m+[m
[32m+[m[32m    def test_manual_multipart_upload_still_works(self):[m
[32m+[m[32m        res = self.client.post('/api/captures/', {[m
[32m+[m[32m            'session': self.session.id,[m
[32m+[m[32m            'image': SimpleUploadedFile('m.jpg', _real_jpeg_bytes(), content_type='image/jpeg'),[m
[32m+[m[32m        })[m
[32m+[m[32m        self.assertEqual(res.status_code, 201)[m
[32m+[m[32m        capture = Capture.objects.get(pk=res.data['id'])[m
[32m+[m[32m        self.assertEqual(capture.session_id, self.session.id)[m
[32m+[m
[32m+[m[32m    def test_generate_pdf_still_works_after_device_flow(self):[m
[32m+[m[32m        self.client.post('/api/sessions/%d/arm/' % self.session.id)[m
[32m+[m[32m        self.client.post([m
[32m+[m[32m            '/api/device/capture/',[m
[32m+[m[32m            {'image': SimpleUploadedFile('b.jpg', _real_jpeg_bytes(), content_type='image/jpeg')},[m
[32m+[m[32m            **self.auth)[m
[32m+[m[32m        self.client.post('/api/device/end-session/', **self.auth)[m
[32m+[m[32m        res = self.client.post('/api/sessions/%d/generate-pdf/' % self.session.id)[m
[32m+[m[32m        self.assertEqual(res.status_code, 201)[m
[32m+[m[32m        self.session.refresh_from_db()[m
[32m+[m[32m        self.assertNotEqual(self.session.status, 'finalized')  # finalize is explicit PATCH only[m
[32m+[m
[32m+[m[32mclass AuthTests(_DeviceTestBase):[m
[32m+[m[32m    """Phase 1C: teacher login, current-user and logout behavior."""[m
[32m+[m
[32m+[m[32m    def test_login_with_valid_credentials(self):[m
[32m+[m[32m        self.client.logout()[m
[32m+[m
[32m+[m[32m        response = self.client.post([m
[32m+[m[32m            '/api/auth/login/',[m
[32m+[m[32m            {'username': 'teacher', 'password': 'teacher-pass-123'},[m
[32m+[m[32m            format='json',[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m        self.assertEqual(response.status_code, 200)[m
[32m+[m[32m        self.assertTrue(response.data['authenticated'])[m
[32m+[m[32m        self.assertEqual(response.data['user']['username'], 'teacher')[m
[32m+[m
[32m+[m[32m        me_response = self.client.get('/api/auth/me/')[m
[32m+[m[32m        self.assertEqual(me_response.status_code, 200)[m
[32m+[m[32m        self.assertTrue(me_response.data['is_authenticated'])[m
[32m+[m[32m        self.assertEqual(me_response.data['username'], 'teacher')[m
[32m+[m
[32m+[m[32m    def test_login_with_invalid_password(self):[m
[32m+[m[32m        self.client.logout()[m
[32m+[m
[32m+[m[32m        response = self.client.post([m
[32m+[m[32m            '/api/auth/login/',[m
[32m+[m[32m            {'username': 'teacher', 'password': 'wrong-password'},[m
[32m+[m[32m            format='json',[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m        self.assertEqual(response.status_code, 401)[m
[32m+[m[32m        self.assertEqual(response.data['detail'], 'Invalid credentials.')[m
[32m+[m
[32m+[m[32m    def test_login_with_missing_credentials(self):[m
[32m+[m[32m        self.client.logout()[m
[32m+[m
[32m+[m[32m        response = self.client.post([m
[32m+[m[32m            '/api/auth/login/',[m
[32m+[m[32m            {'username': 'teacher'},[m
[32m+[m[32m            format='json',[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m        self.assertEqual(response.status_code, 400)[m
[32m+[m
[32m+[m[32m    def test_me_requires_authentication(self):[m
[32m+[m[32m        self.client.logout()[m
[32m+[m
[32m+[m[32m        response = self.client.get('/api/auth/me/')[m
[32m+[m
[32m+[m[32m        self.assertEqual(response.status_code, 403)[m
[32m+[m
[32m+[m[32m    def test_logout_ends_teacher_session(self):[m
[32m+[m[32m        response = self.client.post('/api/auth/logout/')[m
[32m+[m
[32m+[m[32m        self.assertEqual(response.status_code, 200)[m
[32m+[m[32m        self.assertTrue(response.data['logged_out'])[m
[32m+[m
[32m+[m[32m        me_response = self.client.get('/api/auth/me/')[m
[32m+[m[32m        self.assertEqual(me_response.status_code, 403)[m
[32m+[m
[32m+[m
[32m+[m[32mclass PermissionTests(_DeviceTestBase):[m
[32m+[m[32m    """Phase 1C: anonymous users cannot access teacher-facing APIs."""[m
[32m+[m
[32m+[m[32m    def setUp(self):[m
[32m+[m[32m        super().setUp()[m
[32m+[m[32m        self.client.logout()[m
[32m+[m
[32m+[m[32m    def test_anonymous_cannot_list_courses(self):[m
[32m+[m[32m        response = self.client.get('/api/courses/')[m
[32m+[m[32m        self.assertIn(response.status_code, (401, 403))[m
[32m+[m
[32m+[m[32m    def test_anonymous_cannot_list_sessions(self):[m
[32m+[m[32m        response = self.client.get('/api/sessions/')[m
[32m+[m[32m        self.assertIn(response.status_code, (401, 403))[m
[32m+[m
[32m+[m[32m    def test_anonymous_cannot_list_captures(self):[m
[32m+[m[32m        response = self.client.get('/api/captures/')[m
[32m+[m[32m        self.assertIn(response.status_code, (401, 403))[m
[32m+[m
[32m+[m[32m    def test_anonymous_cannot_list_pdfs(self):[m
[32m+[m[32m        response = self.client.get('/api/pdfs/')[m
[32m+[m[32m        self.assertIn(response.status_code, (401, 403))[m
[32m+[m
[32m+[m[32m    def test_authenticated_teacher_can_list_courses(self):[m
[32m+[m[32m        self.client.force_login(self.teacher)[m
[32m+[m
[32m+[m[32m        response = self.client.get('/api/courses/')[m
[32m+[m
[32m+[m[32m        self.assertEqual(response.status_code, 200)[m
[32m+[m
[32m+[m
[32m+[m[32mclass DevicePermissionRegressionTests(_DeviceTestBase):[m
[32m+[m[32m    """Phase 1C: device routes remain independent of teacher login."""[m
[32m+[m
[32m+[m[32m    @override_settings(DEVICE_TOKEN=DEVICE_TOKEN)[m
[32m+[m[32m    def test_device_status_works_without_teacher_login_with_valid_token(self):[m
[32m+[m[32m        self.client.logout()[m
[32m+[m
[32m+[m[32m        response = self.client.get([m
[32m+[m[32m            '/api/device/status/',[m
[32m+[m[32m            HTTP_AUTHORIZATION='Token ' + DEVICE_TOKEN,[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m        self.assertEqual(response.status_code, 200)[m
[32m+[m[32m        self.assertIn('armed', response.data)[m
[32m+[m
[32m+[m[32m    @override_settings(DEVICE_TOKEN=DEVICE_TOKEN)[m
[32m+[m[32m    def test_device_status_still_rejects_missing_token(self):[m
[32m+[m[32m        self.client.logout()[m
[32m+[m
[32m+[m[32m        response = self.client.get('/api/device/status/')[m
[32m+[m
[32m+[m[32m        self.assertEqual(response.status_code, 401)[m
[1mdiff --git a/backend/apps/core/urls.py b/backend/apps/core/urls.py[m
[1mindex 306d496..28f5abd 100644[m
[1m--- a/backend/apps/core/urls.py[m
[1m+++ b/backend/apps/core/urls.py[m
[36m@@ -1,6 +1,8 @@[m
 ﻿from rest_framework.routers import DefaultRouter[m
 from django.urls import path, include[m
[31m-from .views import CourseViewSet, LessonSessionViewSet, CaptureViewSet, PdfDocumentViewSet[m
[32m+[m[32mfrom .views import (CourseViewSet, LessonSessionViewSet, CaptureViewSet, PdfDocumentViewSet,[m
[32m+[m[32m                    device_status, device_capture, device_end_session,[m
[32m+[m[32m                    auth_login, auth_logout, auth_me)[m
 [m
 router = DefaultRouter()[m
 router.register(r'courses', CourseViewSet)[m
[36m@@ -10,5 +12,11 @@[m [mrouter.register(r'pdfs', PdfDocumentViewSet)[m
 [m
 urlpatterns = [[m
     path('', include(router.urls)),[m
[32m+[m[32m    path('device/status/', device_status, name='device-status'),[m
[32m+[m[32m    path('device/capture/', device_capture, name='device-capture'),[m
[32m+[m[32m    path('device/end-session/', device_end_session, name='device-end-session'),[m
[32m+[m[32m    path('auth/login/', auth_login, name='auth-login'),[m
[32m+[m[32m    path('auth/logout/', auth_logout, name='auth-logout'),[m
[32m+[m[32m    path('auth/me/', auth_me, name='auth-me'),[m
 ][m
 [m
[1mdiff --git a/backend/apps/core/views.py b/backend/apps/core/views.py[m
[1mindex b91ea1c..5149d7b 100644[m
[1m--- a/backend/apps/core/views.py[m
[1m+++ b/backend/apps/core/views.py[m
[36m@@ -1,14 +1,20 @@[m
 from rest_framework import viewsets, filters, status[m
[31m-from rest_framework.decorators import action[m
[32m+[m[32mfrom rest_framework.decorators import action, api_view, permission_classes, parser_classes[m
 from rest_framework.response import Response[m
[32m+[m[32mfrom rest_framework.permissions import AllowAny, IsAuthenticated[m
[32m+[m[32mfrom rest_framework.parsers import MultiPartParser, FormParser[m
 from django_filters.rest_framework import DjangoFilterBackend[m
 from django.core.files.base import ContentFile[m
 from django.conf import settings[m
[32m+[m[32mfrom django.utils import timezone[m
[32m+[m[32mfrom django.contrib.auth import authenticate, login as django_login, logout as django_logout[m
[32m+[m[32mfrom django.contrib.auth.decorators import login_required[m
[32m+[m[32mfrom datetime import timedelta[m
 import logging[m
 import os[m
 import time[m
 import cv2[m
[31m-from .models import Course, LessonSession, Capture, PdfDocument[m
[32m+[m[32mfrom .models import Course, LessonSession, Capture, PdfDocument, CameraState[m
 from .serializers import CourseSerializer, LessonSessionSerializer, CaptureSerializer, PdfDocumentSerializer[m
 from .pdf_service import build_session_pdf[m
 from .ocr_service import run_ocr, run_gemini_ocr[m
[36m@@ -17,6 +23,72 @@[m [mfrom .cleaning_service import clean_for_ocr, clean_board_image, find_text_region[m
 logger = logging.getLogger(__name__)[m
 [m
 [m
[32m+[m[32m# ---------------------------------------------------------------- device auth[m
[32m+[m
[32m+[m
[32m+[m[32mdef _device_token_ok(request):[m
[32m+[m[32m    """Constant-time check of the shared device token from the Authorization header."""[m
[32m+[m[32m    import hmac[m
[32m+[m[32m    expected = getattr(settings, 'DEVICE_TOKEN', '')[m
[32m+[m[32m    if not expected:[m
[32m+[m[32m        return False  # no token configured -> device endpoints disabled[m
[32m+[m[32m    header = request.META.get('HTTP_AUTHORIZATION', '')[m
[32m+[m[32m    supplied = header[6:] if header.startswith('Token ') else header[m
[32m+[m[32m    return bool(supplied) and hmac.compare_digest(supplied, expected)[m
[32m+[m
[32m+[m
[32m+[m[32mdef _device_forbidden():[m
[32m+[m[32m    return Response({'detail': 'Invalid or missing device token.'},[m
[32m+[m[32m                    status=status.HTTP_401_UNAUTHORIZED)[m
[32m+[m
[32m+[m
[32m+[m[32mdef _get_camera_state():[m
[32m+[m[32m    state, _ = CameraState.objects.get_or_create(pk=1)[m
[32m+[m[32m    return state[m
[32m+[m
[32m+[m
[32m+[m[32mdef _armed_session(state, now=None):[m
[32m+[m[32m    """Return the armed LessonSession if the state is valid and unexpired, else None."""[m
[32m+[m[32m    if state.armed_session_id is None:[m
[32m+[m[32m        return None[m
[32m+[m[32m    now = now or timezone.now()[m
[32m+[m[32m    if state.expires_at is not None and state.expires_at <= now:[m
[32m+[m[32m        return None[m
[32m+[m[32m    return state.armed_session[m
[32m+[m
[32m+[m
[32m+[m[32mdef _clear_camera_state(state, save=True):[m
[32m+[m[32m    state.armed_session = None[m
[32m+[m[32m    state.armed_at = None[m
[32m+[m[32m    state.expires_at = None[m
[32m+[m[32m    if save:[m
[32m+[m[32m        state.save()[m
[32m+[m
[32m+[m
[32m+[m[32mdef _validate_jpeg_upload(file_obj):[m
[32m+[m[32m    """Validate an uploaded camera image. Returns (ok, error_detail)."""[m
[32m+[m[32m    if file_obj is None:[m
[32m+[m[32m        return False, 'No image provided.'[m
[32m+[m[32m    max_bytes = getattr(settings, 'DEVICE_UPLOAD_MAX_BYTES', 10 * 1024 * 1024)[m
[32m+[m[32m    if file_obj.size > max_bytes:[m
[32m+[m[32m        return False, 'File too large.'[m
[32m+[m[32m    if file_obj.size < 1024:[m
[32m+[m[32m        return False, 'File too small to be a valid image.'[m
[32m+[m[32m    content_type = getattr(file_obj, 'content_type', '') or ''[m
[32m+[m[32m    if content_type not in ('image/jpeg', 'image/jpg'):[m
[32m+[m[32m        return False, 'Only JPEG images are accepted.'[m
[32m+[m[32m    data = file_obj.read()[m
[32m+[m[32m    file_obj.seek(0)[m
[32m+[m[32m    if not data.startswith(b'\xff\xd8'):[m
[32m+[m[32m        return False, 'File is not a valid JPEG.'[m
[32m+[m[32m    import numpy as np[m
[32m+[m[32m    arr = np.frombuffer(data, dtype=np.uint8)[m
[32m+[m[32m    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)[m
[32m+[m[32m    if img is None:[m
[32m+[m[32m        return False, 'Image could not be decoded.'[m
[32m+[m[32m    return True, None[m
[32m+[m
[32m+[m
 class CourseViewSet(viewsets.ModelViewSet):[m
     queryset = Course.objects.all().order_by('code')[m
     serializer_class = CourseSerializer[m
[36m@@ -44,6 +116,53 @@[m [mclass LessonSessionViewSet(viewsets.ModelViewSet):[m
         serializer = PdfDocumentSerializer(pdf_doc, context={'request': request})[m
         return Response(serializer.data, status=status.HTTP_201_CREATED)[m
 [m
[32m+[m[32m    @action(detail=True, methods=['post'], url_path='arm')[m
[32m+[m[32m    def arm(self, request, pk=None):[m
[32m+[m[32m        """Explicitly arm this session for the camera."""[m
[32m+[m[32m        session = self.get_object()[m
[32m+[m[32m        if session.status == 'finalized':[m
[32m+[m[32m            return Response({'detail': 'Cannot arm a finalized session.'},[m
[32m+[m[32m                            status=status.HTTP_409_CONFLICT)[m
[32m+[m[32m        state = _get_camera_state()[m
[32m+[m[32m        current = _armed_session(state)[m
[32m+[m[32m        if current is not None and current.pk != session.pk:[m
[32m+[m[32m            return Response([m
[32m+[m[32m                {'detail': 'Another session (%s) is currently armed. Disarm it first.'[m
[32m+[m[32m                    % current.pk},[m
[32m+[m[32m                status=status.HTTP_409_CONFLICT)[m
[32m+[m[32m        minutes = getattr(settings, 'DEVICE_SESSION_TIMEOUT_MINUTES', 120)[m
[32m+[m[32m        try:[m
[32m+[m[32m            minutes = int(request.data.get('timeout_minutes', minutes))[m
[32m+[m[32m        except (TypeError, ValueError):[m
[32m+[m[32m            minutes = getattr(settings, 'DEVICE_SESSION_TIMEOUT_MINUTES', 120)[m
[32m+[m[32m        minutes = max(1, min(minutes, 24 * 60))[m
[32m+[m[32m        now = timezone.now()[m
[32m+[m[32m        state.armed_session = session[m
[32m+[m[32m        state.armed_at = now[m
[32m+[m[32m        state.expires_at = now + timedelta(minutes=minutes)[m
[32m+[m[32m        state.save()[m
[32m+[m[32m        if session.status != 'capturing':[m
[32m+[m[32m            session.status = 'capturing'[m
[32m+[m[32m            session.save(update_fields=['status'])[m
[32m+[m[32m        return Response({[m
[32m+[m[32m            'id': session.id, 'status': session.status, 'armed': True,[m
[32m+[m[32m            'expires_at': state.expires_at,[m
[32m+[m[32m        })[m
[32m+[m
[32m+[m[32m    @action(detail=True, methods=['post'], url_path='disarm')[m
[32m+[m[32m    def disarm(self, request, pk=None):[m
[32m+[m[32m        """Safely disarm this session (teacher-initiated)."""[m
[32m+[m[32m        session = self.get_object()[m
[32m+[m[32m        state = _get_camera_state()[m
[32m+[m[32m        if state.armed_session_id != session.pk:[m
[32m+[m[32m            return Response({'detail': 'This session is not the armed session.'},[m
[32m+[m[32m                            status=status.HTTP_409_CONFLICT)[m
[32m+[m[32m        _clear_camera_state(state)[m
[32m+[m[32m        if session.status == 'capturing':[m
[32m+[m[32m            session.status = 'processing'[m
[32m+[m[32m            session.save(update_fields=['status'])[m
[32m+[m[32m        return Response({'id': session.id, 'status': session.status, 'armed': False})[m
[32m+[m
 [m
 class CaptureViewSet(viewsets.ModelViewSet):[m
     queryset = Capture.objects.select_related('session').order_by('-created_at')[m
[36m@@ -205,4 +324,140 @@[m [mclass PdfDocumentViewSet(viewsets.ModelViewSet):[m
     serializer_class = PdfDocumentSerializer[m
     filter_backends = [filters.SearchFilter, DjangoFilterBackend][m
     search_fields = ['session__title', 'session__course__name'][m
[31m-    filterset_fields = ['session'][m
\ No newline at end of file[m
[32m+[m[32m    filterset_fields = ['session'][m
[32m+[m
[32m+[m
[32m+[m[32m# ------------------------------------------------------------ device endpoints[m
[32m+[m
[32m+[m
[32m+[m[32m@api_view(['GET'])[m
[32m+[m[32m@permission_classes([AllowAny])[m
[32m+[m[32mdef device_status(request):[m
[32m+[m[32m    """Camera polls this to learn whether (and which) session is armed."""[m
[32m+[m[32m    if not _device_token_ok(request):[m
[32m+[m[32m        return _device_forbidden()[m
[32m+[m[32m    state = _get_camera_state()[m
[32m+[m[32m    session = _armed_session(state)[m
[32m+[m[32m    if session is None:[m
[32m+[m[32m        return Response({'armed': False})[m
[32m+[m[32m    return Response({[m
[32m+[m[32m        'armed': True,[m
[32m+[m[32m        'session_id': session.id,[m
[32m+[m[32m        'session_title': session.title,[m
[32m+[m[32m        'expires_at': state.expires_at,[m
[32m+[m[32m    })[m
[32m+[m
[32m+[m
[32m+[m[32m@api_view(['POST'])[m
[32m+[m[32m@permission_classes([AllowAny])[m
[32m+[m[32m@parser_classes([MultiPartParser, FormParser])[m
[32m+[m[32mdef device_capture(request):[m
[32m+[m[32m    """Receive a JPEG from the camera and attach it to the armed session.[m
[32m+[m
[32m+[m[32m    The session is resolved server-side; the camera never sends a session id.[m
[32m+[m[32m    """[m
[32m+[m[32m    if not _device_token_ok(request):[m
[32m+[m[32m        return _device_forbidden()[m
[32m+[m[32m    state = _get_camera_state()[m
[32m+[m[32m    session = _armed_session(state)[m
[32m+[m[32m    if session is None:[m
[32m+[m[32m        return Response({'detail': 'No session is armed.'},[m
[32m+[m[32m                        status=status.HTTP_409_CONFLICT)[m
[32m+[m[32m    file_obj = request.FILES.get('image')[m
[32m+[m[32m    ok, error = _validate_jpeg_upload(file_obj)[m
[32m+[m[32m    if not ok:[m
[32m+[m[32m        return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)[m
[32m+[m[32m    capture = Capture(session=session, image=file_obj)[m
[32m+[m[32m    capture.save()[m
[32m+[m[32m    return Response({[m
[32m+[m[32m        'capture_id': capture.id,[m
[32m+[m[32m        'session_id': session.id,[m
[32m+[m[32m        'status': session.status,[m
[32m+[m[32m    }, status=status.HTTP_201_CREATED)[m
[32m+[m
[32m+[m
[32m+[m[32m@api_view(['POST'])[m
[32m+[m[32m@permission_classes([AllowAny])[m
[32m+[m[32mdef device_end_session(request):[m
[32m+[m[32m    """Long-press on the camera ends the armed session (capturing -> processing)."""[m
[32m+[m[32m    if not _device_token_ok(request):[m
[32m+[m[32m        return _device_forbidden()[m
[32m+[m[32m    state = _get_camera_state()[m
[32m+[m[32m    session = _armed_session(state)[m
[32m+[m[32m    if session is None:[m
[32m+[m[32m        return Response({'detail': 'No session is armed.'},[m
[32m+[m[32m                        status=status.HTTP_409_CONFLICT)[m
[32m+[m[32m    _clear_camera_state(state)[m
[32m+[m[32m    if session.status == 'capturing':[m
[32m+[m[32m        session.status = 'processing'[m
[32m+[m[32m        session.save(update_fields=['status'])[m
[32m+[m[32m    return Response({[m
[32m+[m[32m        'ended': True,[m
[32m+[m[32m        'session_id': session.id,[m
[32m+[m[32m        'status': session.status,[m
[32m+[m[32m        'capture_count': session.captures.count(),[m
[32m+[m[32m    })[m
[32m+[m
[32m+[m
[32m+[m[32m# ---------------------------------------------------------------- teacher auth[m
[32m+[m
[32m+[m[32mdef _safe_username(user):[m
[32m+[m[32m    """Return a display-friendly username, falling back to the account id."""[m
[32m+[m[32m    username = getattr(user, 'username', '') or ''[m
[32m+[m[32m    if username:[m
[32m+[m[32m        return username[m
[32m+[m[32m    return 'user_%s' % getattr(user, 'pk', '')[m
[32m+[m
[32m+[m
[32m+[m[32m@api_view(['POST'])[m
[32m+[m[32m@permission_classes([AllowAny])[m
[32m+[m[32mdef auth_login(request):[m
[32m+[m[32m    """Authenticate a teacher and establish a Django session.[m
[32m+[m
[32m+[m[32m    Accepts ``username`` and ``password``. Returns a generic error for any[m
[32m+[m[32m    invalid credential so callers cannot enumerate registered accounts.[m
[32m+[m[32m    CSRF is enforced by CsrfViewMiddleware; do not exempt this view.[m
[32m+[m[32m    """[m
[32m+[m[32m    username = (request.data.get('username') or '').strip()[m
[32m+[m[32m    password = request.data.get('password') or ''[m
[32m+[m
[32m+[m[32m    if not username or not password:[m
[32m+[m[32m        return Response({'detail': 'Username and password are required.'},[m
[32m+[m[32m                        status=status.HTTP_400_BAD_REQUEST)[m
[32m+[m
[32m+[m[32m    user = authenticate(request, username=username, password=password)[m
[32m+[m[32m    if user is None:[m
[32m+[m[32m        # Generic message: do not reveal whether the username exists.[m
[32m+[m[32m        return Response({'detail': 'Invalid credentials.'},[m
[32m+[m[32m                        status=status.HTTP_401_UNAUTHORIZED)[m
[32m+[m
[32m+[m[32m    django_login(request, user)[m
[32m+[m[32m    return Response({[m
[32m+[m[32m        'authenticated': True,[m
[32m+[m[32m        'user': {[m
[32m+[m[32m            'id': user.pk,[m
[32m+[m[32m            'username': _safe_username(user),[m
[32m+[m[32m            'display_name': _safe_username(user),[m
[32m+[m[32m        },[m
[32m+[m[32m    })[m
[32m+[m
[32m+[m
[32m+[m[32m@api_view(['POST'])[m
[32m+[m[32m@permission_classes([IsAuthenticated])[m
[32m+[m[32mdef auth_logout(request):[m
[32m+[m[32m    """End the authenticated teacher's session."""[m
[32m+[m[32m    django_logout(request)[m
[32m+[m[32m    return Response({'logged_out': True})[m
[32m+[m
[32m+[m
[32m+[m[32m@api_view(['GET'])[m
[32m+[m[32m@permission_classes([IsAuthenticated])[m
[32m+[m[32mdef auth_me(request):[m
[32m+[m[32m    """Return safe information about the currently authenticated teacher."""[m
[32m+[m[32m    user = request.user[m
[32m+[m[32m    return Response({[m
[32m+[m[32m        'id': user.pk,[m
[32m+[m[32m        'username': _safe_username(user),[m
[32m+[m[32m        'display_name': _safe_username(user),[m
[32m+[m[32m        'is_authenticated': True,[m
[32m+[m[32m    })[m
\ No newline at end of file[m
[1mdiff --git a/backend/config/settings.py b/backend/config/settings.py[m
[1mindex 8ffc0a8..ec7b839 100644[m
[1m--- a/backend/config/settings.py[m
[1m+++ b/backend/config/settings.py[m
[36m@@ -70,6 +70,13 @@[m [mSTATIC_URL = 'static/'[m
 MEDIA_URL = '/media/'[m
 MEDIA_ROOT = BASE_DIR / 'media'[m
 [m
[32m+[m[32m# Device (ESP32-CAM) shared token. Read from env; never hardcode or log it.[m
[32m+[m[32mDEVICE_TOKEN = os.environ.get('DEVICE_TOKEN', '')[m
[32m+[m[32m# How long an armed session stays armed without renewal (minutes).[m
[32m+[m[32mDEVICE_SESSION_TIMEOUT_MINUTES = int(os.environ.get('DEVICE_SESSION_TIMEOUT_MINUTES', '120'))[m
[32m+[m[32m# Max accepted camera upload size in bytes.[m
[32m+[m[32mDEVICE_UPLOAD_MAX_BYTES = int(os.environ.get('DEVICE_UPLOAD_MAX_BYTES', str(10 * 1024 * 1024)))[m
[32m+[m
 DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'[m
 [m
 [m
[36m@@ -84,6 +91,12 @@[m [mREST_FRAMEWORK = {[m
     'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],[m
     'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',[m
     'PAGE_SIZE': 20,[m
[32m+[m[32m    'DEFAULT_AUTHENTICATION_CLASSES': [[m
[32m+[m[32m        'rest_framework.authentication.SessionAuthentication',[m
[32m+[m[32m    ],[m
[32m+[m[32m    'DEFAULT_PERMISSION_CLASSES': [[m
[32m+[m[32m        'rest_framework.permissions.IsAuthenticated',[m
[32m+[m[32m    ],[m
 }[m
 [m
 [m
