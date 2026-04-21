from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'recipient',
        'get_notif_type_display',
        'message_preview',
        'is_read',
        'created_at',
    ]
    
    list_filter = ['notif_type', 'is_read', 'created_at']
    search_fields = ['recipient__username', 'recipient__first_name', 
                    'recipient__last_name', 'message']
    
    ordering = ['-created_at']
    readonly_fields = ['created_at']

    fieldsets = [
        ('Notification Details', {
            'fields': ('recipient', 'notif_type', 'message', 'link')
        }),
        ('Status', {
            'fields': ('is_read', 'created_at')
        }),
    ]

    def message_preview(self, obj):
        return (obj.message[:75] + '...') if len(obj.message) > 75 else obj.message
    message_preview.short_description = 'Message'

    def get_notif_type_display(self, obj):
        return obj.get_notif_type_display()
    get_notif_type_display.short_description = 'Type'
    get_notif_type_display.admin_order_field = 'notif_type'

    # Bulk actions
    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} notification(s) marked as read.")
    mark_as_read.short_description = "Mark selected as Read"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} notification(s) marked as unread.")
    mark_as_unread.short_description = "Mark selected as Unread"