from django.db import models

class Course(models.Model):
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    section = models.CharField(max_length=100, blank=True)
    schedule = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.code} - {self.name}'


class LessonSession(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('capturing', 'Capturing'),
        ('processing', 'Processing'),
        ('finalized', 'Finalized'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=200)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Capture(models.Model):
    session = models.ForeignKey(LessonSession, on_delete=models.CASCADE, related_name='captures')
    image = models.ImageField(upload_to='board_images/')
    extracted_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Capture for {self.session}'


class PdfDocument(models.Model):
    session = models.ForeignKey(LessonSession, on_delete=models.CASCADE, related_name='pdfs')
    file = models.FileField(upload_to='pdfs/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'PDF for {self.session}'

