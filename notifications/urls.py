from django.urls import path
from .views import NotificationListView, unread_count, mark_read, mark_all_read

app_name = 'notifications'

urlpatterns = [
    path('', NotificationListView.as_view(), name='list'),
    path('unread-count/', unread_count, name='unread_count'),
    path('read/<int:pk>/', mark_read, name='mark_read'),
    path('read-all/', mark_all_read, name='mark_all_read'),
]