
from django.urls import path, include
from mainapp import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'mainapp'


urlpatterns = [
    
    path('', views.home, name="home"),
    path('about-us/', views.about_us, name='about_us'),

     # About Dashboard
    path('dashboard/about/', views.about_dashboard, name='about_dashboard'),
    path('dashboard/about/edit/', views.edit_about_page, name='edit_about_page'),

    # Timeline
    path('dashboard/about/timeline/add/', views.add_timeline_event, name='add_timeline_event'),
    path('dashboard/about/timeline/<int:pk>/edit/', views.edit_timeline_event, name='edit_timeline_event'),
    path('dashboard/about/timeline/<int:pk>/delete/', views.delete_timeline_event, name='delete_timeline_event'),

    # Departments
    path('dashboard/about/departments/add/', views.add_department, name='add_department'),
    path('dashboard/about/departments/<int:pk>/edit/', views.edit_department, name='edit_department'),
    path('dashboard/about/departments/<int:pk>/delete/', views.delete_department, name='delete_department'),

    # Staff
    path('dashboard/about/staff/add/', views.add_staff_member, name='add_staff_member'),
    path('dashboard/about/staff/<int:pk>/edit/', views.edit_staff_member, name='edit_staff_member'),
    path('dashboard/about/staff/<int:pk>/delete/', views.delete_staff_member, name='delete_staff_member'),

    # Historical Images
    path('dashboard/about/history/add/', views.add_historical_image, name='add_historical_image'),
    path('dashboard/about/history/<int:pk>/edit/', views.edit_historical_image, name='edit_historical_image'),
    path('dashboard/about/history/<int:pk>/delete/', views.delete_historical_image, name='delete_historical_image'),

    path('contact-us/', views.contact_us, name='contact_us'),

]
    





