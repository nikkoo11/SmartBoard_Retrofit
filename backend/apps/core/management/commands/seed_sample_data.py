from django.core.management.base import BaseCommand
from apps.core.models import Course, LessonSession
from datetime import date


class Command(BaseCommand):
    help = 'Seed sample data'

    def handle(self, *args, **options):
        c1, _ = Course.objects.get_or_create(code='CS101', defaults={'name': '[Sample] Intro to CS', 'section': 'A', 'schedule': 'Mon/Wed 9:00'})
        c2, _ = Course.objects.get_or_create(code='MATH201', defaults={'name': '[Sample] Calculus I', 'section': 'B', 'schedule': 'Tue/Thu 11:00'})
        LessonSession.objects.get_or_create(course=c1, title='[Sample] Arrays and Lists', defaults={'date': date.today(), 'status': 'draft', 'notes': '[Sample] Notes'})
        LessonSession.objects.get_or_create(course=c2, title='[Sample] Derivatives', defaults={'date': date.today(), 'status': 'capturing', 'notes': '[Sample] Notes'})
        self.stdout.write(self.style.SUCCESS('Sample data seeded'))

