from django.contrib import admin
from .models import AboutPage, TimelineEvent, Department, StaffMember, HistoricalImage


class TimelineEventInline(admin.TabularInline):
    model = TimelineEvent
    extra = 1


class HistoricalImageInline(admin.TabularInline):
    model = HistoricalImage
    extra = 1


@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    list_display = ('school_name', 'updated_at')
    inlines = [TimelineEventInline, HistoricalImageInline]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'job_title', 'staff_type', 'department', 'order')
    list_filter = ('staff_type', 'department')
    search_fields = ('full_name', 'job_title')


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ('year', 'title', 'order')


@admin.register(HistoricalImage)
class HistoricalImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'order')