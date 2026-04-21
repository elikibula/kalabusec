from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q
from .models import Announcement
from .forms import AnnouncementForm


class StaffRequiredMixin(UserPassesTestMixin):
    """Only teachers and admins can create/edit announcements."""
    def test_func(self):
        return self.request.user.is_teacher or self.request.user.is_school_admin


class AnnouncementListView(LoginRequiredMixin, ListView):
    model = Announcement
    template_name = 'announcements/announcement_list.html'
    context_object_name = 'announcements'
    paginate_by = 20

    def get_queryset(self):
        queryset = Announcement.objects.filter(
            is_published=True,
            published_date__lte=timezone.now()
        ).select_related('author', 'course')

        user = self.request.user
        if user.is_student:
            queryset = queryset.filter(
                Q(course__isnull=True) |
                Q(course__students=user)
            )
        return queryset.order_by('-is_pinned', '-published_date')


class AnnouncementDetailView(LoginRequiredMixin, DetailView):
    model = Announcement
    template_name = 'announcements/announcement_detail.html'
    context_object_name = 'announcement'

    def get_queryset(self):
        return Announcement.objects.filter(
            is_published=True,
            published_date__lte=timezone.now()
        ).select_related('author', 'course')


class AnnouncementCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'announcements/announcement_form.html'
    success_url = reverse_lazy('announcements:list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Pre-select course if ?course= param is in the URL
        course_pk = self.request.GET.get('course')
        if course_pk and 'course' in form.fields:
            form.fields['course'].initial = course_pk
        # Teachers only see their own courses in the dropdown
        if self.request.user.is_teacher and 'course' in form.fields:
            from courses.models import Course
            form.fields['course'].queryset = Course.objects.filter(
                teacher=self.request.user, is_active=True
            )
        return form

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, 'Announcement posted.')
        return super().form_valid(form)


class AnnouncementUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'announcements/announcement_form.html'
    success_url = reverse_lazy('announcements:list')

    def test_func(self):
        ann = self.get_object()
        user = self.request.user
        # Only the original author or an admin can edit
        return user.is_school_admin or ann.author == user

    def form_valid(self, form):
        messages.success(self.request, 'Announcement updated.')
        return super().form_valid(form)


class AnnouncementDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Announcement
    template_name = 'announcements/announcement_confirm_delete.html'
    success_url = reverse_lazy('announcements:list')

    def test_func(self):
        ann = self.get_object()
        user = self.request.user
        return user.is_school_admin or ann.author == user

    def form_valid(self, form):
        messages.success(self.request, 'Announcement deleted.')
        return super().form_valid(form)
