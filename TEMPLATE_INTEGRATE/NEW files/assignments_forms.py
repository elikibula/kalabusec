from django import forms
from .models import Assignment, Submission

TW = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent'


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = [
            'course', 'title', 'description', 'instructions',
            'attachment', 'total_points', 'due_date', 'available_from',
            'allow_late_submission', 'late_penalty_percent',
        ]
        widgets = {
            'description':    forms.Textarea(attrs={'rows': 4, 'class': TW}),
            'instructions':   forms.Textarea(attrs={'rows': 6, 'class': TW}),
            'due_date':       forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': TW}),
            'available_from': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': TW}),
            'total_points':   forms.NumberInput(attrs={'min': 0, 'class': TW}),
            'late_penalty_percent': forms.NumberInput(attrs={'min': 0, 'max': 100, 'class': TW}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ('allow_late_submission',) and 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = TW

    def clean(self):
        cleaned = super().clean()
        available = cleaned.get('available_from')
        due = cleaned.get('due_date')
        if available and due and due <= available:
            raise forms.ValidationError('Due date must be after the available-from date.')
        return cleaned


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['submission_text', 'attachment']
        widgets = {
            'submission_text': forms.Textarea(attrs={
                'rows': 10,
                'class': TW,
                'placeholder': 'Type your answer here…',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['attachment'].widget.attrs['class'] = TW
        self.fields['submission_text'].required = False
        self.fields['attachment'].required = False

    def clean(self):
        cleaned = super().clean()
        text = cleaned.get('submission_text', '').strip()
        attachment = cleaned.get('attachment')
        if not text and not attachment:
            raise forms.ValidationError(
                'Please provide either a text response or a file attachment.'
            )
        return cleaned
