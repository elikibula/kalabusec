from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPES = [
        ('enrolment', 'Enrolment confirmed'),
        ('enrolment_request', 'Enrolment request'),
        ('enrolment_approved', 'Enrolment approved'),
        ('enrolment_rejected', 'Enrolment rejected'),
        ('assignment_graded', 'Assignment graded'),
        ('announcement', 'Announcement'),
        ('certificate', 'Certificate issued'),
        ('general', 'General'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    message = models.TextField()
    notif_type = models.CharField(max_length=30, choices=TYPES, default='general')
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notif_type}] → {self.recipient.username}: {self.message[:60]}"
