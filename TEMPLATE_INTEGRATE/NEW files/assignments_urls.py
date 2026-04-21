from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [
    # ── Assignments ──────────────────────────────────────────
    path('', views.AssignmentListView.as_view(), name='list'),
    path('create/', views.AssignmentCreateView.as_view(), name='create'),
    path('<int:pk>/', views.AssignmentDetailView.as_view(), name='detail'),

    # ── Submissions ──────────────────────────────────────────
    path('<int:pk>/submit/', views.submit_assignment, name='submit'),
    path('submission/<int:pk>/grade/', views.grade_submission, name='grade'),
]
