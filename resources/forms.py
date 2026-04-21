from django import forms
from .models import Resource


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = [
            'title',
            'description',
            'resource_type',
            'file',
            'url',
            'category',
            'subject',
            'course',
            'is_public',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and user.is_teacher:
            self.fields['course'].queryset = self.fields['course'].queryset.filter(
                teacher=user
            )

        self.fields['file'].required = False
        self.fields['url'].required = False

        text_like_class = (
            'w-full px-4 py-3 rounded-xl border border-gray-300 '
            'dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white '
            'focus:ring-2 focus:ring-green-500 focus:border-transparent'
        )

        for name, field in self.fields.items():
            if name == 'is_public':
                field.widget.attrs.update({
                    'class': 'h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500'
                })
            elif name == 'file':
                field.widget.attrs.update({
                    'class': (
                        'block w-full text-sm text-gray-700 dark:text-gray-300 '
                        'file:mr-4 file:py-2 file:px-4 file:rounded-xl '
                        'file:border-0 file:text-sm file:font-semibold '
                        'file:bg-green-50 file:text-green-700 '
                        'hover:file:bg-green-100'
                    )
                })
            else:
                field.widget.attrs.update({'class': text_like_class})

    def clean(self):
        cleaned_data = super().clean()
        resource_type = cleaned_data.get('resource_type')
        file = cleaned_data.get('file')
        url = cleaned_data.get('url')

        if resource_type in ['document', 'presentation', 'image', 'other'] and not file and not url:
            raise forms.ValidationError('Please upload a file or provide a URL.')

        if resource_type in ['video', 'link'] and not url and not file:
            raise forms.ValidationError('Please provide a URL or upload a file.')

        return cleaned_data