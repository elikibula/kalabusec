from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


# ── Shared widget style ────────────────────────────────────────────────────────

FIELD_CLASS = (
    'w-full px-4 py-3 rounded-lg border border-gray-300 '
    'focus:ring-2 focus:ring-indigo-500 focus:border-transparent '
    'bg-white text-gray-900 placeholder-gray-400 transition'
)


def styled(widget):
    widget.attrs.update({'class': FIELD_CLASS})
    return widget


# ── Login Form ─────────────────────────────────────────────────────────────────

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': FIELD_CLASS,
            'placeholder': 'Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': FIELD_CLASS,
            'placeholder': 'Password',
        })
    )


# ── Invite-based Registration Form ────────────────────────────────────────────

class InviteRegistrationForm(UserCreationForm):
    """
    Registration form used ONLY via a valid invite link.
    Email and role are pre-filled from the invitation — not editable by user.
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        # Accept invitation instance to pre-populate read-only fields
        self.invitation = kwargs.pop('invitation', None)
        super().__init__(*args, **kwargs)

        # Apply styling to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': FIELD_CLASS})

        # Pre-fill name from invite if provided
        if self.invitation:
            if self.invitation.first_name:
                self.fields['first_name'].initial = self.invitation.first_name
            if self.invitation.last_name:
                self.fields['last_name'].initial = self.invitation.last_name

        # Make name fields required
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

        # Add placeholders
        self.fields['first_name'].widget.attrs['placeholder'] = 'First name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Last name'
        self.fields['username'].widget.attrs['placeholder'] = 'Choose a username'
        self.fields['password1'].widget.attrs['placeholder'] = 'Create a password'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm password'

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.invitation:
            user.email = self.invitation.email
            user.role = self.invitation.role
        user.is_active = True
        if commit:
            user.save()
        return user


# ── Send Invite Form (for admins) ──────────────────────────────────────────────

class SendInviteForm(forms.Form):
    """
    Form used by admins/teachers to send invitations.
    """

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Administrator'),
        ('parent', 'Parent'),
    ]

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': FIELD_CLASS,
            'placeholder': 'recipient@email.com',
        })
    )
    first_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': FIELD_CLASS,
            'placeholder': 'First name (optional)',
        })
    )
    last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': FIELD_CLASS,
            'placeholder': 'Last name (optional)',
        })
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': FIELD_CLASS})
    )
    personal_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': FIELD_CLASS,
            'rows': 3,
            'placeholder': 'Optional personal message to include in the invite email...',
        })
    )

    def clean_email(self):
        from .models_invite import Invitation
        email = self.cleaned_data['email'].lower()

        # Check no active pending invite exists for this email
        if Invitation.objects.filter(email=email, status='pending').exists():
            raise forms.ValidationError(
                'An active invitation has already been sent to this email address.'
            )

        # Check user doesn't already exist
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'A user with this email address already exists.'
            )

        return email


# ── Bulk Invite Form (paste multiple emails) ───────────────────────────────────

class BulkInviteForm(forms.Form):
    """
    Paste multiple email addresses at once — one per line.
    All get the same role.
    """

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('parent', 'Parent'),
    ]

    emails = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': FIELD_CLASS,
            'rows': 6,
            'placeholder': 'Enter one email address per line:\njohn@example.com\njane@example.com',
        }),
        help_text='One email address per line.'
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': FIELD_CLASS})
    )

    def clean_emails(self):
        raw = self.cleaned_data['emails']
        emails = [e.strip().lower() for e in raw.splitlines() if e.strip()]

        if not emails:
            raise forms.ValidationError('Please enter at least one email address.')

        if len(emails) > 100:
            raise forms.ValidationError('Maximum 100 emails per bulk invite.')

        # Validate each address
        validator = forms.EmailField()
        invalid = []
        for email in emails:
            try:
                validator.clean(email)
            except forms.ValidationError:
                invalid.append(email)

        if invalid:
            raise forms.ValidationError(
                f'The following addresses are invalid: {", ".join(invalid)}'
            )

        return emails


# ── Profile Update Form ────────────────────────────────────────────────────────

class UserProfileForm(forms.ModelForm):

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone_number',
            'date_of_birth', 'bio', 'address', 'profile_picture',
            'student_id', 'grade_level',
            'employee_id', 'department', 'specialization',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        instance = self.instance if self.instance and self.instance.pk else self.user

        if instance:
            role = getattr(instance, 'role', 'other')
            if role != 'student':
                for f in ('student_id', 'grade_level'):
                    self.fields.pop(f, None)
            if role != 'teacher':
                for f in ('employee_id', 'department', 'specialization'):
                    self.fields.pop(f, None)

        for field in self.fields.values():
            field.widget.attrs.update({'class': FIELD_CLASS})