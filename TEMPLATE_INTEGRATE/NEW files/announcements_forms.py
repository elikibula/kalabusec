from django import forms
from django.utils import timezone
from .models import Announcement

TW = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent'


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'course', 'is_published', 'is_pinned', 'published_date']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 6}),
            'published_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ('is_published', 'is_pinned'):
                field.widget.attrs.update({'class': TW})
        # Default published_date to now
        if not self.instance.pk:
            self.fields['published_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
        self.fields['course'].required = False
        self.fields['course'].help_text = 'Leave blank to post school-wide'
