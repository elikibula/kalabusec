from django import forms
from django.utils import timezone
from .models import Assignment, Submission, Quiz, Question
import json


# ====================== ASSIGNMENT FORM ======================

class AssignmentForm(forms.ModelForm):
    """Form for teachers to create/edit assignments"""

    class Meta:
        model = Assignment
        fields = [
            'course', 'title', 'description', 'instructions', 'status',
            'attachment', 'total_points', 'due_date', 'available_from',
            'allow_late_submission', 'late_penalty_percent'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'instructions': forms.Textarea(attrs={'rows': 8}),
            'status': forms.Select(),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'available_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'total_points': forms.NumberInput(attrs={'min': 0, 'step': 1}),
            'late_penalty_percent': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': 0.5}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user and self.user.is_teacher:
            self.fields['course'].queryset = self.fields['course'].queryset.filter(
                teacher=self.user, is_active=True
            )

        self.apply_tailwind_styles()

    def apply_tailwind_styles(self):
        tailwind_class = (
            "w-full px-4 py-3 rounded-xl border border-gray-300 "
            "focus:ring-2 focus:ring-blue-600 focus:border-transparent "
            "dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        )

        for field_name, field in self.fields.items():
            if field_name != 'allow_late_submission':
                field.widget.attrs.update({'class': tailwind_class})

    def clean(self):
        cleaned_data = super().clean()
        due_date = cleaned_data.get('due_date')
        available_from = cleaned_data.get('available_from')
        status = cleaned_data.get('status')

        if due_date and available_from and due_date <= available_from:
            self.add_error('due_date', "Due date must be after 'Available From' time.")

        if status == 'published' and available_from and available_from < timezone.now():
            # Allow backdated publish windows, but nudge teachers through help text instead of failing.
            self.fields['available_from'].help_text = 'This assignment will be visible to students immediately.'

        return cleaned_data


# ====================== SUBMISSION FORM ======================

class SubmissionForm(forms.ModelForm):
    """Form for students to submit assignments"""

    class Meta:
        model = Submission
        fields = ['submission_text', 'attachment']
        widgets = {
            'submission_text': forms.Textarea(attrs={
                'rows': 12,
                'placeholder': 'Write your answer or reflection here...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind_styles()

    def apply_tailwind_styles(self):
        tailwind_class = (
            "w-full px-4 py-3 rounded-xl border border-gray-300 "
            "focus:ring-2 focus:ring-blue-600 focus:border-transparent "
            "dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        )

        for field in self.fields.values():
            field.widget.attrs.update({'class': tailwind_class})


# ====================== QUIZ FORM ======================

class QuizForm(forms.ModelForm):
    """Form for teachers to create/edit quizzes"""

    class Meta:
        model = Quiz
        fields = [
            'course', 'title', 'description',
            'time_limit_minutes', 'total_points',
            'available_from', 'available_until',
            'allow_multiple_attempts', 'max_attempts',
            'show_correct_answers', 'shuffle_questions'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'available_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'available_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'time_limit_minutes': forms.NumberInput(attrs={'min': 5, 'step': 5}),
            'total_points': forms.NumberInput(attrs={'min': 0, 'step': 1}),
            'max_attempts': forms.NumberInput(attrs={'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user and self.user.is_teacher:
            self.fields['course'].queryset = self.fields['course'].queryset.filter(
                teacher=self.user, is_active=True
            )

        self.apply_tailwind_styles()

    def apply_tailwind_styles(self):
        tailwind_class = (
            "w-full px-4 py-3 rounded-xl border border-gray-300 "
            "focus:ring-2 focus:ring-blue-600 focus:border-transparent "
            "dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        )

        for field_name, field in self.fields.items():
            if field_name not in [
                'allow_multiple_attempts',
                'show_correct_answers',
                'shuffle_questions'
            ]:
                field.widget.attrs.update({'class': tailwind_class})

    def clean(self):
        cleaned_data = super().clean()
        available_from = cleaned_data.get('available_from')
        available_until = cleaned_data.get('available_until')

        if available_from and available_until and available_until <= available_from:
            self.add_error('available_until', "End time must be after start time.")

        return cleaned_data


# ====================== QUESTION FORM ======================

class QuestionForm(forms.ModelForm):
    """Form for teachers to create/edit quiz questions"""

    choices = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Enter one choice per line:\nOption A\nOption B\nOption C\nOption D'
        })
    )

    class Meta:
        model = Question
        fields = [
            'question_text',
            'question_type',
            'points',
            'order',
            'choices',
            'correct_answer',
            'explanation'
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 4}),
            'correct_answer': forms.TextInput(attrs={
                'placeholder': 'Exact correct answer'
            }),
            'explanation': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Pre-fill choices when editing
        if self.instance and self.instance.pk and self.instance.choices:
            try:
                choices_list = json.loads(self.instance.choices)
                self.initial['choices'] = '\n'.join(choices_list)
            except Exception:
                pass

        self.apply_tailwind_styles()

    def apply_tailwind_styles(self):
        tailwind_class = (
            "w-full px-4 py-3 rounded-xl border border-gray-300 "
            "focus:ring-2 focus:ring-blue-600 focus:border-transparent "
            "dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        )

        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': tailwind_class})

    # Convert choices input into JSON
    def clean_choices(self):
        q_type = self.cleaned_data.get('question_type')
        choices_text = self.cleaned_data.get('choices', '')

        # TRUE / FALSE auto-handling
        if q_type == 'true_false':
            return json.dumps(["True", "False"])

        if not choices_text.strip():
            return '[]'

        choices_list = [
            line.strip()
            for line in choices_text.splitlines()
            if line.strip()
        ]

        return json.dumps(choices_list)

    def clean(self):
        cleaned_data = super().clean()
        q_type = cleaned_data.get('question_type')
        choices = cleaned_data.get('choices')
        correct_answer = cleaned_data.get('correct_answer')

        if q_type == 'multiple_choice' and (not choices or choices == '[]'):
            self.add_error('choices', "Choices are required for Multiple Choice questions.")

        if q_type in ['multiple_choice', 'true_false'] and not correct_answer:
            self.add_error('correct_answer', "Correct answer is required for auto-graded questions.")

        # Normalize True/False answers
        if q_type == 'true_false' and correct_answer:
            cleaned_data['correct_answer'] = correct_answer.strip().title()

        return cleaned_data
