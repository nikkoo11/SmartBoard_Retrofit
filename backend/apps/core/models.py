from django.db import models

class Course(models.Model):
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    section = models.CharField(max_length=100, blank=True)
    schedule = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.code} - {self.name}'


class CourseMeeting(models.Model):
    """One weekly class time, for example DSP on Monday 07:00-08:00.

    A course can have many meetings (for example Monday and Tuesday).
    weekday follows Python: Monday = 0 ... Sunday = 6.
    """
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='meetings')
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['weekday', 'start_time']

    def __str__(self):
        return f'{self.course.code} {self.get_weekday_display()} {self.start_time:%H:%M}-{self.end_time:%H:%M}'


class LessonSession(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('capturing', 'Capturing'),
        ('processing', 'Processing'),
        ('finalized', 'Finalized'),
    ]
    # A session in one of these statuses counts as "open".
    OPEN_STATUSES = ('draft', 'capturing')

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=200)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Capture(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]
    session = models.ForeignKey(LessonSession, on_delete=models.CASCADE, related_name='captures')
    image = models.ImageField(upload_to='board_images/')
    cleaned_image = models.ImageField(upload_to='board_cleaned/', blank=True, null=True)
    clean_ms = models.PositiveIntegerField(blank=True, null=True)
    extracted_text = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    ocr_engine = models.CharField(max_length=20, blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Capture for {self.session}'


class PdfDocument(models.Model):
    session = models.ForeignKey(LessonSession, on_delete=models.CASCADE, related_name='pdfs')
    capture = models.ForeignKey(Capture, on_delete=models.CASCADE, related_name='pdfs', null=True, blank=True)
    file = models.FileField(upload_to='pdfs/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'PDF for {self.session}'


class CameraState(models.Model):
    """Singleton row holding the currently armed camera session.

    There is exactly one row (pk=1). If armed_session is null the camera
    is idle. This makes the armed state survive server restarts and be
    visible to every worker process.
    """
    armed_session = models.OneToOneField(
        LessonSession, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='camera_state')
    armed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'CameraState(armed_session=%s)' % self.armed_session_id

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)