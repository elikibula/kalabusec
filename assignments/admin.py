from django.contrib import admin
from .models import Assignment, Submission, Quiz, Question, QuizAttempt

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'due_date', 'total_points', 'allow_late_submission']
    list_filter = ['course', 'due_date', 'allow_late_submission']
    search_fields = ['title', 'course__title']
    date_hierarchy = 'due_date'

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'assignment', 'submitted_at', 'status', 'score']
    list_filter = ['status', 'submitted_at']
    search_fields = ['student__username', 'assignment__title']
    date_hierarchy = 'submitted_at'

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'time_limit_minutes', 'total_points', 'available_from']
    list_filter = ['course', 'available_from']
    search_fields = ['title', 'course__title']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'question_type', 'order', 'points']
    list_filter = ['question_type', 'quiz']
    search_fields = ['question_text', 'quiz__title']

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'quiz', 'attempt_number', 'started_at', 'score']
    list_filter = ['quiz', 'started_at']
    search_fields = ['student__username', 'quiz__title']
