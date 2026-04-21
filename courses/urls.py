from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # ── My courses / browse ──────────────────────────────────
    path('', views.CourseListView.as_view(), name='list'),
    path('browse/', views.CourseBrowseView.as_view(), name='browse'),

    # ── Course CRUD ──────────────────────────────────────────
    path('create/', views.CourseCreateView.as_view(), name='create'),
    path('<int:pk>/', views.CourseDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.CourseUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.CourseDeleteView.as_view(), name='delete'),
    path('<int:pk>/duplicate/', views.duplicate_course, name='duplicate'),

    # ── Enrolment ────────────────────────────────────────────
    path('<int:pk>/enroll/', views.enroll_course, name='enroll'),
    path('<int:pk>/unenroll/', views.unenroll_course, name='unenroll'),
    path('<int:pk>/enrolment-requests/', views.enrolment_requests, name='enrolment_requests'),
    path('enrolment/<int:enrollment_pk>/approve/', views.approve_enrolment, name='approve_enrolment'),
    path('enrolment/<int:enrollment_pk>/reject/', views.reject_enrolment, name='reject_enrolment'),

    # ── Roster ───────────────────────────────────────────────
    path('<int:pk>/roster/', views.student_roster, name='roster'),
    path('<int:pk>/roster/', views.student_roster, name='student_roster'),


    # ── Module CRUD + reorder ────────────────────────────────
    path('<int:course_pk>/module/create/', views.ModuleCreateView.as_view(), name='module_create'),
    path('module/<int:pk>/edit/', views.ModuleUpdateView.as_view(), name='module_update'),
    path('module/<int:pk>/delete/', views.ModuleDeleteView.as_view(), name='module_delete'),
    path('<int:course_pk>/modules/reorder/', views.reorder_modules, name='reorder_modules'),

    # ── Lesson CRUD + publish toggle + reorder ───────────────
    path('module/<int:module_pk>/lesson/create/', views.LessonCreateView.as_view(), name='lesson_create'),
    path('lesson/<int:pk>/', views.LessonDetailView.as_view(), name='lesson_detail'),
    path('lesson/<int:pk>/edit/', views.LessonUpdateView.as_view(), name='lesson_update'),
    path('lesson/<int:pk>/delete/', views.LessonDeleteView.as_view(), name='lesson_delete'),
    path('lesson/<int:pk>/complete/', views.complete_lesson, name='lesson_complete'),
    path('lesson/<int:pk>/toggle-publish/', views.toggle_lesson_publish, name='lesson_toggle_publish'),
    path('module/<int:module_pk>/lessons/reorder/', views.reorder_lessons, name='reorder_lessons'),

    # ── Lesson files ─────────────────────────────────────────
    path('lesson/<int:lesson_pk>/files/upload/', views.upload_lesson_file, name='lesson_file_upload'),
    path('lesson-file/<int:pk>/delete/', views.delete_lesson_file, name='lesson_file_delete'),

    # ── Certificates ─────────────────────────────────────────
    path('certificates/', views.my_certificates, name='my_certificates'),
    path('certificate/<int:pk>/', views.view_certificate, name='certificate'),

    path('<int:pk>/analysis/', views.course_analysis, name='course_analysis'),
    path('<int:pk>/analysis/export/csv/', views.course_analysis_export_csv, name='course_analysis_export_csv'),
]
