from django.contrib import admin
from .models import Announcement

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'course', 'is_published', 'is_pinned', 'published_date']
    list_filter = ['is_published', 'is_pinned', 'published_date', 'course']
    search_fields = ['title', 'content', 'author__username']
    date_hierarchy = 'published_date'
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'content', 'author')
        }),
        ('Settings', {
            'fields': ('course', 'is_published', 'is_pinned', 'published_date')
        }),
    )
