from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assignments.models import Assignment, Question, Quiz, QuizAttempt
from courses.models import Course, Subject


User = get_user_model()


class AssignmentSecurityTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1',
            password='pass123',
            role='teacher',
        )
        self.other_teacher = User.objects.create_user(
            username='teacher2',
            password='pass123',
            role='teacher',
        )
        self.student = User.objects.create_user(
            username='student1',
            password='pass123',
            role='student',
        )
        self.admin = User.objects.create_user(
            username='admin1',
            password='pass123',
            role='admin',
        )
        self.subject = Subject.objects.create(name='Math', code='MATH')
        self.course = Course.objects.create(
            title='Algebra I',
            code='ALG101',
            subject=self.subject,
            description='Foundations of algebra',
            teacher=self.teacher,
            grade_level=9,
            term='term1',
            year=2026,
        )

    def test_student_cannot_start_quiz_for_unenrolled_course(self):
        quiz = Quiz.objects.create(
            course=self.course,
            title='Quiz 1',
            description='Chapter 1 quiz',
            available_from=timezone.now() - timedelta(hours=1),
            available_until=timezone.now() + timedelta(hours=1),
        )

        self.client.force_login(self.student)
        response = self.client.get(reverse('assignments:quiz_start', args=[quiz.pk]))

        self.assertRedirects(response, reverse('assignments:quiz_list'))
        self.assertFalse(QuizAttempt.objects.filter(quiz=quiz, student=self.student).exists())

    def test_student_cannot_start_quiz_outside_availability_window(self):
        self.course.students.add(self.student)
        quiz = Quiz.objects.create(
            course=self.course,
            title='Quiz 2',
            description='Locked quiz',
            available_from=timezone.now() + timedelta(hours=1),
            available_until=timezone.now() + timedelta(hours=2),
        )

        self.client.force_login(self.student)
        response = self.client.get(reverse('assignments:quiz_start', args=[quiz.pk]))

        self.assertRedirects(response, reverse('assignments:quiz_detail', args=[quiz.pk]))
        self.assertFalse(QuizAttempt.objects.filter(quiz=quiz, student=self.student).exists())

    def test_teacher_cannot_add_question_to_another_teachers_quiz(self):
        quiz = Quiz.objects.create(
            course=self.course,
            title='Protected quiz',
            description='Owned by teacher 1',
            available_from=timezone.now() - timedelta(hours=1),
            available_until=timezone.now() + timedelta(hours=1),
        )

        self.client.force_login(self.other_teacher)
        response = self.client.post(
            reverse('assignments:question_add', args=[quiz.pk]),
            {
                'question_text': 'What is 2 + 2?',
                'question_type': 'multiple_choice',
                'points': '1',
                'order': '1',
                'choices': '3\n4\n5',
                'correct_answer': '4',
                'explanation': '',
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Question.objects.filter(quiz=quiz).count(), 0)

    def test_admin_can_open_assignment_update_for_other_teachers_course(self):
        assignment = Assignment.objects.create(
            course=self.course,
            title='Worksheet',
            description='Practice set',
            instructions='Solve all questions',
            total_points=20,
            due_date=timezone.now() + timedelta(days=3),
            available_from=timezone.now() - timedelta(days=1),
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse('assignments:update', args=[assignment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.course, response.context['form'].fields['course'].queryset)
