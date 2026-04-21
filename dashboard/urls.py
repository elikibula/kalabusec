from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('analytics/', views.analytics, name='analytics'),

    # Teacher quick-create shortcuts (stay within classroom context)
    path('classroom/<int:course_pk>/assignment/', views.quick_create_assignment, name='quick_assignment'),
    path('classroom/<int:course_pk>/announcement/', views.quick_create_announcement, name='quick_announcement'),
    path('classroom/<int:course_pk>/module/', views.quick_create_module, name='quick_module'),

    path('users/', views.users_configuration, name='users_configuration'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/change-role/', views.change_user_role, name='change_user_role'),
]