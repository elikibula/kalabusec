from django.db import models
from django.conf import settings
from courses.models import Course, Subject

class ResourceCategory(models.Model):
    """Categories for organizing resources"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text='Icon name or emoji')
    
    class Meta:
        verbose_name_plural = 'Resource Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Resource(models.Model):
    """Educational resources - documents, videos, links"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    RESOURCE_TYPES = [
        ('document', 'Document'),
        ('video', 'Video'),
        ('link', 'External Link'),
        ('presentation', 'Presentation'),
        ('image', 'Image'),
        ('other', 'Other'),
    ]
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    
    # File or URL
    file = models.FileField(upload_to='resources/', blank=True, null=True)
    url = models.URLField(blank=True, help_text='External URL')
    
    # Organization
    category = models.ForeignKey(
        ResourceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resources'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resources'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resources',
        help_text='Link to specific course or leave blank for general resource'
    )
    
    # Access control
    is_public = models.BooleanField(default=True, help_text='Public resources visible to all')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_resources'
    )
    
    # Metadata
    file_size = models.BigIntegerField(blank=True, null=True, help_text='Size in bytes')
    download_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def increment_downloads(self):
        self.download_count += 1
        self.save(update_fields=['download_count'])
