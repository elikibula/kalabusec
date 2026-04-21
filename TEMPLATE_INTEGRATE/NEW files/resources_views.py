from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, F
from .models import Resource, ResourceCategory
from .forms import ResourceForm


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

        if search := self.request.GET.get('search'):
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        if cat := self.request.GET.get('category'):
            queryset = queryset.filter(category_id=cat)
        if rt := self.request.GET.get('type'):
            queryset = queryset.filter(resource_type=rt)
        if subj := self.request.GET.get('subject'):
            queryset = queryset.filter(subject_id=subj)

        return queryset.select_related(
            'category', 'subject', 'uploaded_by'
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = ResourceCategory.objects.all()
        ctx['resource_types'] = Resource.RESOURCE_TYPES
        return ctx


class ResourceDetailView(LoginRequiredMixin, DetailView):
    model = Resource
    template_name = 'resources/resource_detail.html'
    context_object_name = 'resource'

    def get_queryset(self):
        user = self.request.user
        if user.is_student or user.is_parent:
            return Resource.objects.filter(is_public=True)
        return Resource.objects.all()

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if 'download' in request.GET:
            self.object.increment_downloads()
        return response


class ResourceCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Resource
    form_class = ResourceForm
    template_name = 'resources/resource_form.html'
    success_url = reverse_lazy('resources:list')

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        if form.instance.file:
            form.instance.file_size = form.instance.file.size
        messages.success(self.request, 'Resource uploaded.')
        return super().form_valid(form)


class ResourceUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Resource
    form_class = ResourceForm
    template_name = 'resources/resource_form.html'
    success_url = reverse_lazy('resources:list')

    def test_func(self):
        user = self.request.user
        return user.is_school_admin or self.get_object().uploaded_by == user

    def form_valid(self, form):
        messages.success(self.request, 'Resource updated.')
        return super().form_valid(form)


class ResourceDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Resource
    template_name = 'resources/resource_confirm_delete.html'
    success_url = reverse_lazy('resources:list')

    def test_func(self):
        user = self.request.user
        return user.is_school_admin or self.get_object().uploaded_by == user

    def form_valid(self, form):
        obj = self.get_object()
        if obj.file:
            obj.file.delete(save=False)
        messages.success(self.request, 'Resource deleted.')
        return super().form_valid(form)
