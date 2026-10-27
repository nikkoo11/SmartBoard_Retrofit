from django.contrib import admin
from .models import Course, CourseMeeting, LessonSession


class CourseMeetingInline(admin.TabularInline):
    model = CourseMeeting
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'section')
    inlines = [CourseMeetingInline]


@admin.register(LessonSession)
class LessonSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'date', 'status', 'started_at', 'ended_at')
    list_filter = ('status', 'course')