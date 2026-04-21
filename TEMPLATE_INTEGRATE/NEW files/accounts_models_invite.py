import uuid
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone


class Invitation(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('accepted', 'Accepted'),
        ('expired',  'Expired'),
        ('revoked',  'Revoked'),
    ]

    # The person being invited
    email = models.EmailField()
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    role = models.CharField(
        max_length=20,
        choices=settings.AUTH_USER_MODEL and [
            ('student', 'Student'),
            ('teacher', 'Teacher'),
            ('admin',   'Administrator'),
            ('parent',  'Parent'),
        ],
        default='student'
    )
    personal_message = models.TextField(blank=True)

    # The one-time token embedded in the email link
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Who sent the invite
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_invitations'
    )

    # Who accepted it (populated on acceptance)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_invitation'
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invite → {self.email} ({self.status})"

    def save(self, *args, **kwargs):
        # Default expiry: 72 hours from creation
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=72)
        super().save(*args, **kwargs)

    # ── Properties ────────────────────────────────────────────

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        if self.status not in ('pending',):
            return False
        if self.is_expired:
            return False
        return True

    def get_role_display(self):
        role_map = {
            'student': 'Student',
            'teacher': 'Teacher',
            'admin':   'Administrator',
            'parent':  'Parent',
        }
        return role_map.get(self.role, self.role.title())

    def get_register_url(self):
        return reverse('accounts:register_invite', kwargs={'token': self.token})

    # ── State transitions ──────────────────────────────────────

    def accept(self, user):
        """Call this after successfully creating the user account."""
        self.status = 'accepted'
        self.accepted_by = user
        self.save(update_fields=['status', 'accepted_by', 'updated_at'])

    def revoke(self):
        self.status = 'revoked'
        self.save(update_fields=['status', 'updated_at'])

    def mark_expired(self):
        self.status = 'expired'
        self.save(update_fields=['status', 'updated_at'])
