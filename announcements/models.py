from django.db import models
from django.conf import settings
from courses.models import Course

class Announcement(models.Model):
    """School-wide or course-specific announcements"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='announcements'
    )
    
    # Can be school-wide or course-specific
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='announcements',
        null=True,
        blank=True,
        help_text='Leave blank for school-wide announcement'
    )
    
    is_published = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    published_date = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_pinned', '-published_date']
    
    def __str__(self):
        return self.title
