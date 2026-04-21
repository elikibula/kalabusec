from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Q, F
from django.urls import reverse_lazy, reverse
from .models import Resource, ResourceCategory
from .forms import ResourceForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
import os


@login_required
def download_resource(request, pk):
    resource = get_object_or_404(Resource, pk=pk)

    # Access control
    if (request.user.is_student or request.user.is_parent) and not resource.is_public:
        raise Http404("Resource not found.")

    if not resource.file:
        raise Http404("No file attached to this resource.")

    # Increment downloads atomically
    Resource.objects.filter(pk=resource.pk).update(
        download_count=F('download_count') + 1
    )

    filename = os.path.basename(resource.file.name)
    return FileResponse(
        resource.file.open('rb'),
        as_attachment=True,
        filename=filename
    )




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


def _notify_course_students(course, message, notif_type='announcement', link=''):
    students = course.students.all()
    for student in students:
        _notify(student, message, notif_type, link=link)


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_teacher or self.request.user.is_school_admin


class ResourceListView(LoginRequiredMixin, ListView):
    model = Resource
    template_name = 'resources/resource_list.html'
    context_object_name = 'resources'
    paginate_by = 24

    def get_queryset(self):
        user = self.request.user

        if user.is_student or user.is_parent:
            queryset = Resource.objects.filter(is_public=True)
        else:
            queryset = Resource.objects.all()

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        resource_type = self.request.GET.get('type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)

        subject = self.request.GET.get('subject')
        if subject:
            queryset = queryset.filter(subject_id=subject)

        course = self.request.GET.get('course')
        if course:
            queryset = queryset.filter(course_id=course)

        return queryset.select_related(
            'category', 'subject', 'course', 'uploaded_by'
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ResourceCategory.objects.all()
        context['resource_types'] = Resource.RESOURCE_TYPES
        context['filter_search'] = self.request.GET.get('search', '')
        context['filter_category'] = self.request.GET.get('category', '')
        context['filter_type'] = self.request.GET.get('type', '')
        context['filter_subject'] = self.request.GET.get('subject', '')
        context['filter_course'] = self.request.GET.get('course', '')
        return context


class ResourceDetailView(LoginRequiredMixin, DetailView):
    model = Resource
    template_name = 'resources/resource_detail.html'
    context_object_name = 'resource'

    def get_queryset(self):
        user = self.request.user
        if user.is_student or user.is_parent:
            return Resource.objects.filter(is_public=True)
        return Resource.objects.all()


class ResourceCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Resource
    form_class = ResourceForm
    template_name = 'resources/resource_form.html'
    success_url = reverse_lazy('resources:list')

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
        form.instance.uploaded_by = self.request.user

        if form.instance.file:
            form.instance.file_size = form.instance.file.size

        response = super().form_valid(form)
        resource = self.object

        _notify(
            self.request.user,
            f'Resource "{resource.title}" uploaded successfully.',
            'general',
            link=reverse('resources:detail', kwargs={'pk': resource.pk})
        )

        if resource.course and resource.is_public:
            _notify_course_students(
                resource.course,
                f'New resource added in {resource.course.title}: {resource.title}',
                'announcement',
                link=reverse('resources:detail', kwargs={'pk': resource.pk})
            )

            if self.request.user.is_school_admin and resource.course.teacher:
                _notify(
                    resource.course.teacher,
                    f'{_display_name(self.request.user)} uploaded a new resource to {resource.course.title}: {resource.title}',
                    'announcement',
                    link=reverse('resources:detail', kwargs={'pk': resource.pk})
                )

        messages.success(self.request, 'Resource uploaded successfully!')
        return response


class ResourceUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Resource
    form_class = ResourceForm
    template_name = 'resources/resource_form.html'
    success_url = reverse_lazy('resources:list')

    def get_queryset(self):
        qs = Resource.objects.all()
        if self.request.user.is_school_admin:
            return qs
        return qs.filter(uploaded_by=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if form.instance.file:
            form.instance.file_size = form.instance.file.size

        response = super().form_valid(form)
        resource = self.object

        _notify(
            self.request.user,
            f'Resource "{resource.title}" updated successfully.',
            'general',
            link=reverse('resources:detail', kwargs={'pk': resource.pk})
        )

        if resource.course and resource.is_public:
            _notify_course_students(
                resource.course,
                f'Resource updated in {resource.course.title}: {resource.title}',
                'announcement',
                link=reverse('resources:detail', kwargs={'pk': resource.pk})
            )

        messages.success(self.request, 'Resource updated successfully!')
        return response


class ResourceDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Resource
    template_name = 'resources/resource_confirm_delete.html'
    success_url = reverse_lazy('resources:list')

    def get_queryset(self):
        qs = Resource.objects.all()
        if self.request.user.is_school_admin:
            return qs
        return qs.filter(uploaded_by=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Resource deleted successfully!')
        return super().form_valid(form)