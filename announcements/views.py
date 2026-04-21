from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .models import Announcement
from .forms import AnnouncementForm


def _display_name(user):
    full_name = user.get_full_name() if hasattr(user, 'get_full_name') else ''
    return full_name.strip() or getattr(user, 'username', 'A user')


def _notify(user, message, notif_type='announcement', link=''):
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
    students = course.students.all()
    for student in students:
        _notify(student, message, notif_type, link=link)


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_teacher or self.request.user.is_school_admin


class AnnouncementListView(LoginRequiredMixin, ListView):
    model = Announcement
    template_name = 'announcements/announcement_list.html'
    context_object_name = 'announcements'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Announcement.objects.filter(is_published=True).select_related('course', 'author')

        if user.is_student:
            qs = qs.filter(course__students=user)

        elif user.is_teacher:
            qs = qs.filter(course__teacher=user)

        elif user.is_school_admin:
            qs = Announcement.objects.select_related('course', 'author')

        return qs.order_by('-is_pinned', '-published_date')


class AnnouncementDetailView(LoginRequiredMixin, DetailView):
    model = Announcement
    template_name = 'announcements/announcement_detail.html'
    context_object_name = 'announcement'

    def get_queryset(self):
        user = self.request.user
        qs = Announcement.objects.select_related('course', 'author')

        if user.is_school_admin:
            return qs

        if user.is_teacher:
            return qs.filter(course__teacher=user)

        if user.is_student:
            return qs.filter(is_published=True, course__students=user)

        return qs.none()


class AnnouncementCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'announcements/announcement_form.html'
    success_url = reverse_lazy('announcements:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        course_id = self.request.GET.get('course')
        if course_id:
            initial['course'] = course_id
        return initial

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        announcement = self.object
        detail_link = reverse('announcements:detail', kwargs={'pk': announcement.pk})

        # Notify creator
        _notify(
            self.request.user,
            f'Announcement "{announcement.title}" created successfully.',
            'announcement',
            link=detail_link
        )

        # Only send audience notifications if published
        if announcement.is_published:
            if announcement.course:
                _notify_course_students(
                    announcement.course,
                    f'New announcement in {announcement.course.title}: {announcement.title}',
                    'announcement',
                    link=detail_link
                )

                if self.request.user.is_school_admin and announcement.course.teacher:
                    _notify(
                        announcement.course.teacher,
                        f'{_display_name(self.request.user)} posted a new announcement in {announcement.course.title}: {announcement.title}',
                        'announcement',
                        link=detail_link
                    )
            else:
                # School-wide announcement
                # Optional: add school-wide recipient logic later if desired
                pass

        messages.success(self.request, 'Announcement created successfully!')
        return response


class AnnouncementUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'announcements/announcement_form.html'
    success_url = reverse_lazy('announcements:list')

    def get_queryset(self):
        qs = Announcement.objects.all()
        if self.request.user.is_school_admin:
            return qs
        return qs.filter(author=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        announcement = self.object
        detail_link = reverse('announcements:detail', kwargs={'pk': announcement.pk})

        _notify(
            self.request.user,
            f'Announcement "{announcement.title}" updated successfully.',
            'announcement',
            link=detail_link
        )

        if announcement.is_published:
            if announcement.course:
                _notify_course_students(
                    announcement.course,
                    f'Announcement updated in {announcement.course.title}: {announcement.title}',
                    'announcement',
                    link=detail_link
                )

        messages.success(self.request, 'Announcement updated successfully!')
        return response


class AnnouncementDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Announcement
    template_name = 'announcements/announcement_confirm_delete.html'
    success_url = reverse_lazy('announcements:list')

    def get_queryset(self):
        qs = Announcement.objects.all()
        if self.request.user.is_school_admin:
            return qs
        return qs.filter(author=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Announcement deleted successfully!')
        return super().form_valid(form)