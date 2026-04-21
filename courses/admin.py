from django.contrib import admin
from .models import Subject, Course, Module, Lesson, LessonCompletion, Enrollment

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'created_at']
    search_fields = ['name', 'code']

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    fields = ['title', 'order', 'start_date', 'end_date']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'teacher', 'grade_level', 'term', 'year', 'is_active']
    list_filter = ['is_active', 'term', 'year', 'grade_level', 'subject']
    search_fields = ['title', 'code', 'teacher__username']
    filter_horizontal = ['students']
    inlines = [ModuleInline]
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "teacher":
            # Only show staff users as teacher options
            kwargs["queryset"] = db_field.related_model.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "students":
            # Show all users for students selection
            kwargs["queryset"] = db_field.related_model.objects.all()
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'code', 'subject', 'description', 'teacher')
        }),
        ('Academic Info', {
            'fields': ('grade_level', 'term', 'year')
        }),
        ('Settings', {
            'fields': ('max_students', 'syllabus', 'thumbnail', 'is_active')
        }),
    )

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ['title', 'order', 'duration_minutes', 'is_published']

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['course', 'title', 'order', 'start_date', 'end_date']
    list_filter = ['course']
    search_fields = ['title', 'course__title']
    inlines = [LessonInline]

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'order', 'duration_minutes', 'is_published']
    list_filter = ['is_published', 'module__course']
    search_fields = ['title', 'module__title']

@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ['student', 'lesson', 'completed_at']
    list_filter = ['completed_at', 'lesson__module__course']
    search_fields = ['student__username', 'lesson__title']

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'status', 'final_grade', 'enrolled_at']
    list_filter = ['status', 'enrolled_at', 'course']
    search_fields = ['student__username', 'course__title']
