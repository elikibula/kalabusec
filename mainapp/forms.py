from django import forms
from .models import AboutPage, TimelineEvent, Department, StaffMember, HistoricalImage


class AboutPageForm(forms.ModelForm):
    class Meta:
        model = AboutPage
        fields = [
            'school_name',
            'title',
            'intro',
            'mission',
            'vision',
            'history_summary',
            'hero_image',
        ]
        widgets = {
            'school_name': forms.TextInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'intro': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'mission': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'vision': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'history_summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class TimelineEventForm(forms.ModelForm):
    class Meta:
        model = TimelineEvent
        fields = ['year', 'title', 'description', 'event_image', 'order']
        widgets = {
            'year': forms.TextInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class StaffMemberForm(forms.ModelForm):
    class Meta:
        model = StaffMember
        fields = [
            'full_name',
            'job_title',
            'staff_type',
            'department',
            'photo',
            'bio',
            'order',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'staff_type': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class HistoricalImageForm(forms.ModelForm):
    class Meta:
        model = HistoricalImage
        fields = ['title', 'image', 'caption', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'caption': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

#CONTACT US
class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Full Name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email Address'})
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write your message...'})
    )