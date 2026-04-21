from django.db import models
from django.conf import settings
from django.db.models import F
from courses.models import Course, Subject


class ResourceCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = 'Resource categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Resource(models.Model):
    RESOURCE_TYPES = [
        ('document',     'Document'),
        ('video',        'Video'),
        ('link',         'External link'),
        ('presentation', 'Presentation'),
        ('image',        'Image'),
        ('other',        'Other'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)

    file = models.FileField(upload_to='resources/', blank=True, null=True)
    url = models.URLField(blank=True, help_text='External URL')

    category = models.ForeignKey(
        ResourceCategory,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resources'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resources'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resources',
        help_text='Link to a specific course, or leave blank for a general resource'
    )

    is_public = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_resources'
    )

    file_size = models.BigIntegerField(blank=True, null=True, help_text='Size in bytes')
    download_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def increment_downloads(self):
        """Atomic download counter — no race condition."""
        Resource.objects.filter(pk=self.pk).update(
            download_count=F('download_count') + 1
        )

    @property
    def file_size_display(self):
        if not self.file_size:
            return ''
        for unit in ('B', 'KB', 'MB', 'GB'):
            if self.file_size < 1024:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024
        return f"{self.file_size:.1f} TB"
