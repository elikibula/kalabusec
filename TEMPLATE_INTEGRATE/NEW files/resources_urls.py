from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    path('', views.ResourceListView.as_view(), name='list'),
    path('upload/', views.ResourceCreateView.as_view(), name='upload'),
    path('<int:pk>/', views.ResourceDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ResourceUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.ResourceDeleteView.as_view(), name='delete'),
]
