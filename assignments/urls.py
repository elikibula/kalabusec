from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [
    # Main Views
    path('', views.AssignmentListView.as_view(), name='list'),
    path('create/', views.AssignmentCreateView.as_view(), name='create'),

    # Assignment Detail & Actions
    path('<int:pk>/', views.AssignmentDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.AssignmentUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.AssignmentDeleteView.as_view(), name='delete'),
    path('<int:pk>/submit/', views.submit_assignment, name='submit'),

    # ====================== QUIZ URLS ======================
    path('quizzes/', views.QuizListView.as_view(), name='quiz_list'),
    path('quizzes/<int:pk>/', views.QuizDetailView.as_view(), name='quiz_detail'),
    path('quizzes/<int:pk>/start/', views.start_quiz, name='quiz_start'),
    path('quiz-attempt/<int:pk>/', views.take_quiz, name='take_quiz'),
    path('quiz-attempt/<int:pk>/submit/', views.submit_quiz, name='submit_quiz'),
    path('quiz-attempt/<int:pk>/result/', views.quiz_result, name='quiz_result'),

        # ====================== QUIZ MANAGEMENT (Teacher) ======================
    path('quizzes/create/', views.QuizCreateView.as_view(), name='quiz_create'),
    path('quizzes/<int:pk>/edit/', views.QuizUpdateView.as_view(), name='quiz_update'),
    
    path('quizzes/<int:quiz_id>/questions/add/', views.QuestionCreateView.as_view(), name='question_add'),
    path('questions/<int:pk>/edit/', views.QuestionUpdateView.as_view(), name='question_edit'),
    path('questions/<int:pk>/delete/', views.QuestionDeleteView.as_view(), name='question_delete'),

    # Grading
    path('submission/<int:pk>/grade/', views.grade_submission, name='grade'),
]