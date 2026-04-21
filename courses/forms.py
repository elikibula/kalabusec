from django import forms
from .models import Course, Module, Lesson, LessonFile, Enrollment

TW = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent'


def _tw(fields, form):
    for name, field in form.fields.items():
        if name not in fields:
            field.widget.attrs.update({'class': TW})


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'title', 'code', 'subject', 'description', 'syllabus',
            'grade_level', 'term', 'year', 'max_students', 'thumbnail',
            'enrolment_type', 'enrolment_open', 'enrolment_close', 'is_active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'year': forms.NumberInput(attrs={'min': 2020, 'max': 2030}),
            'enrolment_open': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'enrolment_close': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _tw(['is_active'], self)


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description', 'order', 'start_date', 'end_date']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _tw([], self)


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            'title', 'content', 'video_url', 'attachments',
            'order', 'duration_minutes', 'is_published', 'release_at', 'prerequisite',
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
            'release_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _tw(['is_published'], self)


class LessonFileForm(forms.ModelForm):
    class Meta:
        model = LessonFile
        fields = ['file', 'label']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _tw([], self)


class EnrolmentApprovalForm(forms.Form):
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Reason for rejection (optional)'}),
        label='Rejection reason'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reason'].widget.attrs.update({'class': TW})


class ReorderForm(forms.Form):
    """Dummy form — reordering is handled via JSON POST."""
    pass
