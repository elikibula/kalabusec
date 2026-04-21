import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Max, Min, Q
from django.utils import timezone

from courses.models import (
    Course, Enrollment, LessonCompletion, Lesson,
    CourseCompletionCertificate, Module
)
from assignments.models import Assignment, Submission, Quiz
from announcements.models import Announcement
from assignments.models import Quiz, QuizAttempt

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST

User = get_user_model()


@login_required
def users_configuration(request):
    if not request.user.is_school_admin:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard:home')

    search = request.GET.get('search', '').strip()
    role = request.GET.get('role', '').strip()
    status = request.GET.get('status', '').strip()

    users = User.objects.all().order_by('first_name', 'last_name', 'username')

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )

    if role == 'student':
        users = users.filter(is_student=True)
    elif role == 'teacher':
        users = users.filter(is_teacher=True)
    elif role == 'school_admin':
        users = users.filter(is_school_admin=True)

    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)

    context = {
        'users': users,
        'filter_search': search,
        'filter_role': role,
        'filter_status': status,
        'active_view_name': 'dashboard:users_configuration',
    }
    return render(request, 'dashboard/users_configuration.html', context)


@login_required
@require_POST
def toggle_user_status(request, user_id):
    if not request.user.is_school_admin:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('dashboard:home')

    user_obj = get_object_or_404(User, pk=user_id)

    if user_obj == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('dashboard:users_configuration')

    user_obj.is_active = not user_obj.is_active
    user_obj.save()

    if user_obj.is_active:
        messages.success(request, f"{user_obj.get_full_name() or user_obj.username} has been activated.")
    else:
        messages.success(request, f"{user_obj.get_full_name() or user_obj.username} has been deactivated.")

    return redirect('dashboard:users_configuration')


@login_required
@require_POST
def change_user_role(request, user_id):
    if not request.user.is_school_admin:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('dashboard:home')

    user_obj = get_object_or_404(User, pk=user_id)
    new_role = request.POST.get('role')

    if user_obj == request.user and new_role != 'school_admin':
        messages.error(request, "You cannot remove your own school admin role.")
        return redirect('dashboard:users_configuration')

    user_obj.is_student = False
    user_obj.is_teacher = False
    user_obj.is_school_admin = False

    if new_role == 'student':
        user_obj.is_student = True
    elif new_role == 'teacher':
        user_obj.is_teacher = True
    elif new_role == 'school_admin':
        user_obj.is_school_admin = True
    else:
        messages.error(request, "Invalid role selected.")
        return redirect('dashboard:users_configuration')

    user_obj.save()
    messages.success(request, f"{user_obj.get_full_name() or user_obj.username} role updated successfully.")
    return redirect('dashboard:users_configuration')

# ──────────────────────────────────────────────────────────────
# Shared helper
# ──────────────────────────────────────────────────────────────

def _unread_notifications(user):
    try:
        from notifications.models import Notification
        return Notification.objects.filter(recipient=user, is_read=False).count()
    except Exception:
        return 0


# ──────────────────────────────────────────────────────────────
# Main dashboard — role-branched
# ──────────────────────────────────────────────────────────────

@login_required
def home(request):
    user = request.user

    if user.is_teacher:
        return _teacher_classroom(request)
    if user.is_student:
        return _student_home(request)
    if user.is_school_admin:
        return _admin_home(request)

    # Fallback for parent or unknown roles
    context = {
        'recent_announcements': _recent_announcements(),
        'unread_notifications': _unread_notifications(user),
    }
    return render(request, 'dashboard/home.html', context)


# ──────────────────────────────────────────────────────────────
# Teacher — classroom view
# ──────────────────────────────────────────────────────────────

@login_required
def _teacher_classroom(request):
    """
    Classroom-style dashboard for teachers.
    Organised around the currently selected course so the teacher
    can create assignments and announcements without leaving the page.
    """
    user = request.user

    # All courses this teacher owns
    teaching_courses = (
        Course.objects
        .filter(teacher=user, is_active=True)
        .annotate(
            student_count=Count('students', distinct=True),
            assignment_count=Count('assignments', distinct=True),
        )
        .order_by('-created_at')
    )

    # ── Selected course (session-persisted) ──────────────────
    selected_pk = request.GET.get('course')

    if selected_pk:
        request.session['selected_course_id'] = selected_pk

    selected_course_id = request.session.get('selected_course_id')
    selected_course = None

    if selected_course_id:
        selected_course = teaching_courses.filter(pk=selected_course_id).first()

    # fallback to first available course
    if not selected_course and teaching_courses.exists():
        selected_course = teaching_courses.first()
        request.session['selected_course_id'] = selected_course.pk

    classroom_ctx = {}

    if selected_course:
        # ── Roster & enrolments ──────────────────────────────
        course_quizzes = (
            Quiz.objects
            .filter(course=selected_course)
            .prefetch_related('questions')
            .order_by('-created_at')
        )

        teacher_quizzes = (
            Quiz.objects
            .filter(course__teacher=user)
            .prefetch_related('questions')
            .order_by('-created_at')
        )

        active_enrollments = (
            Enrollment.objects
            .filter(course=selected_course, status='active')
            .select_related('student')
            .order_by('student__last_name', 'student__first_name')
        )

        pending_enrollments = (
            Enrollment.objects
            .filter(course=selected_course, status='pending')
            .select_related('student')
            .order_by('student__last_name', 'student__first_name')
        )

        # ── Per-student progress ─────────────────────────────
        total_lessons = Lesson.objects.filter(
            module__course=selected_course,
            is_published=True
        ).count()

        completion_map = {
            row['student_id']: row['cnt']
            for row in (
                LessonCompletion.objects
                .filter(lesson__module__course=selected_course)
                .values('student_id')
                .annotate(cnt=Count('id'))
            )
        }

        student_progress = [
            {
                'enrollment': enr,
                'completed': completion_map.get(enr.student_id, 0),
                'total': total_lessons,
                'pct': round(
                    (completion_map.get(enr.student_id, 0) / total_lessons * 100)
                    if total_lessons > 0 else 0,
                    1
                ),
            }
            for enr in active_enrollments
        ]

        # ── Assignments ──────────────────────────────────────
        assignments = (
            Assignment.objects
            .filter(course=selected_course)
            .annotate(
                submission_count=Count('submissions', distinct=True),
                graded_count=Count(
                    'submissions',
                    filter=Q(submissions__status='graded'),
                    distinct=True,
                ),
            )
            .order_by('-due_date')
        )

        pending_submissions = (
            Submission.objects
            .filter(assignment__course=selected_course, status='submitted')
            .select_related('student', 'assignment')
            .order_by('-submitted_at')[:15]
        )

        # ── Announcements ────────────────────────────────────
        course_announcements = (
            Announcement.objects
            .filter(course=selected_course)
            .select_related('author')
            .order_by('-published_date')[:5]
        )

        # ── Module / lesson overview ─────────────────────────
        modules = (
            selected_course.modules
            .prefetch_related('lessons')
            .order_by('order')
        )

        classroom_ctx = {
            'selected_course': selected_course,
            'active_enrollments': active_enrollments,
            'pending_enrollments': pending_enrollments,
            'student_progress': student_progress,
            'total_lessons': total_lessons,
            'assignments': assignments,
            'course_quizzes': course_quizzes,
            'quizzes': teacher_quizzes,
            'pending_submissions': pending_submissions,
            'course_announcements': course_announcements,
            'modules': modules,
        }

    # ── Cross-course stats (sidebar) ─────────────────────────
    all_pending_submissions = Submission.objects.filter(
        assignment__course__teacher=user,
        status='submitted'
    ).count()

    all_pending_enrolments = Enrollment.objects.filter(
        course__teacher=user,
        status='pending'
    ).count()

    context = {
        'teaching_courses': teaching_courses,
        'sidebar_teaching_courses': teaching_courses,
        'all_pending_submissions': all_pending_submissions,
        'all_pending_enrolments': all_pending_enrolments,
        'sidebar_pending_submissions': all_pending_submissions,
        'sidebar_pending_enrolments': all_pending_enrolments,
        'recent_announcements': _recent_announcements(),
        'unread_notifications': _unread_notifications(user),
        **classroom_ctx,
    }

    return render(request, 'dashboard/teacher_classroom.html', context)
    


# ──────────────────────────────────────────────────────────────
# Teacher — quick-create shortcuts
# These are lightweight POST-only views that live on the dashboard
# URL so the teacher never has to navigate away from their classroom.
# ──────────────────────────────────────────────────────────────

@login_required
def quick_create_assignment(request, course_pk):
    """
    Redirects to the full assignment create form pre-scoped to
    this course, preserving the classroom ?course= param on cancel.
    """
    course = get_object_or_404(Course, pk=course_pk, teacher=request.user)
    from django.urls import reverse
    url = reverse('assignments:create') + f'?course={course.pk}'
    return redirect(url)


@login_required
def quick_create_announcement(request, course_pk):
    """
    Redirects to the announcement create form pre-scoped to this course.
    """
    course = get_object_or_404(Course, pk=course_pk, teacher=request.user)
    from django.urls import reverse
    url = reverse('announcements:create') + f'?course={course.pk}'
    return redirect(url)


@login_required
def quick_create_module(request, course_pk):
    """Redirects to the module create form for this course."""
    course = get_object_or_404(Course, pk=course_pk, teacher=request.user)
    from django.urls import reverse
    return redirect(reverse('courses:module_create', kwargs={'course_pk': course.pk}))


# ──────────────────────────────────────────────────────────────
# Student home
# ──────────────────────────────────────────────────────────────

def _student_home(request):
    user = request.user

    enrolled_ids = Enrollment.objects.filter(
        student=user, status='active'
    ).values_list('course_id', flat=True)

    enrolled_courses = Course.objects.filter(
        id__in=enrolled_ids, is_active=True
    ).select_related('teacher', 'subject')

    lesson_totals = {
        row['module__course_id']: row['total']
        for row in Lesson.objects.filter(
            module__course__in=enrolled_courses,
            is_published=True
        ).values('module__course_id').annotate(total=Count('id'))
    }

    completion_counts = {
        row['lesson__module__course_id']: row['cnt']
        for row in LessonCompletion.objects.filter(
            student=user,
            lesson__module__course__in=enrolled_courses
        ).values('lesson__module__course_id').annotate(cnt=Count('id'))
    }

    progress_data = [{
        'course': c,
        'total': lesson_totals.get(c.pk, 0),
        'completed': completion_counts.get(c.pk, 0),
        'percentage': round(
            (completion_counts.get(c.pk, 0) / lesson_totals.get(c.pk, 1) * 100)
            if lesson_totals.get(c.pk, 0) > 0 else 0, 1
        ),
    } for c in enrolled_courses]

    now = timezone.now()

    # ====================== QUIZZES ======================
    upcoming_quizzes = (
        Quiz.objects.filter(
            course__in=enrolled_courses,
            available_from__lte=now,
            available_until__gte=now
        )
        .select_related('course')
        .order_by('available_until')[:5]
    )

    recent_attempts = (
        QuizAttempt.objects.filter(student=user)
        .select_related('quiz', 'quiz__course')
        .order_by('-submitted_at')[:5]
    )

    # ====================== CONTEXT ======================
    context = {
        'enrolled_courses': enrolled_courses[:6],

        # Assignments
        'upcoming_assignments': (
            Assignment.objects
            .filter(course__in=enrolled_courses, due_date__gte=now)
            .select_related('course')
            .order_by('due_date')[:5]
        ),

        # QUIZZES (NEW)
        'upcoming_quizzes': upcoming_quizzes,
        'recent_quiz_attempts': recent_attempts,

        # Submissions
        'recent_submissions': (
            Submission.objects.filter(student=user)
            .select_related('assignment', 'assignment__course')
            .order_by('-submitted_at')[:5]
        ),

        # Progress
        'progress_data': progress_data,

        # Certificates
        'certificates': (
            CourseCompletionCertificate.objects
            .filter(student=user)
            .select_related('course')[:3]
        ),

        # Enrollment + notifications
        'pending_enrollments': Enrollment.objects.filter(
            student=user, status='pending'
        ).select_related('course'),

        'recent_announcements': _recent_announcements(),
        'unread_notifications': _unread_notifications(user),
    }

    return render(request, 'dashboard/student_home.html', context)


# ──────────────────────────────────────────────────────────────
# Admin home
# ──────────────────────────────────────────────────────────────

def _admin_home(request):
    user = request.user
    context = {
        'total_courses': Course.objects.filter(is_active=True).count(),
        'total_students': user.__class__.objects.filter(role='student').count(),
        'total_teachers': user.__class__.objects.filter(role='teacher').count(),
        'recent_enrollments': Enrollment.objects.select_related(
            'student', 'course'
        ).order_by('-enrolled_at')[:10],
        'recent_announcements': _recent_announcements(),
        'unread_notifications': _unread_notifications(user),
    }
    return render(request, 'dashboard/admin_home.html', context)


# ──────────────────────────────────────────────────────────────
# Analytics
# ──────────────────────────────────────────────────────────────

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Max, Min, Q
from django.shortcuts import render
from django.utils import timezone

from courses.models import (
    Course,
    Enrollment,
    LessonCompletion,
    Lesson,
    CourseCompletionCertificate,
)
from assignments.models import Assignment, Submission, Quiz


@login_required
def analytics(request):
    user = request.user
    now = timezone.now()

    context = {
        'unread_notifications': _unread_notifications(user),
    }

    if user.is_student:
        enrollments = Enrollment.objects.filter(student=user).select_related('course')
        graded_enrollments = enrollments.exclude(final_grade__isnull=True)

        context.update(
            graded_enrollments.aggregate(
                average=Avg('final_grade'),
                highest=Max('final_grade'),
                lowest=Min('final_grade'),
            )
        )

        submissions = Submission.objects.filter(student=user).select_related('assignment', 'assignment__course')
        graded_submissions_qs = submissions.filter(status='graded')

        active_course_ids = enrollments.filter(status='active').values_list('course_id', flat=True)

        total_lessons = Lesson.objects.filter(
            module__course_id__in=active_course_ids,
            is_published=True
        ).count()

        completed_lessons = LessonCompletion.objects.filter(
            student=user,
            lesson__module__course_id__in=active_course_ids
        ).count()

        total_quizzes = Quiz.objects.filter(
            course_id__in=active_course_ids,
            available_from__lte=now
        ).count()

        available_quizzes = Quiz.objects.filter(
            course_id__in=active_course_ids,
            available_from__lte=now,
            available_until__gte=now
        ).count()

        certificates = CourseCompletionCertificate.objects.filter(
            student=user
        ).select_related('course')

        course_grade_breakdown = list(
            graded_enrollments.values(
                'course__title',
                'course__code',
                'final_grade'
            ).order_by('course__title')
        )

        context.update({
            'total_submissions': submissions.count(),
            'graded_submissions': graded_submissions_qs.count(),
            'submitted_submissions': submissions.filter(status='submitted').count(),
            'late_submissions': submissions.filter(status='late').count(),
            'completed_lessons': completed_lessons,
            'total_lessons': total_lessons,
            'lesson_completion_rate': round((completed_lessons / total_lessons * 100), 1) if total_lessons else 0,
            'certificates': certificates,
            'certificate_count': certificates.count(),
            'active_course_count': enrollments.filter(status='active').count(),
            'pending_course_count': enrollments.filter(status='pending').count(),
            'total_quizzes': total_quizzes,
            'available_quizzes': available_quizzes,
            'graded_submission_average': graded_submissions_qs.aggregate(avg=Avg('score'))['avg'] or 0,
            'course_grade_breakdown': course_grade_breakdown,

            # chart data
            'student_performance_labels_json': json.dumps(['Lowest', 'Average', 'Highest']),
            'student_performance_values_json': json.dumps([
                float(context.get('lowest') or 0),
                float(context.get('average') or 0),
                float(context.get('highest') or 0),
            ]),
            'student_progress_labels_json': json.dumps(['Completed Lessons', 'Remaining Lessons']),
            'student_progress_values_json': json.dumps([
                completed_lessons,
                max(total_lessons - completed_lessons, 0),
            ]),
            'student_course_grade_labels_json': json.dumps([row['course__title'] for row in course_grade_breakdown]),
            'student_course_grade_values_json': json.dumps([float(row['final_grade'] or 0) for row in course_grade_breakdown]),
        })

    elif user.is_teacher:
        courses = Course.objects.filter(teacher=user, is_active=True)

        submissions = Submission.objects.filter(
            assignment__course__teacher=user
        ).select_related('assignment', 'student', 'assignment__course')

        quizzes = Quiz.objects.filter(course__teacher=user)

        total_courses = courses.count()
        total_students = courses.aggregate(
            total=Count('students', distinct=True)
        )['total'] or 0
        total_assignments = Assignment.objects.filter(course__teacher=user).count()
        total_submissions = submissions.count()
        pending_grading = submissions.filter(status='submitted').count()
        graded_submissions = submissions.filter(status='graded').count()
        total_quizzes = quizzes.count()

        total_lessons = Lesson.objects.filter(
            module__course__teacher=user,
            is_published=True
        ).count()

        course_breakdown = list(
            courses.annotate(
                student_count=Count('students', distinct=True),
                assignment_count=Count('assignments', distinct=True),
                submission_count=Count('assignments__submissions', distinct=True),
                quiz_count=Count('quizzes', distinct=True),
                module_count=Count('modules', distinct=True),
            ).values(
                'id',
                'title',
                'code',
                'student_count',
                'assignment_count',
                'submission_count',
                'quiz_count',
                'module_count',
            ).order_by('title')
        )

        top_course_by_students = max(course_breakdown, key=lambda x: x['student_count'], default=None)
        top_course_by_submissions = max(course_breakdown, key=lambda x: x['submission_count'], default=None)

        grading_completion_rate = round((graded_submissions / total_submissions * 100), 1) if total_submissions else 0

        context.update({
            'total_courses': total_courses,
            'total_students': total_students,
            'total_assignments': total_assignments,
            'total_submissions': total_submissions,
            'pending_grading': pending_grading,
            'graded_submissions': graded_submissions,
            'total_quizzes': total_quizzes,
            'total_lessons': total_lessons,
            'average_students_per_course': round((total_students / total_courses), 1) if total_courses else 0,
            'average_assignments_per_course': round((total_assignments / total_courses), 1) if total_courses else 0,
            'grading_completion_rate': grading_completion_rate,
            'submission_rate': round((total_submissions / total_assignments), 1) if total_assignments else 0,
            'course_breakdown': course_breakdown,
            'top_course_by_students': top_course_by_students,
            'top_course_by_submissions': top_course_by_submissions,
            'recent_submissions_to_grade': submissions.filter(status='submitted').order_by('-submitted_at')[:8],

            # chart data
            'teacher_overview_labels_json': json.dumps(['Courses', 'Students', 'Assignments', 'Quizzes']),
            'teacher_overview_values_json': json.dumps([
                total_courses,
                total_students,
                total_assignments,
                total_quizzes,
            ]),
            'teacher_grading_labels_json': json.dumps(['Graded', 'Pending']),
            'teacher_grading_values_json': json.dumps([
                graded_submissions,
                pending_grading,
            ]),
            'teacher_course_labels_json': json.dumps([row['title'] for row in course_breakdown]),
            'teacher_course_students_json': json.dumps([row['student_count'] for row in course_breakdown]),
            'teacher_course_submissions_json': json.dumps([row['submission_count'] for row in course_breakdown]),
            'teacher_course_assignments_json': json.dumps([row['assignment_count'] for row in course_breakdown]),
        })

    elif user.is_school_admin:
        total_courses = Course.objects.filter(is_active=True).count()
        total_students = user.__class__.objects.filter(role='student').count()
        total_teachers = user.__class__.objects.filter(role='teacher').count()
        total_submissions = Submission.objects.count()
        pending_grading = Submission.objects.filter(status='submitted').count()
        total_assignments = Assignment.objects.count()
        total_quizzes = Quiz.objects.count()
        total_enrollments = Enrollment.objects.count()
        active_enrollments = Enrollment.objects.filter(status='active').count()
        pending_enrollments = Enrollment.objects.filter(status='pending').count()
        total_certificates = CourseCompletionCertificate.objects.count()

        system_completion_rate = round((active_enrollments / total_enrollments * 100), 1) if total_enrollments else 0

        recent_enrollment_activity = Enrollment.objects.select_related(
            'student', 'course'
        ).order_by('-enrolled_at')[:8]

        context.update({
            'total_courses': total_courses,
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_submissions': total_submissions,
            'pending_grading': pending_grading,
            'total_assignments': total_assignments,
            'total_quizzes': total_quizzes,
            'total_enrollments': total_enrollments,
            'active_enrollments': active_enrollments,
            'pending_enrollments': pending_enrollments,
            'total_certificates': total_certificates,
            'student_teacher_ratio': round((total_students / total_teachers), 1) if total_teachers else 0,
            'courses_per_teacher': round((total_courses / total_teachers), 1) if total_teachers else 0,
            'submissions_per_course': round((total_submissions / total_courses), 1) if total_courses else 0,
            'system_completion_rate': system_completion_rate,
            'role_distribution': {
                'students': total_students,
                'teachers': total_teachers,
            },
            'recent_enrollment_activity': recent_enrollment_activity,

            # chart data
            'admin_role_labels_json': json.dumps(['Students', 'Teachers']),
            'admin_role_values_json': json.dumps([total_students, total_teachers]),
            'admin_system_labels_json': json.dumps(['Courses', 'Assignments', 'Quizzes', 'Submissions']),
            'admin_system_values_json': json.dumps([
                total_courses,
                total_assignments,
                total_quizzes,
                total_submissions,
            ]),
            'admin_enrollment_labels_json': json.dumps(['Active', 'Pending']),
            'admin_enrollment_values_json': json.dumps([
                active_enrollments,
                pending_enrollments,
            ]),
        })

    return render(request, 'dashboard/analytics.html', context)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _recent_announcements():
    return (
        Announcement.objects
        .filter(is_published=True, published_date__lte=timezone.now())
        .select_related('author')
        .order_by('-published_date')[:5]
    )
