from django.shortcuts import get_object_or_404, redirect, render
from datetime import datetime
from news.models import News, PhotoNews
from itertools import chain
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import AboutPage, TimelineEvent, Department, StaffMember, HistoricalImage
from .forms import ( AboutPageForm, TimelineEventForm, DepartmentForm, StaffMemberForm, HistoricalImageForm, ContactForm )
from django.core.mail import send_mail



def home(request):
    # Featured items
    featured_news = (
        News.objects.filter(is_featured=True)
        .select_related('author', 'category')
        .order_by('-date_posted')[:3]
    )
    featured_photo_news = PhotoNews.objects.filter(featured=True).order_by('-date_posted')[:3]

    # Recent news (combine articles and photo news)
    article_news = News.objects.all().order_by('-date_posted')[:10]
    photo_news = PhotoNews.objects.all().order_by('-date_posted')[:10]
    combined_recent_news = list(chain(article_news, photo_news))
    combined_recent_news.sort(key=lambda x: x.date_posted, reverse=True)
    recent_news = combined_recent_news[:6]     

    context = {
        'featured_news': featured_news,
        'featured_photo_news': featured_photo_news,
        'latest_news': recent_news,
        
    }

    return render(request, "home.html", context)



def your_view(request):
    current_year = datetime.now().year
    next_year = current_year + 1

    return render(request, 'your_template.html', {
        'current_year': current_year,
        'next_year': next_year,
    })




def about_us(request):
    about_page = AboutPage.objects.first()
    departments = Department.objects.prefetch_related('staff_members').all()
    admins = StaffMember.objects.filter(staff_type='admin').order_by('order', 'full_name')
    teachers = StaffMember.objects.filter(staff_type='teacher').select_related('department').order_by('department__order', 'order', 'full_name')

    context = {
        'about_page': about_page,
        'departments': departments,
        'admins': admins,
        'teachers': teachers,
    }
    return render(request, 'about/about_us.html', context)

#ABOUT US PAGE
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from .models import AboutPage, TimelineEvent, Department, StaffMember, HistoricalImage
from .forms import (
    AboutPageForm,
    TimelineEventForm,
    DepartmentForm,
    StaffMemberForm,
    HistoricalImageForm,
)


def is_admin_user(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


@login_required
@user_passes_test(is_admin_user)
def about_dashboard(request):
    about_page = AboutPage.objects.first()

    if not about_page:
        about_page = AboutPage.objects.create(
            school_name="Kalabu Secondary School",
            title="About Us",
            intro="Welcome to our school.",
            mission="Enter school mission here.",
            vision="Enter school vision here.",
            history_summary="Enter school history summary here.",
        )

    context = {
        'about_page': about_page,
        'timeline_events': about_page.timeline_events.all(),
        'departments': Department.objects.all(),
        'staff_members': StaffMember.objects.select_related('department').all(),
        'historical_images': about_page.historical_images.all(),

        # Blank forms for add modals
        'about_form': AboutPageForm(instance=about_page),
        'timeline_form': TimelineEventForm(),
        'department_form': DepartmentForm(),
        'staff_form': StaffMemberForm(),
        'historical_image_form': HistoricalImageForm(),
    }
    return render(request, 'dashboard/about/about_dashboard.html', context)


@login_required
@user_passes_test(is_admin_user)
def edit_about_page(request):
    about_page = AboutPage.objects.first()

    if request.method == 'POST':
        form = AboutPageForm(request.POST, request.FILES, instance=about_page)
        if form.is_valid():
            form.save()
            messages.success(request, "About page updated successfully.")
    return redirect('mainapp:about_dashboard')


@login_required
@user_passes_test(is_admin_user)
def add_timeline_event(request):
    about_page = AboutPage.objects.first()

    if request.method == 'POST':
        form = TimelineEventForm(request.POST, request.FILES)
        if form.is_valid():
            timeline = form.save(commit=False)
            timeline.about_page = about_page
            timeline.save()
            messages.success(request, "Timeline event added successfully.")
    return redirect('mainapp:about_dashboard')


@login_required
@user_passes_test(is_admin_user)
def edit_timeline_event(request, pk):
    event = get_object_or_404(TimelineEvent, pk=pk)

    if request.method == 'POST':
        form = TimelineEventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Timeline event updated successfully.")
    return redirect('mainapp:about_dashboard')


@login_required
@user_passes_test(is_admin_user)
def delete_timeline_event(request, pk):
    event = get_object_or_404(TimelineEvent, pk=pk)
    if request.method == 'POST':
        event.delete()
        messages.success(request, "Timeline event deleted successfully.")
    return redirect('mainapp:about_dashboard')


@login_required
@user_passes_test(is_admin_user)
def add_department(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department added successfully.")
    return redirect('mainapp:about_dashboard')


@login_required
@user_passes_test(is_admin_user)
def edit_department(request, pk):
    department = get_object_or_404(Department, pk=pk)

    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated successfully.")
    return redirect('mainapp:about_dashboard')


@login_required
@user_passes_test(is_admin_user)
def delete_department(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        department.delete()
        messages.success(request, "Department deleted successfully.")
    return redirect('mainapp:about_dashboard')


@login_required
@user_passes_test(is_admin_user)
def add_staff_member(request):
    if request.method == 'POST':
        form = StaffMemberForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff member added successfully.")
    return redirect('mainapp:about_dashboard')


@login_required
@user_passes_test(is_admin_user)
def edit_staff_member(request, pk):
    staff = get_object_or_404(StaffMember, pk=pk)

    if request.method == 'POST':
        form = StaffMemberForm(request.POST, request.FILES, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff member updated successfully.")
    return redirect('mainapp:about_dashboard')


@login_required
@user_passes_test(is_admin_user)
def delete_staff_member(request, pk):
    staff = get_object_or_404(StaffMember, pk=pk)
    if request.method == 'POST':
        staff.delete()
        messages.success(request, "Staff member deleted successfully.")
    return redirect('mainapp:about_dashboard')


@login_required
@user_passes_test(is_admin_user)
def add_historical_image(request):
    about_page = AboutPage.objects.first()

    if request.method == 'POST':
        form = HistoricalImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.about_page = about_page
            image.save()
            messages.success(request, "Historical image added successfully.")
    return redirect('mainapp:about_dashboard')


@login_required
@user_passes_test(is_admin_user)
def edit_historical_image(request, pk):
    image = get_object_or_404(HistoricalImage, pk=pk)

    if request.method == 'POST':
        form = HistoricalImageForm(request.POST, request.FILES, instance=image)
        if form.is_valid():
            form.save()
            messages.success(request, "Historical image updated successfully.")
    return redirect('mainapp:about_dashboard')


@login_required
@user_passes_test(is_admin_user)
def delete_historical_image(request, pk):
    image = get_object_or_404(HistoricalImage, pk=pk)
    if request.method == 'POST':
        image.delete()
        messages.success(request, "Historical image deleted successfully.")
    return redirect('mainapp:about_dashboard')


#CONTACT US
def contact_us(request):
    form = ContactForm()

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            full_message = f"""
            New Contact Message from Website

            Name: {name}
            Email: {email}
            Subject: {subject}

            Message:
            {message}
            """

            send_mail(
                subject,
                full_message,
                email,  # sender
                ['kalabusecondaryschool@yahoo.com'],  # receiver
                fail_silently=False,
            )

            messages.success(request, "Your message has been sent successfully!")
            return redirect('mainapp:contact_us')

    return render(request, 'contact/contact_us.html', {'form': form})