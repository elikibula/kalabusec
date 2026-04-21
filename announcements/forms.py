from django import forms
from .models import Announcement


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = [
            'title',
            'content',
            'course',
            'is_published',
            'is_pinned',
            'published_date',
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 6}),
            'published_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and user.is_teacher:
            self.fields['course'].queryset = self.fields['course'].queryset.filter(
                teacher=user
            )

        input_class = (
            "w-full px-4 py-3 rounded-xl border border-gray-300 "
            "dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white "
            "focus:ring-2 focus:ring-pink-500 focus:border-transparent"
        )

        for name, field in self.fields.items():
            if field.widget.__class__.__name__ == 'CheckboxInput':
                field.widget.attrs.update({
                    'class': 'h-4 w-4 rounded border-gray-300 text-pink-600 focus:ring-pink-500'
                })
            else:
                field.widget.attrs.update({'class': input_class})