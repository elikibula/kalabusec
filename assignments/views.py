from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.http import Http404
from django.db.models import Q

from .models import Assignment, Submission, Quiz, QuizAttempt, Question
from .forms import SubmissionForm, AssignmentForm, QuestionForm, QuizForm


# ====================== HELPERS ======================

def _display_name(user):
    full_name = user.get_full_name() if hasattr(user, 'get_full_name') else ''
    return full_name.strip() or getattr(user, 'username', 'A user')


def _notify(user, message, notif_type='general', link=''):
    if not user:
        return

    from notifications.models import Notification
    Notification.objects.create(
        recipient=user,
        message=message,
        notif_type=notif_type,
        link=link or '',
    )


def _notify_course_students(course, message, notif_type='general', link=''):
    students = course.students.all()
    for student in students:
        _notify(student, message, notif_type, link=link)


def _quiz_is_available(quiz):
    now = timezone.now()
    return quiz.available_from <= now <= quiz.available_until


# ====================== MIXINS ======================

class TeacherRequiredMixin(UserPassesTestMixin):
    """Restrict access to teachers and school admins only"""
    def test_func(self):
        return self.request.user.is_teacher or self.request.user.is_school_admin

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to perform this action.")
        return redirect('assignments:list')


def _can_manage_course(user, course):
    return user.is_school_admin or (user.is_teacher and course.teacher_id == user.id)


def _get_manageable_quiz_or_404(user, quiz_id):
    quiz = get_object_or_404(Quiz.objects.select_related('course'), pk=quiz_id)
    if _can_manage_course(user, quiz.course):
        return quiz
    raise Http404


# ====================== STUDENT + TEACHER VIEWS ======================

class AssignmentListView(LoginRequiredMixin, ListView):
    model = Assignment
    template_name = 'assignments/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()

        if user.is_student:
            queryset = Assignment.objects.filter(
                course__students=user
            ).exclude(status__in=['draft', 'archived'])
        elif user.is_teacher:
            queryset = Assignment.objects.filter(
                course__teacher=user
            )
        elif user.is_school_admin:
            queryset = Assignment.objects.all()
        else:
            queryset = Assignment.objects.none()

        if search := self.request.GET.get('search'):
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(course__title__icontains=search) |
                Q(course__code__icontains=search)
            )

        if course_id := self.request.GET.get('course'):
            queryset = queryset.filter(course_id=course_id)

        if status_filter := self.request.GET.get('status'):
            if status_filter in ['draft', 'published', 'archived']:
                queryset = queryset.filter(status=status_filter)
            elif status_filter == 'open':
                queryset = queryset.filter(status='published', available_from__lte=now, due_date__gte=now)
            elif status_filter == 'upcoming':
                queryset = queryset.filter(status='published', available_from__gt=now)
            elif status_filter == 'closed':
                queryset = queryset.filter(status='published', due_date__lt=now)

        return queryset.select_related('course').order_by('due_date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_student:
            courses = user.enrolled_courses.filter(is_active=True).order_by('title')
        elif user.is_teacher:
            courses = user.teaching_courses.filter(is_active=True).order_by('title')
        else:
            courses = Assignment.objects.values_list('course__id', flat=True)
            courses = []

        if user.is_school_admin:
            from courses.models import Course
            courses = Course.objects.filter(is_active=True).order_by('title')

        context['now'] = timezone.now()
        context['filter_courses'] = courses
        context['filter_status'] = self.request.GET.get('status', '')
        context['filter_course'] = self.request.GET.get('course', '')
        context['filter_search'] = self.request.GET.get('search', '')
        context['status_options'] = [
            ('open', 'Open'),
            ('upcoming', 'Upcoming'),
            ('closed', 'Closed'),
        ]
        if user.is_teacher or user.is_school_admin:
            context['status_options'] += [
                ('draft', 'Draft'),
                ('published', 'Published'),
                ('archived', 'Archived'),
            ]
        return context


class AssignmentDetailView(LoginRequiredMixin, DetailView):
    model = Assignment
    template_name = 'assignments/assignment_detail.html'
    context_object_name = 'assignment'

    def get_queryset(self):
        user = self.request.user
        queryset = Assignment.objects.select_related('course')
        if user.is_student:
            return queryset.filter(course__students=user).exclude(status__in=['draft', 'archived'])
        if user.is_teacher:
            return queryset.filter(course__teacher=user)
        if user.is_school_admin:
            return queryset
        return queryset.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignment = self.object
        user = self.request.user
        now = timezone.now()

        if user.is_student:
            context['submission'] = Submission.objects.filter(
                assignment=assignment, student=user
            ).first()

            context['can_submit'] = (
                assignment.status == 'published' and
                assignment.available_from <= now and
                assignment.course.students.filter(id=user.id).exists() and
                (assignment.allow_late_submission or now <= assignment.due_date)
            )

        elif (user.is_teacher and assignment.course.teacher == user) or user.is_school_admin:
            context['submissions'] = assignment.submissions.select_related('student').order_by('-submitted_at')

        context['now'] = now
        context['assignment_state'] = assignment.timeline_state
        return context


# ====================== TEACHER ONLY VIEWS ======================

class AssignmentCreateView(LoginRequiredMixin, TeacherRequiredMixin, CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignments/assignment_form.html'
    success_url = reverse_lazy('assignments:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.request.user.is_teacher:
            form.fields['course'].queryset = form.fields['course'].queryset.filter(
                teacher=self.request.user
            )
        return form

    def form_valid(self, form):
        response = super().form_valid(form)
        assignment = self.object

        if assignment.status == 'published':
            _notify_course_students(
                assignment.course,
                f'New assignment posted in {assignment.course.title}: {assignment.title}',
                'announcement',
                link=reverse('assignments:detail', kwargs={'pk': assignment.pk})
            )

        messages.success(self.request, "Assignment created successfully!")
        return response


class AssignmentUpdateView(LoginRequiredMixin, TeacherRequiredMixin, UpdateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignments/assignment_form.html'
    success_url = reverse_lazy('assignments:list')

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_school_admin:
            return queryset
        return queryset.filter(course__teacher=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.request.user.is_teacher:
            form.fields['course'].queryset = form.fields['course'].queryset.filter(
                teacher=self.request.user
            )
        return form

    def form_valid(self, form):
        old_assignment = self.get_object()
        old_status = old_assignment.status
        old_available_from = old_assignment.available_from
        response = super().form_valid(form)
        assignment = self.object

        became_published = old_status != 'published' and assignment.status == 'published'
        became_available_now = (
            assignment.status == 'published' and
            old_available_from > timezone.now() and
            assignment.available_from <= timezone.now()
        )

        if became_published or became_available_now:
            _notify_course_students(
                assignment.course,
                f'Assignment available in {assignment.course.title}: {assignment.title}',
                'announcement',
                link=reverse('assignments:detail', kwargs={'pk': assignment.pk})
            )

        messages.success(self.request, "Assignment updated successfully!")
        return response


class AssignmentDeleteView(LoginRequiredMixin, TeacherRequiredMixin, DeleteView):
    model = Assignment
    template_name = 'assignments/assignment_confirm_delete.html'
    success_url = reverse_lazy('assignments:list')

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_school_admin:
            return queryset
        return queryset.filter(course__teacher=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Assignment deleted successfully!")
        return super().form_valid(form)


# ====================== FUNCTION VIEWS ======================

@login_required
def submit_assignment(request, pk):
    """Submit or update assignment submission"""
    assignment = get_object_or_404(Assignment, pk=pk)

    if not request.user.is_student:
        messages.error(request, 'Only students can submit assignments.')
        return redirect('assignments:detail', pk=pk)

    if assignment.status != 'published':
        messages.error(request, 'This assignment is not currently accepting student submissions.')
        return redirect('assignments:detail', pk=pk)

    if timezone.now() < assignment.available_from:
        messages.error(request, 'This assignment is not available yet.')
        return redirect('assignments:detail', pk=pk)

    if not assignment.course.students.filter(id=request.user.id).exists():
        messages.error(request, 'You must be enrolled in this course.')
        return redirect('assignments:detail', pk=pk)

    if timezone.now() > assignment.due_date and not assignment.allow_late_submission:
        messages.error(request, 'This assignment is past due and no longer accepts submissions.')
        return redirect('assignments:detail', pk=pk)

    submission = Submission.objects.filter(
        assignment=assignment, student=request.user
    ).first()

    is_update = submission is not None

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = request.user
            submission.save()

            _notify(
                request.user,
                f'Your work for "{assignment.title}" has been submitted successfully.',
                'general',
                link=reverse('assignments:detail', kwargs={'pk': assignment.pk})
            )

            if assignment.course.teacher:
                action_text = 'updated a submission for' if is_update else 'submitted'
                _notify(
                    assignment.course.teacher,
                    f'{_display_name(request.user)} {action_text} "{assignment.title}" in {assignment.course.title}.',
                    'general',
                    link=reverse('assignments:detail', kwargs={'pk': assignment.pk})
                )

            messages.success(request, 'Assignment submitted successfully!')
            return redirect('assignments:detail', pk=pk)
    else:
        form = SubmissionForm(instance=submission)

    return render(request, 'assignments/submit_assignment.html', {
        'assignment': assignment,
        'form': form,
        'submission': submission,
    })


@login_required
def grade_submission(request, pk):
    """Grade a student submission (teachers only)"""
    submission = get_object_or_404(Submission, pk=pk)
    assignment = submission.assignment

    if not request.user.is_teacher or assignment.course.teacher != request.user:
        messages.error(request, 'You do not have permission to grade this submission.')
        return redirect('assignments:detail', pk=assignment.pk)

    if request.method == 'POST':
        score = request.POST.get('score')
        feedback = request.POST.get('feedback', '')

        try:
            score_value = float(score)
        except (TypeError, ValueError):
            messages.error(request, 'Invalid score value.')
            return redirect('assignments:detail', pk=assignment.pk)

        if score_value < 0 or score_value > float(assignment.total_points):
            messages.error(
                request,
                f'Score must be between 0 and {assignment.total_points}.'
            )
            return redirect('assignments:detail', pk=assignment.pk)

        submission.score = score_value
        submission.feedback = feedback
        submission.status = 'graded'
        submission.graded_at = timezone.now()
        submission.graded_by = request.user
        submission.save()

        _notify(
            submission.student,
            f'Your assignment "{assignment.title}" has been graded.',
            'assignment_graded',
            link=reverse('assignments:detail', kwargs={'pk': assignment.pk})
        )

        messages.success(request, 'Submission graded successfully!')
        return redirect('assignments:detail', pk=assignment.pk)

    return render(request, 'assignments/grade_submission.html', {
        'submission': submission,
    })


# ====================== QUIZ VIEWS ======================

class QuizListView(LoginRequiredMixin, ListView):
    model = Quiz
    template_name = 'assignments/quiz_list.html'
    context_object_name = 'quizzes'

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()

        if user.is_student:
            return Quiz.objects.filter(
                course__students=user,
                available_from__lte=now,
                available_until__gte=now
            ).select_related('course')

        if user.is_teacher:
            return Quiz.objects.filter(course__teacher=user).select_related('course')

        if user.is_school_admin:
            return Quiz.objects.select_related('course')

        return Quiz.objects.none()


class QuizDetailView(LoginRequiredMixin, DetailView):
    model = Quiz
    template_name = 'assignments/quiz_detail.html'
    context_object_name = 'quiz'

    def get_queryset(self):
        user = self.request.user
        queryset = Quiz.objects.select_related('course')

        if user.is_student:
            return queryset.filter(course__students=user)
        if user.is_teacher:
            return queryset.filter(course__teacher=user)
        if user.is_school_admin:
            return queryset
        return queryset.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        quiz = self.object

        if user.is_student:
            attempts = QuizAttempt.objects.filter(
                quiz=quiz, student=user
            ).order_by('-attempt_number')
            context['attempts'] = attempts
            context['can_start'] = (
                _quiz_is_available(quiz) and
                (quiz.allow_multiple_attempts or attempts.count() == 0)
            )
        return context


@login_required
def start_quiz(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    user = request.user
    now = timezone.now()

    if not user.is_student:
        messages.error(request, "Only students can take quizzes.")
        return redirect('assignments:quiz_detail', pk=pk)

    if not quiz.course.students.filter(pk=user.pk).exists():
        messages.error(request, "You must be enrolled in this course to take this quiz.")
        return redirect('assignments:quiz_list')

    if not (quiz.available_from <= now <= quiz.available_until):
        messages.error(request, "This quiz is not currently available.")
        return redirect('assignments:quiz_detail', pk=pk)

    attempts_count = QuizAttempt.objects.filter(quiz=quiz, student=user).count()
    if not quiz.allow_multiple_attempts and attempts_count >= quiz.max_attempts:
        messages.error(request, "You have reached the maximum number of attempts.")
        return redirect('assignments:quiz_detail', pk=pk)

    attempt = QuizAttempt.objects.create(
        quiz=quiz,
        student=user,
        attempt_number=attempts_count + 1
    )

    return redirect('assignments:take_quiz', pk=attempt.pk)


@login_required
def take_quiz(request, pk):
    attempt = get_object_or_404(QuizAttempt, pk=pk, student=request.user)

    if attempt.submitted_at:
        return redirect('assignments:quiz_result', pk=attempt.pk)

    questions = attempt.quiz.questions.all().order_by('order')

    return render(request, 'assignments/take_quiz.html', {
        'quiz': attempt.quiz,
        'attempt': attempt,
        'questions': questions,
    })


@login_required
def submit_quiz(request, pk):
    attempt = get_object_or_404(QuizAttempt, pk=pk, student=request.user)

    if attempt.submitted_at:
        return redirect('assignments:quiz_result', pk=attempt.pk)

    quiz = attempt.quiz
    questions = quiz.questions.all()
    answers = {}
    total_score = 0

    for question in questions:
        answer = request.POST.get(f'question_{question.id}')
        if answer:
            answers[str(question.id)] = answer.strip()

            if question.question_type in ['multiple_choice', 'true_false']:
                if answer.strip().lower() == question.correct_answer.strip().lower():
                    total_score += float(question.points)

    attempt.answers = answers
    attempt.submitted_at = timezone.now()
    attempt.score = total_score
    attempt.save()

    _notify(
        request.user,
        f'You submitted quiz "{quiz.title}" and scored {total_score} point(s).',
        'general',
        link=reverse('assignments:quiz_result', kwargs={'pk': attempt.pk})
    )

    if quiz.course.teacher:
        _notify(
            quiz.course.teacher,
            f'{_display_name(request.user)} submitted quiz "{quiz.title}" in {quiz.course.title}.',
            'general',
            link=reverse('assignments:quiz_detail', kwargs={'pk': quiz.pk})
        )

    messages.success(request, f"Quiz submitted! Your score: {total_score} points")
    return redirect('assignments:quiz_result', pk=attempt.pk)


@login_required
def quiz_result(request, pk):
    attempt = get_object_or_404(QuizAttempt, pk=pk, student=request.user)
    quiz = attempt.quiz
    questions = quiz.questions.all().order_by('order')

    return render(request, 'assignments/quiz_result.html', {
        'attempt': attempt,
        'quiz': quiz,
        'questions': questions,
    })


# ====================== TEACHER QUIZ MANAGEMENT ======================

class QuizCreateView(LoginRequiredMixin, TeacherRequiredMixin, CreateView):
    model = Quiz
    form_class = QuizForm
    template_name = 'assignments/quiz_form.html'
    success_url = reverse_lazy('assignments:quiz_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        quiz = self.object

        if _quiz_is_available(quiz):
            _notify_course_students(
                quiz.course,
                f'New quiz available in {quiz.course.title}: {quiz.title}',
                'announcement',
                link=reverse('assignments:quiz_detail', kwargs={'pk': quiz.pk})
            )

        messages.success(self.request, "Quiz created successfully!")
        return response


class QuizUpdateView(LoginRequiredMixin, TeacherRequiredMixin, UpdateView):
    model = Quiz
    form_class = QuizForm
    template_name = 'assignments/quiz_form.html'
    success_url = reverse_lazy('assignments:quiz_list')

    def get_queryset(self):
        if self.request.user.is_school_admin:
            return super().get_queryset()
        return super().get_queryset().filter(course__teacher=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        old_quiz = self.get_object()
        old_available_from = old_quiz.available_from
        old_available_until = old_quiz.available_until

        response = super().form_valid(form)
        quiz = self.object
        now = timezone.now()

        became_available_now = (
            old_available_from > now and
            quiz.available_from <= now <= quiz.available_until
        )
        reopened_now = (
            old_available_until < now and
            quiz.available_until >= now and
            quiz.available_from <= now
        )

        if became_available_now or reopened_now:
            _notify_course_students(
                quiz.course,
                f'Quiz available in {quiz.course.title}: {quiz.title}',
                'announcement',
                link=reverse('assignments:quiz_detail', kwargs={'pk': quiz.pk})
            )

        messages.success(self.request, "Quiz updated successfully!")
        return response


# ====================== QUESTION MANAGEMENT ======================

class QuestionCreateView(LoginRequiredMixin, TeacherRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'assignments/question_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.quiz = _get_manageable_quiz_or_404(request.user, self.kwargs['quiz_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = self.quiz
        return context

    def form_valid(self, form):
        form.instance.quiz = self.quiz
        messages.success(self.request, "Question added successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('assignments:quiz_detail', kwargs={'pk': self.kwargs['quiz_id']})


class QuestionUpdateView(LoginRequiredMixin, TeacherRequiredMixin, UpdateView):
    model = Question
    form_class = QuestionForm
    template_name = 'assignments/question_form.html'

    def get_queryset(self):
        if self.request.user.is_school_admin:
            return super().get_queryset()
        return super().get_queryset().filter(quiz__course__teacher=self.request.user)

    def get_success_url(self):
        return reverse('assignments:quiz_detail', kwargs={'pk': self.object.quiz.pk})


class QuestionDeleteView(LoginRequiredMixin, TeacherRequiredMixin, DeleteView):
    model = Question
    template_name = 'assignments/question_confirm_delete.html'

    def get_queryset(self):
        if self.request.user.is_school_admin:
            return super().get_queryset()
        return super().get_queryset().filter(quiz__course__teacher=self.request.user)

    def get_success_url(self):
        return reverse('assignments:quiz_detail', kwargs={'pk': self.object.quiz.pk})

    def form_valid(self, form):
        messages.success(self.request, "Question deleted successfully!")
        return super().form_valid(form)