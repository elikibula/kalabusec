from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import User

TW = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent'
TW_SM = 'w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': TW, 'placeholder': 'Username', 'autofocus': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TW, 'placeholder': 'Password'})
    )


class UserRegistrationForm(forms.ModelForm):
    """Open registration form (non-invite path)."""
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': TW}),
        validators=[validate_password],
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'class': TW}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'role']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': TW}),
            'last_name': forms.TextInput(attrs={'class': TW}),
            'username': forms.TextInput(attrs={'class': TW}),
            'email': forms.EmailInput(attrs={'class': TW}),
            'role': forms.Select(attrs={'class': TW}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class InviteRegistrationForm(forms.ModelForm):
    """Registration form pre-filled from an invitation."""
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': TW}),
        validators=[validate_password],
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'class': TW}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': TW}),
            'last_name': forms.TextInput(attrs={'class': TW}),
            'username': forms.TextInput(attrs={'class': TW}),
        }

    def __init__(self, *args, invitation=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.invitation = invitation
        if invitation:
            self.fields['first_name'].initial = invitation.first_name
            self.fields['last_name'].initial = invitation.last_name

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return p2

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('That username is already taken.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.invitation.email
        user.role = self.invitation.role
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class SendInviteForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': TW, 'placeholder': 'email@example.com'})
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': TW, 'placeholder': 'First name (optional)'})
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': TW, 'placeholder': 'Last name (optional)'})
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': TW})
    )
    personal_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': TW, 'rows': 3,
            'placeholder': 'Optional personal message to include in the invitation email…'
        })
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email


class BulkInviteForm(forms.Form):
    emails_raw = forms.CharField(
        label='Email addresses',
        widget=forms.Textarea(attrs={
            'class': TW, 'rows': 6,
            'placeholder': 'One email per line, or comma-separated:\njohn@example.com\njane@example.com'
        }),
        help_text='Enter one email address per line, or separate with commas.'
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': TW})
    )

    def clean_emails_raw(self):
        raw = self.cleaned_data['emails_raw']
        # Accept newline or comma-separated
        emails = [
            e.strip().lower()
            for e in raw.replace(',', '\n').splitlines()
            if e.strip()
        ]
        if not emails:
            raise forms.ValidationError('Please enter at least one email address.')
        invalid = [e for e in emails if '@' not in e or '.' not in e.split('@')[-1]]
        if invalid:
            raise forms.ValidationError(
                f'Invalid email(s): {", ".join(invalid[:5])}'
            )
        return emails

    # Make cleaned_data['emails'] work as expected in the view
    @property
    def cleaned_emails(self):
        return self.cleaned_data.get('emails_raw', [])


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email',
            'bio', 'phone_number', 'date_of_birth', 'address',
            'profile_picture',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': TW}),
            'last_name': forms.TextInput(attrs={'class': TW}),
            'email': forms.EmailInput(attrs={'class': TW}),
            'bio': forms.Textarea(attrs={'class': TW, 'rows': 3}),
            'phone_number': forms.TextInput(attrs={'class': TW}),
            'date_of_birth': forms.DateInput(attrs={'class': TW, 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': TW, 'rows': 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # user kwarg is passed from the view — kept for compatibility
