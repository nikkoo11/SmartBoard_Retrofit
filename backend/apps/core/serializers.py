from rest_framework import serializers
from .models import Course, LessonSession, Capture, PdfDocument


class CourseSerializer(serializers.ModelSerializer):
    session_count = serializers.SerializerMethodField()

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
