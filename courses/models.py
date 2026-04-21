from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Course(models.Model):
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='courses')
    description = models.TextField()
    syllabus = models.FileField(upload_to='syllabi/', blank=True, null=True)

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teaching_courses'
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='enrolled_courses',
        blank=True
    )

    grade_level = models.IntegerField()
    term = models.CharField(max_length=20, null=True, choices=[
        ('term1', 'Term 1'),
        ('term2', 'Term 2'),
        ('term3', 'Term 3'),
    ])
    year = models.IntegerField()
    max_students = models.IntegerField(default=30)
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # NEW: enrolment window
    enrolment_open = models.DateTimeField(null=True, blank=True)
    enrolment_close = models.DateTimeField(null=True, blank=True)

    # NEW: approval required flag
    ENROLMENT_CHOICES = [
        ('open', 'Open — anyone can enrol'),
        ('approval', 'Requires teacher approval'),
        ('invite', 'Invite only'),
    ]
    enrolment_type = models.CharField(max_length=20, choices=ENROLMENT_CHOICES, default='open')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', 'term', 'title']
        unique_together = ['code', 'year', 'term']

    def __str__(self):
        return f"{self.code} - {self.title} ({self.year} {self.term})"

    def get_absolute_url(self):
        return reverse('courses:detail', kwargs={'pk': self.pk})

    @property
    def enrollment_count(self):
        return Enrollment.objects.filter(course=self, status='active').count()

    @property
    def is_full(self):
        return self.enrollment_count >= self.max_students

    @property
    def enrolment_is_open(self):
        now = timezone.now()
        if self.enrolment_open and now < self.enrolment_open:
            return False
        if self.enrolment_close and now > self.enrolment_close:
            return False
        return True


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['course', 'order']

    def __str__(self):
        return f"{self.course.code} - Module {self.order}: {self.title}"


class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField()
    video_url = models.URLField(blank=True, help_text='YouTube or video URL')
    attachments = models.FileField(upload_to='lesson_attachments/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    duration_minutes = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)
    release_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Optional scheduled release time for students.',
    )

    # NEW: prerequisite gating
    prerequisite = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unlocks',
        help_text='Student must complete this lesson first'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['module', 'order']

    def __str__(self):
        return f"{self.module.course.code} - {self.title}"

    def is_accessible_to(self, student):
        """Return True if the student may view this lesson."""
        if self.release_at and timezone.now() < self.release_at:
            return False
        if not self.prerequisite:
            return True
        return LessonCompletion.objects.filter(
            student=student,
            lesson=self.prerequisite
        ).exists()


class LessonFile(models.Model):
    """Multiple file attachments per lesson."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='lesson_files/')
    label = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label or self.file.name


class LessonCompletion(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_completions'
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)
    time_spent_minutes = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['student', 'lesson']
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.student.username} completed {self.lesson.title}"


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ('pending', 'Pending approval'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    final_grade = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    # NEW: approval tracking
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_enrollments'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.student.username} - {self.course.code} ({self.status})"


class CourseCompletionCertificate(models.Model):
    """Issued when a student completes all lessons in a course."""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    issued_at = models.DateTimeField(auto_now_add=True)
    certificate_number = models.CharField(max_length=40, unique=True)

    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-issued_at']

    def __str__(self):
        return f"Certificate: {self.student.username} — {self.course.code}"
