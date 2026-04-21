import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Invitation(models.Model):
    """
    Invite-only registration system.
    Admin sends an invite → user registers via unique token link.
    """

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Administrator'),
        ('parent', 'Parent'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]

    # Who is being invited
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)

    # Secure token — unguessable, single-use
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Who sent the invite
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_invitations',
    )

    # Lifecycle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    # The account created from this invite
    accepted_by = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invite',
    )

    # Optional: personalised message from admin
    personal_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invite → {self.email} ({self.role}) [{self.status}]"

    def save(self, *args, **kwargs):
        # Auto-set expiry to 72 hours from creation if not set
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=72)
        super().save(*args, **kwargs)

    # ── Helpers ──────────────────────────────────────────────

    @property
    def is_valid(self):
        """Token is usable: pending and not expired."""
        return self.status == 'pending' and timezone.now() < self.expires_at

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def mark_expired(self):
        self.status = 'expired'
        self.save(update_fields=['status'])

    def accept(self, user):
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.accepted_by = user
        self.save(update_fields=['status', 'accepted_at', 'accepted_by'])

    def revoke(self):
        self.status = 'revoked'
        self.save(update_fields=['status'])

    def get_register_url(self):
        from django.urls import reverse
        return reverse('accounts:register_invite', kwargs={'token': self.token})