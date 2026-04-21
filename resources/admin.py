from django.contrib import admin
from .models import ResourceCategory, Resource

@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon']
    search_fields = ['name']

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'resource_type', 'category', 'subject', 'uploaded_by', 'download_count', 'is_public']
    list_filter = ['resource_type', 'category', 'subject', 'is_public', 'created_at']
    search_fields = ['title', 'description']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'description', 'resource_type')
        }),
        ('Files', {
            'fields': ('file', 'url')
        }),
        ('Organization', {
            'fields': ('category', 'subject', 'course')
        }),
        ('Settings', {
            'fields': ('is_public', 'uploaded_by', 'file_size', 'download_count')
        }),
    )
    
    readonly_fields = ['download_count']
