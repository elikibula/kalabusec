from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_staff']
    list_filter = ['role', 'is_staff', 'is_active', 'grade_level']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'student_id', 'employee_id']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'profile_picture', 'bio', 'phone_number', 'date_of_birth', 'address')
        }),
        ('Student Info', {
            'fields': ('student_id', 'grade_level'),
            'classes': ('collapse',)
        }),
        ('Teacher Info', {
            'fields': ('employee_id', 'department', 'specialization'),
            'classes': ('collapse',)
        }),
    )
