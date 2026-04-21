from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('mainapp.urls')),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),    
    path('courses/', include('courses.urls')),
    path('assignments/', include('assignments.urls')),
    path('notifications/', include('notifications.urls')),
    path('resources/', include('resources.urls')),
    path('announcements/', include('announcements.urls')),
    path('news/', include ('news.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    
]




if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)