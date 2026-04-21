from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from courses.models import Course


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructions = models.TextField(blank=True)
    attachment = models.FileField(upload_to='assignment_files/', blank=True, null=True)

    total_points = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    due_date = models.DateTimeField()
    available_from = models.DateTimeField(default=timezone.now)

    allow_late_submission = models.BooleanField(default=True)
    late_penalty_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=10,
        help_text='Percentage deducted per day late'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.course.code} — {self.title}"

    def get_absolute_url(self):
        return reverse('assignments:detail', kwargs={'pk': self.pk})

    @property
    def is_past_due(self):
        return timezone.now() > self.due_date

    @property
    def is_available(self):
        return timezone.now() >= self.available_from


class Submission(models.Model):
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name='submissions'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submissions'
    )

    submission_text = models.TextField(blank=True)
    attachment = models.FileField(upload_to='submissions/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('graded',    'Graded'),
        ('returned',  'Returned'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')

    score = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(blank=True, null=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='graded_submissions'
    )

    class Meta:
        unique_together = ['assignment', 'student']
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.username} — {self.assignment.title}"

    @property
    def is_late(self):
        return self.submitted_at > self.assignment.due_date

    @property
    def days_late(self):
        if self.is_late:
            return (self.submitted_at - self.assignment.due_date).days
        return 0

    @property
    def effective_score(self):
        """Score after applying late penalty."""
        if self.score is None:
            return None
        if self.is_late and self.assignment.late_penalty_percent:
            penalty = self.score * (self.assignment.late_penalty_percent / 100) * self.days_late
            return max(0, float(self.score) - float(penalty))
        return float(self.score)


class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    time_limit_minutes = models.IntegerField(default=60)
    total_points = models.DecimalField(max_digits=6, decimal_places=2, default=100)

    available_from = models.DateTimeField()
    available_until = models.DateTimeField()

    allow_multiple_attempts = models.BooleanField(default=False)
    max_attempts = models.IntegerField(default=1)
    show_correct_answers = models.BooleanField(default=False)
    shuffle_questions = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-available_from']
        verbose_name_plural = 'Quizzes'

    def __str__(self):
        return f"{self.course.code} — {self.title}"

    @property
    def is_available(self):
        now = timezone.now()
        return self.available_from <= now <= self.available_until


class Question(models.Model):
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple choice'),
        ('true_false',      'True / False'),
        ('short_answer',    'Short answer'),
        ('essay',           'Essay'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    question_text = models.TextField()
    points = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    order = models.PositiveIntegerField(default=0)

    # Stored as a JSON list for multiple choice / true-false
    choices = models.JSONField(blank=True, null=True, help_text='List of answer choices')
    correct_answer = models.CharField(max_length=500, blank=True)
    explanation = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['quiz', 'order']

    def __str__(self):
        return f"{self.quiz.title} — Q{self.order}"


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quiz_attempts'
    )

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    answers = models.JSONField(default=dict, help_text='Student answers keyed by question pk')
    attempt_number = models.IntegerField(default=1)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.username} — {self.quiz.title} (attempt {self.attempt_number})"

    @property
    def is_complete(self):
        return self.submitted_at is not None

    @property
    def time_taken_minutes(self):
        if self.submitted_at:
            return int((self.submitted_at - self.started_at).total_seconds() / 60)
        return None
