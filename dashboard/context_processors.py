from django.db.models import Count
from django.urls import resolve
from django.utils import timezone

from courses.models import Course, Enrollment
from assignments.models import Assignment, Submission, Quiz


def active_nav(request):
    try:
        match = resolve(request.path_info)
        return {
            "active_url_name": match.url_name,
            "active_app_name": match.app_name,
            "active_view_name": f"{match.app_name}:{match.url_name}" if match.app_name else match.url_name,
        }
    except Exception:
        return {
            "active_url_name": "",
            "active_app_name": "",
            "active_view_name": "",
        }


def sidebar_data(request):
    user = request.user

    if not user.is_authenticated:
        return {}

    data = {}
    now = timezone.now()

    if getattr(user, "is_teacher", False):
        data.update({
            "sidebar_teaching_courses": Course.objects.filter(
                teacher=user, is_active=True
            ).annotate(student_count=Count("students", distinct=True)),
            "sidebar_pending_submissions": Submission.objects.filter(
                assignment__course__teacher=user,
                status="submitted"
            ).count(),
            "sidebar_pending_enrolments": Enrollment.objects.filter(
                course__teacher=user,
                status="pending"
            ).count(),
            "sidebar_teacher_quiz_count": Quiz.objects.filter(
                course__teacher=user
            ).count(),
        })

    elif getattr(user, "is_student", False):
        active_course_ids = Enrollment.objects.filter(
            student=user, status="active"
        ).values_list("course_id", flat=True)

        data.update({
            "sidebar_student_course_count": Course.objects.filter(
                id__in=active_course_ids, is_active=True
            ).count(),
            "sidebar_student_assignment_count": Assignment.objects.filter(
                course_id__in=active_course_ids,
                status="published",
                due_date__gte=now
            ).count(),
            "sidebar_student_quiz_count": Quiz.objects.filter(
                course_id__in=active_course_ids,
                available_from__lte=now,
                available_until__gte=now
            ).count(),
        })

    elif getattr(user, "is_school_admin", False):
        data.update({
            "sidebar_admin_course_count": Course.objects.filter(is_active=True).count(),
        })

    return data