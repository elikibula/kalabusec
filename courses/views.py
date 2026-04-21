import uuid
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, Prefetch, Avg
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from assignments.models import Quiz, Question, Submission, QuizAttempt
from .models import ( Course, Module, Lesson, LessonFile, Enrollment, LessonCompletion, Subject, CourseCompletionCertificate )
from .forms import CourseForm, ModuleForm, LessonForm, LessonFileForm
from django.http import HttpResponse
import csv


@login_required
@require_POST
def unenroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk)

    # Allow only the course teacher or school admin
    if request.user.is_teacher and course.teacher != request.user:
        messages.error(request, "You are not allowed to manage this course.")
        return redirect('courses:detail', pk=course.pk)

    if not request.user.is_teacher and not request.user.is_school_admin:
        messages.error(request, "You are not allowed to unenrol students from this course.")
        return redirect('courses:detail', pk=course.pk)

    student_id = request.POST.get('student_id')
    if not student_id:
        messages.error(request, "No student was selected.")
        return redirect('courses:student_roster', pk=course.pk)

    enrollment = get_object_or_404(
        Enrollment,
        course=course,
        student_id=student_id,
        status='active'
    )

    enrollment.status = 'dropped'
    enrollment.reviewed_by = request.user
    enrollment.reviewed_at = timezone.now()
    enrollment.save()

    messages.success(
        request,
        f"{enrollment.student.get_full_name() or enrollment.student.username} has been unenrolled."
    )
    return redirect('courses:student_roster', pk=course.pk)


@login_required
def course_analysis(request, pk):
    course = get_object_or_404(Course, pk=pk)

    if not ((request.user.is_teacher and course.teacher == request.user) or request.user.is_school_admin):
        messages.error(request, 'Permission denied.')
        return redirect('courses:detail', pk=pk)

    enrollments = Enrollment.objects.filter(
        course=course,
        status='active'
    ).select_related('student')

    total_lessons = Lesson.objects.filter(
        module__course=course,
        is_published=True
    ).count()

    student_rows = []

    for enr in enrollments:
        student = enr.student

        completed_lessons = LessonCompletion.objects.filter(
            student=student,
            lesson__module__course=course
        ).count()

        progress_pct = round((completed_lessons / total_lessons * 100), 1) if total_lessons > 0 else 0

        submissions = Submission.objects.filter(
            student=student,
            assignment__course=course
        )

        submitted_count = submissions.count()
        graded_count = submissions.filter(status='graded').count()
        avg_assignment_score = submissions.filter(status='graded').aggregate(
            avg=Avg('score')
        )['avg'] or 0

        quiz_attempts = QuizAttempt.objects.filter(
            student=student,
            quiz__course=course,
            submitted_at__isnull=False
        )

        quiz_attempt_count = quiz_attempts.count()
        avg_quiz_score = quiz_attempts.aggregate(avg=Avg('score'))['avg'] or 0

        has_certificate = CourseCompletionCertificate.objects.filter(
            student=student,
            course=course
        ).exists()

        student_rows.append({
            'student': student,
            'status': enr.status,
            'completed_lessons': completed_lessons,
            'total_lessons': total_lessons,
            'progress_pct': progress_pct,
            'submitted_count': submitted_count,
            'graded_count': graded_count,
            'avg_assignment_score': round(avg_assignment_score, 2) if avg_assignment_score else 0,
            'quiz_attempt_count': quiz_attempt_count,
            'avg_quiz_score': round(avg_quiz_score, 2) if avg_quiz_score else 0,
            'has_certificate': has_certificate,
        })

    return render(request, 'courses/course_analysis.html', {
        'course': course,
        'student_rows': student_rows,
    })


@login_required
def course_analysis_export_csv(request, pk):
    course = get_object_or_404(Course, pk=pk)

    if not ((request.user.is_teacher and course.teacher == request.user) or request.user.is_school_admin):
        messages.error(request, 'Permission denied.')
        return redirect('courses:detail', pk=pk)

    enrollments = Enrollment.objects.filter(
        course=course,
        status='active'
    ).select_related('student')

    total_lessons = Lesson.objects.filter(
        module__course=course,
        is_published=True
    ).count()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{course.code}_analysis.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Student Name',
        'Username',
        'Status',
        'Lessons Completed',
        'Total Lessons',
        'Progress %',
        'Assignments Submitted',
        'Assignments Graded',
        'Average Assignment Score',
        'Quiz Attempts',
        'Average Quiz Score',
        'Certificate Issued',
    ])

    for enr in enrollments:
        student = enr.student

        completed_lessons = LessonCompletion.objects.filter(
            student=student,
            lesson__module__course=course
        ).count()

        progress_pct = round((completed_lessons / total_lessons * 100), 1) if total_lessons > 0 else 0

        submissions = Submission.objects.filter(
            student=student,
            assignment__course=course
        )

        submitted_count = submissions.count()
        graded_count = submissions.filter(status='graded').count()
        avg_assignment_score = submissions.filter(status='graded').aggregate(
            avg=Avg('score')
        )['avg'] or 0

        quiz_attempts = QuizAttempt.objects.filter(
            student=student,
            quiz__course=course,
            submitted_at__isnull=False
        )

        quiz_attempt_count = quiz_attempts.count()
        avg_quiz_score = quiz_attempts.aggregate(avg=Avg('score'))['avg'] or 0

        has_certificate = CourseCompletionCertificate.objects.filter(
            student=student,
            course=course
        ).exists()

        writer.writerow([
            student.get_full_name() or student.username,
            student.username,
            enr.status,
            completed_lessons,
            total_lessons,
            progress_pct,
            submitted_count,
            graded_count,
            round(avg_assignment_score, 2) if avg_assignment_score else 0,
            quiz_attempt_count,
            round(avg_quiz_score, 2) if avg_quiz_score else 0,
            'Yes' if has_certificate else 'No',
        ])

    return response

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _display_name(user):
    full_name = user.get_full_name() if hasattr(user, 'get_full_name') else ''
    return full_name.strip() or getattr(user, 'username', 'A user')


def _is_enrolled_active(user, course):
    return Enrollment.objects.filter(
        student=user, course=course, status='active'
    ).exists()


def _student_visible_lessons_queryset(course):
    now = timezone.now()
    return Lesson.objects.filter(
        module__course=course,
        is_published=True,
    ).filter(
        Q(release_at__isnull=True) | Q(release_at__lte=now)
    )


def _notify(user, message, notif_type, link=''):
    if not user:
        return

    from notifications.models import Notification
    Notification.objects.create(
        recipient=user,
        message=message,
        notif_type=notif_type,
        link=link or '',
    )


def _notify_course_students(course, message, notif_type='announcement', link=''):
    active_enrollments = Enrollment.objects.filter(
        course=course,
        status='active'
    ).select_related('student')

    for enrollment in active_enrollments:
        _notify(
            enrollment.student,
            message,
            notif_type,
            link=link
        )


def _maybe_issue_certificate(student, course):
    cert, created = CourseCompletionCertificate.objects.get_or_create(
        student=student,
        course=course,
        defaults={'certificate_number': uuid.uuid4().hex.upper()}
    )
    if created:
        _notify(
            student,
            f'You earned a certificate for completing {course.title}!',
            'certificate',
            link=reverse('courses:certificate', kwargs={'pk': cert.pk})
        )
    return cert if created else None


# ──────────────────────────────────────────────────────────────
# Mixins
# ──────────────────────────────────────────────────────────────

class TeacherRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_teacher or self.request.user.is_school_admin


class CourseOwnerMixin(UserPassesTestMixin):
    def get_course(self):
        raise NotImplementedError

    def test_func(self):
        user = self.request.user
        if user.is_school_admin:
            return True
        return user.is_teacher and self.get_course().teacher == user


# ──────────────────────────────────────────────────────────────
# Course discovery
# ──────────────────────────────────────────────────────────────

class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 12

    def get_queryset(self):
        user = self.request.user
        if user.is_student:
            ids = Enrollment.objects.filter(
                student=user, status='active'
            ).values_list('course_id', flat=True)
            qs = Course.objects.filter(is_active=True, id__in=ids)
        elif user.is_teacher:
            qs = Course.objects.filter(is_active=True, teacher=user)
        else:
            qs = Course.objects.filter(is_active=True)

        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )

        if s := self.request.GET.get('subject'):
            qs = qs.filter(subject_id=s)

        if g := self.request.GET.get('grade'):
            qs = qs.filter(grade_level=g)

        return qs.select_related('teacher', 'subject').prefetch_related('students')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['subjects'] = Subject.objects.all()
        ctx['grade_levels'] = range(9, 13)
        ctx['is_student'] = self.request.user.is_student

        if self.request.user.is_teacher:
            ctx['pending_count'] = Enrollment.objects.filter(
                course__teacher=self.request.user,
                status='pending'
            ).count()
        return ctx


class CourseBrowseView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'courses/course_browse.html'
    context_object_name = 'courses'
    paginate_by = 12

    def get_queryset(self):
        user = self.request.user

        if user.is_teacher:
            qs = Course.objects.filter(
                is_active=True,
                teacher=user
            )
        elif user.is_school_admin:
            qs = Course.objects.filter(is_active=True)
        else:
            qs = Course.objects.filter(is_active=True)

        if search := self.request.GET.get('search'):
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )

        if s := self.request.GET.get('subject'):
            qs = qs.filter(subject_id=s)

        if g := self.request.GET.get('grade'):
            qs = qs.filter(grade_level=g)

        return qs.select_related('teacher', 'subject')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['subjects'] = Subject.objects.all()
        ctx['grade_levels'] = range(9, 13)

        if self.request.user.is_student:
            ctx['enrolled_ids'] = set(
                Enrollment.objects.filter(
                    student=self.request.user,
                    status__in=['active', 'pending']
                ).values_list('course_id', flat=True)
            )

        return ctx


# ──────────────────────────────────────────────────────────────
# Course detail
# ──────────────────────────────────────────────────────────────

class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        course = self.object
        user = self.request.user
        visible_lessons = _student_visible_lessons_queryset(course)

        if user.is_student:
            enrollment = Enrollment.objects.filter(
                student=user, course=course
            ).first()
            ctx['enrollment'] = enrollment
            ctx['is_enrolled'] = bool(enrollment and enrollment.status == 'active')
            ctx['is_pending'] = bool(enrollment and enrollment.status == 'pending')

            if ctx['is_enrolled']:
                total = visible_lessons.count()
                completed_ids = set(
                    LessonCompletion.objects.filter(
                        student=user, lesson__module__course=course
                    ).values_list('lesson_id', flat=True)
                )
                ctx['completed_ids'] = completed_ids
                ctx['total_lessons'] = total
                ctx['completed_lessons'] = len(completed_ids)
                ctx['progress_percentage'] = round(
                    (len(completed_ids) / total * 100) if total > 0 else 0, 1
                )

                lessons = visible_lessons.select_related('prerequisite')
                ctx['lesson_access'] = {
                    lesson.pk: lesson.is_accessible_to(user)
                    for lesson in lessons
                }

                if total > 0 and len(completed_ids) == total:
                    _maybe_issue_certificate(user, course)
                    ctx['certificate'] = CourseCompletionCertificate.objects.filter(
                        student=user, course=course
                    ).first()

        elif (user.is_teacher and course.teacher == user) or user.is_school_admin:
            roster = Enrollment.objects.filter(
                course=course
            ).select_related('student').order_by('status', 'student__last_name')

            ctx['pending_enrollments'] = roster.filter(status='pending')
            ctx['active_count'] = roster.filter(status='active').count()

            total_lessons = visible_lessons.count()
            per_student = {
                row['student_id']: row['cnt']
                for row in LessonCompletion.objects.filter(
                    lesson__module__course=course
                ).values('student_id').annotate(cnt=Count('id'))
            }

            ctx['student_progress'] = [{
                'enrollment': enr,
                'completed': per_student.get(enr.student_id, 0),
                'total': total_lessons,
                'pct': round(
                    (per_student.get(enr.student_id, 0) / total_lessons * 100)
                    if total_lessons > 0 else 0, 1
                ),
            } for enr in roster.filter(status='active')]

        if user.is_student and ctx.get('is_enrolled'):
            lesson_queryset = visible_lessons.select_related('prerequisite').prefetch_related('files')
        elif user.is_student:
            lesson_queryset = Lesson.objects.none()
        else:
            lesson_queryset = Lesson.objects.filter(
                module__course=course
            ).select_related('prerequisite').prefetch_related('files')

        ctx['modules'] = course.modules.prefetch_related(
            Prefetch('lessons', queryset=lesson_queryset)
        ).order_by('order')

        return ctx


# ──────────────────────────────────────────────────────────────
# Enrolment
# ──────────────────────────────────────────────────────────────

@login_required
@require_POST
def enroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk, is_active=True)

    if not request.user.is_student:
        messages.error(request, 'Only students can enrol.')
        return redirect('courses:detail', pk=pk)

    if not course.enrolment_is_open:
        messages.error(request, 'Enrolment is not currently open.')
        return redirect('courses:detail', pk=pk)

    if course.enrolment_type == 'invite':
        messages.error(request, 'This course is invite-only.')
        return redirect('courses:detail', pk=pk)

    if course.is_full:
        messages.error(request, 'This course is full.')
        return redirect('courses:detail', pk=pk)

    initial_status = 'pending' if course.enrolment_type == 'approval' else 'active'

    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={'status': initial_status}
    )

    if not created and enrollment.status == 'dropped':
        enrollment.status = initial_status
        enrollment.save(update_fields=['status'])
        created = True

    if created:
        if initial_status == 'active':
            course.students.add(request.user)
            messages.success(request, f'Enrolled in {course.title}!')

            _notify(
                request.user,
                f'You are now enrolled in {course.title}.',
                'enrolment',
                link=reverse('courses:detail', kwargs={'pk': course.pk})
            )

            if course.teacher:
                _notify(
                    course.teacher,
                    f'{_display_name(request.user)} enrolled in {course.title}.',
                    'enrolment',
                    link=reverse('courses:student_roster', kwargs={'pk': course.pk})
                )
        else:
            messages.info(request, 'Your enrolment request is pending approval.')

            _notify(
                request.user,
                f'Your enrolment request for {course.title} has been submitted and is awaiting approval.',
                'enrolment_request',
                link=reverse('courses:detail', kwargs={'pk': course.pk})
            )

            if course.teacher:
                _notify(
                    course.teacher,
                    f'{_display_name(request.user)} wants to join {course.title}.',
                    'enrolment_request',
                    link=reverse('courses:enrolment_requests', kwargs={'pk': course.pk})
                )

    elif enrollment.status == 'pending':
        messages.info(request, 'Your request is already pending.')
    else:
        messages.info(request, 'You are already enrolled.')

    return redirect('courses:detail', pk=pk)


@login_required
@require_POST
def unenroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk)

    if not request.user.is_student:
        messages.error(request, 'Invalid action.')
        return redirect('courses:detail', pk=pk)

    try:
        enr = Enrollment.objects.get(student=request.user, course=course)
        enr.status = 'dropped'
        enr.save(update_fields=['status'])

        course.students.remove(request.user)

        _notify(
            request.user,
            f'You have unenrolled from {course.title}.',
            'general',
            link=reverse('courses:list')
        )

        if course.teacher:
            _notify(
                course.teacher,
                f'{_display_name(request.user)} unenrolled from {course.title}.',
                'general',
                link=reverse('courses:student_roster', kwargs={'pk': course.pk})
            )

        messages.success(request, f'Unenrolled from {course.title}.')
    except Enrollment.DoesNotExist:
        messages.error(request, 'You are not enrolled.')

    return redirect('courses:list')


@login_required
def enrolment_requests(request, pk):
    course = get_object_or_404(Course, pk=pk)

    if not ((request.user.is_teacher and course.teacher == request.user)
            or request.user.is_school_admin):
        messages.error(request, 'Permission denied.')
        return redirect('courses:detail', pk=pk)

    pending = Enrollment.objects.filter(
        course=course,
        status='pending'
    ).select_related('student')

    return render(request, 'courses/enrolment_requests.html', {
        'course': course,
        'pending': pending,
    })


@login_required
@require_POST
def approve_enrolment(request, enrollment_pk):
    enr = get_object_or_404(Enrollment, pk=enrollment_pk)
    course = enr.course

    if not ((request.user.is_teacher and course.teacher == request.user)
            or request.user.is_school_admin):
        messages.error(request, 'Permission denied.')
        return redirect('courses:detail', pk=course.pk)

    enr.status = 'active'
    enr.reviewed_by = request.user
    enr.reviewed_at = timezone.now()
    enr.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

    course.students.add(enr.student)

    _notify(
        enr.student,
        f'Your enrolment in {course.title} has been approved!',
        'enrolment_approved',
        link=reverse('courses:detail', kwargs={'pk': course.pk})
    )

    messages.success(request, f'{_display_name(enr.student)} approved.')
    return redirect('courses:enrolment_requests', pk=course.pk)


@login_required
@require_POST
def reject_enrolment(request, enrollment_pk):
    enr = get_object_or_404(Enrollment, pk=enrollment_pk)
    course = enr.course

    if not ((request.user.is_teacher and course.teacher == request.user)
            or request.user.is_school_admin):
        messages.error(request, 'Permission denied.')
        return redirect('courses:detail', pk=course.pk)

    reason = request.POST.get('reason', '').strip()

    enr.status = 'rejected'
    enr.reviewed_by = request.user
    enr.reviewed_at = timezone.now()
    enr.rejection_reason = reason
    enr.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason'])

    msg = f'Your enrolment in {course.title} was not approved.'
    if reason:
        msg += f' Reason: {reason}'

    _notify(
        enr.student,
        msg,
        'enrolment_rejected',
        link=reverse('courses:detail', kwargs={'pk': course.pk})
    )

    messages.info(request, f'{_display_name(enr.student)} rejected.')
    return redirect('courses:enrolment_requests', pk=course.pk)


# ──────────────────────────────────────────────────────────────
# Student roster
# ──────────────────────────────────────────────────────────────

@login_required
def student_roster(request, pk):
    course = get_object_or_404(Course, pk=pk)

    if not (
        (request.user.is_teacher and course.teacher == request.user)
        or request.user.is_school_admin
    ):
        messages.error(request, 'Permission denied.')
        return redirect('courses:detail', pk=pk)

    enrollments = (
        Enrollment.objects
        .filter(course=course, status='active')
        .select_related('student')
        .order_by('student__last_name', 'student__first_name')
    )

    total_lessons = Lesson.objects.filter(
        module__course=course,
        is_published=True
    ).count()

    per_student = {
        row['student_id']: row['cnt']
        for row in (
            LessonCompletion.objects
            .filter(lesson__module__course=course)
            .values('student_id')
            .annotate(cnt=Count('id'))
        )
    }

    roster_data = [{
        'enrollment': enr,
        'completed': per_student.get(enr.student_id, 0),
        'total': total_lessons,
        'pct': round(
            (per_student.get(enr.student_id, 0) / total_lessons * 100)
            if total_lessons > 0 else 0,
            1
        ),
    } for enr in enrollments]

    return render(request, 'courses/student_roster.html', {
        'course': course,
        'roster_data': roster_data,
        'total_lessons': total_lessons,
    })


# ──────────────────────────────────────────────────────────────
# Lessons
# ──────────────────────────────────────────────────────────────

class LessonDetailView(LoginRequiredMixin, DetailView):
    model = Lesson
    template_name = 'courses/lesson_detail.html'
    context_object_name = 'lesson'

    def dispatch(self, request, *args, **kwargs):
        resp = super().dispatch(request, *args, **kwargs)

        if request.user.is_authenticated:
            lesson = self.get_object()
            course = lesson.module.course
            user = request.user
            is_enrolled = _is_enrolled_active(user, course)

            allowed = (
                user.is_school_admin or
                course.teacher == user or
                (user.is_student and is_enrolled)
            )
            if not allowed:
                messages.error(request, 'You do not have access to this lesson.')
                return redirect('courses:detail', pk=course.pk)

            if user.is_student and lesson.release_at and timezone.now() < lesson.release_at:
                messages.warning(
                    request,
                    f'"{lesson.title}" will unlock on '
                    f'{timezone.localtime(lesson.release_at).strftime("%d %b %Y %H:%M")}.'
                )
                return redirect('courses:detail', pk=course.pk)

            if user.is_student and is_enrolled and not lesson.is_accessible_to(user):
                messages.warning(
                    request,
                    f'Complete "{lesson.prerequisite.title}" before accessing this lesson.'
                )
                return redirect('courses:detail', pk=course.pk)

        return resp

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lesson = self.object
        user = self.request.user

        if user.is_student:
            ctx['is_completed'] = LessonCompletion.objects.filter(
                student=user,
                lesson=lesson
            ).exists()

        siblings_queryset = Lesson.objects.filter(module=lesson.module, is_published=True)
        if user.is_student:
            siblings_queryset = siblings_queryset.filter(
                Q(release_at__isnull=True) | Q(release_at__lte=timezone.now())
            )

        siblings = list(siblings_queryset.order_by('order'))
        idx = next((i for i, l in enumerate(siblings) if l.pk == lesson.pk), None)

        if idx is not None:
            ctx['prev_lesson'] = siblings[idx - 1] if idx > 0 else None
            ctx['next_lesson'] = siblings[idx + 1] if idx < len(siblings) - 1 else None

        ctx['files'] = lesson.files.all()
        return ctx


@login_required
@require_POST
def complete_lesson(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)

    if not request.user.is_student:
        messages.error(request, 'Invalid action.')
        return redirect('courses:lesson_detail', pk=pk)

    course = lesson.module.course

    if not _is_enrolled_active(request.user, course):
        messages.error(request, 'You must be enrolled.')
        return redirect('courses:detail', pk=course.pk)

    if not lesson.is_accessible_to(request.user):
        messages.error(request, 'Complete the prerequisite lesson first.')
        return redirect('courses:lesson_detail', pk=pk)

    time_spent = int(request.POST.get('time_spent', 0))
    _, created = LessonCompletion.objects.get_or_create(
        student=request.user,
        lesson=lesson,
        defaults={'time_spent_minutes': time_spent}
    )

    if created:
        messages.success(request, f'"{lesson.title}" marked as complete!')

        total = Lesson.objects.filter(
            module__course=course,
            is_published=True
        ).count()
        completed = LessonCompletion.objects.filter(
            student=request.user,
            lesson__module__course=course
        ).count()

        if total > 0 and completed == total:
            cert = _maybe_issue_certificate(request.user, course)
            if cert:
                messages.success(
                    request,
                    f'You completed {course.title}! Your certificate is ready.'
                )
    else:
        messages.info(request, 'Already marked as complete.')

    return redirect('courses:lesson_detail', pk=pk)


@login_required
@require_POST
def toggle_lesson_publish(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    course = lesson.module.course

    if not ((request.user.is_teacher and course.teacher == request.user)
            or request.user.is_school_admin):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    lesson.is_published = not lesson.is_published
    lesson.save(update_fields=['is_published'])

    if lesson.is_published:
        _notify_course_students(
            course,
            f'"{lesson.title}" is now available in {course.title}.',
            'announcement',
            link=reverse('courses:lesson_detail', kwargs={'pk': lesson.pk})
        )

    return JsonResponse({'is_published': lesson.is_published})


@login_required
@require_POST
def reorder_modules(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)

    if not ((request.user.is_teacher and course.teacher == request.user)
            or request.user.is_school_admin):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    for item in json.loads(request.body):
        Module.objects.filter(pk=item['id'], course=course).update(order=item['order'])

    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def reorder_lessons(request, module_pk):
    module = get_object_or_404(Module, pk=module_pk)
    course = module.course

    if not ((request.user.is_teacher and course.teacher == request.user)
            or request.user.is_school_admin):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    for item in json.loads(request.body):
        Lesson.objects.filter(pk=item['id'], module=module).update(order=item['order'])

    return JsonResponse({'status': 'ok'})


# ──────────────────────────────────────────────────────────────
# Course CRUD
# ──────────────────────────────────────────────────────────────

class CourseCreateView(LoginRequiredMixin, TeacherRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('courses:list')

    def form_valid(self, form):
        form.instance.teacher = self.request.user
        messages.success(self.request, 'Course created!')
        return super().form_valid(form)


class CourseUpdateView(LoginRequiredMixin, CourseOwnerMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'

    def get_course(self):
        return self.get_object()

    def form_valid(self, form):
        messages.success(self.request, 'Course updated!')
        return super().form_valid(form)


class CourseDeleteView(LoginRequiredMixin, CourseOwnerMixin, DeleteView):
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    success_url = reverse_lazy('courses:list')

    def get_course(self):
        return self.get_object()

    def form_valid(self, form):
        messages.success(self.request, 'Course deleted.')
        return super().form_valid(form)


@login_required
def duplicate_course(request, pk):
    course = get_object_or_404(Course, pk=pk)

    if not ((request.user.is_teacher and course.teacher == request.user)
            or request.user.is_school_admin):
        messages.error(request, 'Permission denied.')
        return redirect('courses:detail', pk=pk)

    if request.method != 'POST':
        return render(request, 'courses/course_duplicate_confirm.html', {'course': course})

    new_year = int(request.POST.get('year', course.year))
    new_term = request.POST.get('term', course.term)
    new_code = f"{course.code}-{new_year}{new_term or ''}"[:20]

    new_course = Course.objects.create(
        title=f"{course.title} (copy)",
        code=new_code,
        subject=course.subject,
        description=course.description,
        teacher=request.user,
        grade_level=course.grade_level,
        term=new_term,
        year=new_year,
        max_students=course.max_students,
        enrolment_type=course.enrolment_type,
        is_active=False,
    )

    lesson_map = {}
    quizzes = course.quizzes.prefetch_related('questions').order_by('-available_from')

    for module in course.modules.prefetch_related('lessons__files').order_by('order'):
        new_mod = Module.objects.create(
            course=new_course,
            title=module.title,
            description=module.description,
            order=module.order,
        )

        for lesson in module.lessons.order_by('order'):
            new_lesson = Lesson.objects.create(
                module=new_mod,
                title=lesson.title,
                content=lesson.content,
                video_url=lesson.video_url,
                order=lesson.order,
                duration_minutes=lesson.duration_minutes,
                attachments=lesson.attachments,
                is_published=False,
                release_at=lesson.release_at,
            )
            lesson_map[lesson.pk] = new_lesson

            for lesson_file in lesson.files.all():
                LessonFile.objects.create(
                    lesson=new_lesson,
                    file=lesson_file.file.name,
                    label=lesson_file.label,
                )

    for old_lesson_pk, new_lesson in lesson_map.items():
        old_lesson = Lesson.objects.get(pk=old_lesson_pk)
        if old_lesson.prerequisite_id:
            new_lesson.prerequisite = lesson_map.get(old_lesson.prerequisite_id)
            new_lesson.save(update_fields=['prerequisite'])

    for quiz in quizzes:
        new_quiz = Quiz.objects.create(
            course=new_course,
            title=quiz.title,
            description=quiz.description,
            time_limit_minutes=quiz.time_limit_minutes,
            total_points=quiz.total_points,
            available_from=quiz.available_from,
            available_until=quiz.available_until,
            allow_multiple_attempts=quiz.allow_multiple_attempts,
            max_attempts=quiz.max_attempts,
            show_correct_answers=quiz.show_correct_answers,
            shuffle_questions=quiz.shuffle_questions,
        )

        for question in quiz.questions.all():
            Question.objects.create(
                quiz=new_quiz,
                question_text=question.question_text,
                question_type=question.question_type,
                points=question.points,
                order=question.order,
                choices=question.choices,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
            )

    messages.success(request, f'Course duplicated as "{new_course.title}" (inactive draft).')
    return redirect('courses:update', pk=new_course.pk)


# ──────────────────────────────────────────────────────────────
# Module CRUD
# ──────────────────────────────────────────────────────────────

class ModuleCreateView(LoginRequiredMixin, CourseOwnerMixin, CreateView):
    model = Module
    form_class = ModuleForm
    template_name = 'courses/module_form.html'

    def get_course(self):
        return get_object_or_404(Course, pk=self.kwargs['course_pk'])

    def form_valid(self, form):
        form.instance.course = self.get_course()
        messages.success(self.request, 'Module created.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('courses:detail', kwargs={'pk': self.kwargs['course_pk']})


class ModuleUpdateView(LoginRequiredMixin, CourseOwnerMixin, UpdateView):
    model = Module
    form_class = ModuleForm
    template_name = 'courses/module_form.html'

    def get_course(self):
        return self.get_object().course

    def get_success_url(self):
        return reverse_lazy('courses:detail', kwargs={'pk': self.object.course.pk})


class ModuleDeleteView(LoginRequiredMixin, CourseOwnerMixin, DeleteView):
    model = Module
    template_name = 'courses/module_confirm_delete.html'

    def get_course(self):
        return self.get_object().course

    def get_success_url(self):
        return reverse_lazy('courses:detail', kwargs={'pk': self.object.course.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Module deleted.')
        return super().form_valid(form)


# ──────────────────────────────────────────────────────────────
# Lesson CRUD
# ──────────────────────────────────────────────────────────────

class LessonCreateView(LoginRequiredMixin, CourseOwnerMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'courses/lesson_form.html'

    def get_course(self):
        return get_object_or_404(Module, pk=self.kwargs['module_pk']).course

    def form_valid(self, form):
        module = get_object_or_404(Module, pk=self.kwargs['module_pk'])
        form.instance.module = module

        response = super().form_valid(form)

        if self.object.is_published:
            _notify_course_students(
                module.course,
                f'New lesson added in {module.course.title}: {self.object.title}',
                'announcement',
                link=reverse('courses:lesson_detail', kwargs={'pk': self.object.pk})
            )

        messages.success(self.request, 'Lesson created.')
        return response

    def get_success_url(self):
        return reverse_lazy('courses:detail', kwargs={'pk': self.object.module.course.pk})


class LessonUpdateView(LoginRequiredMixin, CourseOwnerMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'courses/lesson_form.html'

    def get_course(self):
        return self.get_object().module.course

    def get_success_url(self):
        return reverse_lazy('courses:lesson_detail', kwargs={'pk': self.object.pk})


class LessonDeleteView(LoginRequiredMixin, CourseOwnerMixin, DeleteView):
    model = Lesson
    template_name = 'courses/lesson_confirm_delete.html'

    def get_course(self):
        return self.get_object().module.course

    def get_success_url(self):
        return reverse_lazy('courses:detail', kwargs={'pk': self.object.module.course.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Lesson deleted.')
        return super().form_valid(form)


# ──────────────────────────────────────────────────────────────
# Lesson file attachments
# ──────────────────────────────────────────────────────────────

@login_required
def upload_lesson_file(request, lesson_pk):
    lesson = get_object_or_404(Lesson, pk=lesson_pk)
    course = lesson.module.course

    if not ((request.user.is_teacher and course.teacher == request.user)
            or request.user.is_school_admin):
        messages.error(request, 'Permission denied.')
        return redirect('courses:lesson_detail', pk=lesson_pk)

    if request.method == 'POST':
        form = LessonFileForm(request.POST, request.FILES)
        if form.is_valid():
            lf = form.save(commit=False)
            lf.lesson = lesson
            lf.save()
            messages.success(request, 'File uploaded.')
            return redirect('courses:lesson_detail', pk=lesson_pk)
    else:
        form = LessonFileForm()

    return render(request, 'courses/lesson_file_form.html', {
        'form': form,
        'lesson': lesson
    })


@login_required
@require_POST
def delete_lesson_file(request, pk):
    lf = get_object_or_404(LessonFile, pk=pk)
    course = lf.lesson.module.course

    if not ((request.user.is_teacher and course.teacher == request.user)
            or request.user.is_school_admin):
        messages.error(request, 'Permission denied.')
        return redirect('courses:lesson_detail', pk=lf.lesson.pk)

    lesson_pk = lf.lesson.pk
    lf.file.delete(save=False)
    lf.delete()
    messages.success(request, 'File deleted.')
    return redirect('courses:lesson_detail', pk=lesson_pk)


# ──────────────────────────────────────────────────────────────
# Certificates
# ──────────────────────────────────────────────────────────────

@login_required
def view_certificate(request, pk):
    cert = get_object_or_404(
        CourseCompletionCertificate,
        pk=pk,
        student=request.user
    )
    return render(request, 'courses/certificate.html', {'cert': cert})


@login_required
def my_certificates(request):
    certs = CourseCompletionCertificate.objects.filter(
        student=request.user
    ).select_related('course')
    return render(request, 'courses/my_certificates.html', {'certs': certs})