from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from courses.models import Course

class Assignment(models.Model):
    """Assignment model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructions = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published')
    
    attachment = models.FileField(upload_to='assignment_files/', blank=True, null=True)
    
    total_points = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    due_date = models.DateTimeField()
    available_from = models.DateTimeField()
    
    allow_late_submission = models.BooleanField(default=True)
    late_penalty_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=10,
        help_text='Percentage deduction per day late'
    )
    published_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-due_date']
    
    def __str__(self):
        return f"{self.course.code} - {self.title}"
    
    def get_absolute_url(self):
        return reverse('assignments:detail', kwargs={'pk': self.pk})

    @property
    def timeline_state(self):
        now = timezone.now()
        if self.status == 'draft':
            return 'draft'
        if self.status == 'archived':
            return 'archived'
        if self.available_from > now:
            return 'upcoming'
        if self.due_date < now:
            return 'closed'
        return 'open'

    @property
    def is_visible_to_students(self):
        return self.status == 'published'

    def save(self, *args, **kwargs):
        if self.status == 'published' and self.published_at is None:
            self.published_at = timezone.now()
        if self.status != 'published':
            self.published_at = None
        super().save(*args, **kwargs)

class Submission(models.Model):
    """Student assignment submission"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
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
        ('graded', 'Graded'),
        ('returned', 'Returned'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    
    score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(blank=True, null=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_submissions'
    )
    
    class Meta:
        unique_together = ['assignment', 'student']
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"
    
    @property
    def is_late(self):
        return self.submitted_at > self.assignment.due_date
    
    @property
    def days_late(self):
        if self.is_late:
            delta = self.submitted_at - self.assignment.due_date
            return delta.days
        return 0

class Quiz(models.Model):
    """Quiz model"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    time_limit_minutes = models.IntegerField(default=60)
    total_points = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    
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
        return f"{self.course.code} - {self.title}"

class Question(models.Model):
    """Quiz question"""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
    ]
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    
    question_text = models.TextField()
    points = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    order = models.PositiveIntegerField(default=0)
    
    # For multiple choice and true/false
    choices = models.JSONField(blank=True, null=True, help_text='List of answer choices')
    correct_answer = models.CharField(max_length=500, blank=True)
    
    explanation = models.TextField(blank=True, help_text='Explanation of correct answer')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['quiz', 'order']
    
    def __str__(self):
        return f"{self.quiz.title} - Q{self.order}"

class QuizAttempt(models.Model):
    """Student quiz attempt"""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quiz_attempts'
    )
    
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    
    score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    answers = models.JSONField(default=dict, help_text='Student answers')
    
    attempt_number = models.IntegerField(default=1)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.quiz.title} (Attempt {self.attempt_number})"
