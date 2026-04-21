from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assignments.models import Question, Quiz
from courses.models import Course, Enrollment, Lesson, Module, Subject


User = get_user_model()


class CourseEnhancementTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='course-teacher',
            password='pass123',
            role='teacher',
        )
        self.student = User.objects.create_user(
            username='course-student',
            password='pass123',
            role='student',
        )
        self.subject = Subject.objects.create(name='Science', code='SCI')
        self.course = Course.objects.create(
            title='Biology',
            code='BIO101',
            subject=self.subject,
            description='Intro biology',
            teacher=self.teacher,
            grade_level=10,
            term='term1',
            year=2026,
        )
        self.course.students.add(self.student)
        Enrollment.objects.create(student=self.student, course=self.course, status='active')
        self.module = Module.objects.create(
            course=self.course,
            title='Cells',
            description='Cell structure',
            order=1,
        )

    def test_student_course_detail_hides_future_release_lessons(self):
        Lesson.objects.create(
            module=self.module,
            title='Released lesson',
            content='Visible now',
            order=1,
            is_published=True,
        )
        Lesson.objects.create(
            module=self.module,
            title='Future lesson',
            content='Visible later',
            order=2,
            is_published=True,
            release_at=timezone.now() + timedelta(days=1),
        )

        self.client.force_login(self.student)
        response = self.client.get(reverse('courses:detail', args=[self.course.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Released lesson')
        self.assertNotContains(response, 'Future lesson')

    def test_duplicate_course_copies_quizzes_and_prerequisites(self):
        first_lesson = Lesson.objects.create(
            module=self.module,
            title='Lesson 1',
            content='Start here',
            order=1,
            is_published=True,
        )
        future_release = timezone.now() + timedelta(days=2)
        Lesson.objects.create(
            module=self.module,
            title='Lesson 2',
            content='Then here',
            order=2,
            is_published=True,
            prerequisite=first_lesson,
            release_at=future_release,
        )
        quiz = Quiz.objects.create(
            course=self.course,
            title='Cells quiz',
            description='Basics',
            available_from=timezone.now(),
            available_until=timezone.now() + timedelta(days=7),
        )
        Question.objects.create(
            quiz=quiz,
            question_text='What is the powerhouse of the cell?',
            question_type='short_answer',
            points=1,
            order=1,
        )

        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse('courses:duplicate', args=[self.course.pk]),
            {'year': self.course.year + 1, 'term': self.course.term},
        )

        self.assertEqual(response.status_code, 302)
        new_course = Course.objects.exclude(pk=self.course.pk).get()
        self.assertEqual(new_course.quizzes.count(), 1)
        self.assertEqual(new_course.quizzes.first().questions.count(), 1)
        new_lessons = list(Lesson.objects.filter(module__course=new_course).order_by('order'))
        self.assertEqual(len(new_lessons), 2)
        self.assertEqual(new_lessons[1].prerequisite_id, new_lessons[0].pk)
        self.assertEqual(new_lessons[1].release_at, future_release)
