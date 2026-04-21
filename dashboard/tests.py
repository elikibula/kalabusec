from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assignments.models import Quiz
from courses.models import Course, Subject


User = get_user_model()


class TeacherDashboardTests(TestCase):
    def test_teacher_dashboard_includes_quiz_context(self):
        teacher = User.objects.create_user(
            username='teacher-dashboard',
            password='pass123',
            role='teacher',
        )
        subject = Subject.objects.create(name='Science', code='SCI')
        course = Course.objects.create(
            title='Physics',
            code='PHY101',
            subject=subject,
            description='Intro physics',
            teacher=teacher,
            grade_level=10,
            term='term1',
            year=2026,
        )
        quiz = Quiz.objects.create(
            course=course,
            title='Motion quiz',
            description='Kinematics basics',
            available_from=timezone.now() - timedelta(hours=1),
            available_until=timezone.now() + timedelta(hours=1),
        )

        self.client.force_login(teacher)
        response = self.client.get(reverse('dashboard:home'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('quizzes', response.context)
        self.assertIn('course_quizzes', response.context)
        self.assertIn(quiz, list(response.context['quizzes']))
        self.assertIn(quiz, list(response.context['course_quizzes']))
