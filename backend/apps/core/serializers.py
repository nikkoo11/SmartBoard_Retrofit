from rest_framework import serializers
from .models import Course, CourseMeeting, LessonSession, Capture, PdfDocument


class CourseMeetingSerializer(serializers.ModelSerializer):
    weekday_label = serializers.CharField(source='get_weekday_display', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)

    class Meta:
        model = CourseMeeting
        fields = '__all__'

    def validate(self, attrs):
        start = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        if start and end and end <= start:
            raise serializers.ValidationError({'end_time': 'End time must be after start time.'})
        return attrs


class CourseSerializer(serializers.ModelSerializer):
    session_count = serializers.SerializerMethodField()
    meetings = CourseMeetingSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = '__all__'

    def get_session_count(self, obj):
        return obj.sessions.count()


class LessonSessionSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    capture_count = serializers.SerializerMethodField()
    pdf_count = serializers.SerializerMethodField()

    class Meta:
        model = LessonSession
        fields = '__all__'

    def get_capture_count(self, obj):
        return obj.captures.count()

    def get_pdf_count(self, obj):
        return obj.pdfs.count()

    def validate(self, attrs):
        """Allow only one open (draft/capturing) session per course.

        The rule is checked when a session is created, or when an existing
        session changes from a closed status to an open one. Editing the title
        or notes of an already-open session is never blocked.
        """
        open_statuses = LessonSession.OPEN_STATUSES
        creating = self.instance is None
        course = attrs.get('course') or (self.instance.course if self.instance else None)
        new_status = attrs.get('status', self.instance.status if self.instance else 'draft')
        becoming_open = (
            not creating
            and new_status in open_statuses
            and self.instance.status not in open_statuses
        )
        if course is not None and new_status in open_statuses and (creating or becoming_open):
            others = LessonSession.objects.filter(course=course, status__in=open_statuses)
            if self.instance is not None:
                others = others.exclude(pk=self.instance.pk)
            other = others.order_by('-date', '-created_at').first()
            if other is not None:
                raise serializers.ValidationError({
                    'course': 'Session "%s" (%s) is still open for this class. '
                              'Finalize it first.' % (other.title, other.date)
                })
        return attrs


class CaptureSerializer(serializers.ModelSerializer):
    session_title = serializers.CharField(source='session.title', read_only=True)

    class Meta:
        model = Capture
        fields = '__all__'


class PdfDocumentSerializer(serializers.ModelSerializer):
    session_title = serializers.CharField(source='session.title', read_only=True)
    course_name = serializers.CharField(source='session.course.name', read_only=True)

    class Meta:
        model = PdfDocument
        fields = '__all__'