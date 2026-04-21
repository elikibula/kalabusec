from django import forms
from .models import Resource

TW = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent'


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = [
            'title', 'description', 'resource_type',
            'file', 'url', 'category', 'subject', 'course', 'is_public',
        ]
        widgets = {
            'title':       forms.TextInput(attrs={'class': TW}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': TW}),
            'resource_type': forms.Select(attrs={'class': TW}),
            'url':         forms.URLInput(attrs={'class': TW, 'placeholder': 'https://…'}),
            'category':    forms.Select(attrs={'class': TW}),
            'subject':     forms.Select(attrs={'class': TW}),
            'course':      forms.Select(attrs={'class': TW}),
        }

    def clean(self):
        cleaned = super().clean()
        file = cleaned.get('file')
        url = cleaned.get('url')
        if not file and not url:
            raise forms.ValidationError(
                'Please provide either a file upload or an external URL.'
            )
        return cleaned
