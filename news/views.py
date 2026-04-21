from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
from itertools import chain
import uuid

from .models import News, Category, PhotoNews, PhotoNewsImage
from .forms import NewsForm, PhotoNewsForm


# ─────────────────────────────────────────────
# Permission helper
# ─────────────────────────────────────────────

def _is_news_admin(user):
    """True for superusers, school admins, staff, or teachers."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # Custom user model role field
    role = getattr(user, 'role', None)
    if role in ('admin', 'staff', 'teacher'):
        return True
    # Dashboard-style flags
    if getattr(user, 'is_school_admin', False):
        return True
    if getattr(user, 'is_teacher', False):
        return True
    return False


def admin_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not _is_news_admin(request.user):
            messages.error(request, "You don't have permission to access this page.")
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────
# News CRUD
# ─────────────────────────────────────────────

@login_required
def create_news(request):
    form = NewsForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        news = form.save(commit=False)
        news.author = request.user
        news.save()
        messages.success(request, f'"{news.title}" was created successfully.')
        return redirect('news:news_detail', slug=news.slug)
    return render(request, 'news/create_news.html', {'form': form})


@login_required
def update_news(request, pk=None, slug=None):
    if pk:
        news = get_object_or_404(News, pk=pk)
    elif slug:
        news = get_object_or_404(News, slug=slug)
    else:
        messages.error(request, "No news identifier provided.")
        return redirect('news:news_admin')

    form = NewsForm(request.POST or None, request.FILES or None, instance=news)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'"{news.title}" was updated successfully.')
        return redirect('news:news_admin')
    return render(request, 'news/news_form.html', {'form': form, 'news': news})

@login_required
def delete_news(request, pk=None, slug=None):
    if pk:
        news = get_object_or_404(News, pk=pk)
    elif slug:
        news = get_object_or_404(News, slug=slug)
    else:
        messages.error(request, "No news identifier provided.")
        return redirect('news:news_list')

    if request.method == 'POST':
        title = news.title
        news.delete()
        messages.success(request, f'"{title}" was deleted successfully.')
        return redirect('news:news_admin')

    return render(request, 'news/delete_news.html', {'news': news})


# ─────────────────────────────────────────────
# News detail & list
# ─────────────────────────────────────────────

def news_detail(request, slug):
    news = get_object_or_404(News, slug=slug)
    recent_news = News.objects.exclude(pk=news.pk).order_by('-date_posted')[:5]
    categories = Category.objects.all()
    for cat in categories:
        cat.total_count = (
            News.objects.filter(category=cat).count() +
            PhotoNews.objects.filter(category=cat).count()
        )
    return render(request, 'news/news_detail.html', {
        'news': news,
        'recent_news': recent_news,
        'categories': categories,
    })


def news_list(request):
    articles = News.objects.all()
    photos   = PhotoNews.objects.all()

    news_posts = sorted(
        chain(articles, photos),
        key=lambda x: x.date_posted,
        reverse=True
    )

    categories = Category.objects.all()
    for category in categories:
        category.news_count  = News.objects.filter(category=category).count()
        category.photo_count = PhotoNews.objects.filter(category=category).count()
        category.total_count = category.news_count + category.photo_count

    paginator = Paginator(news_posts, 12)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'news/news.html', {
        'page_obj':   page_obj,
        'news_list':  page_obj.object_list,
        'categories': categories,
    })


def category_news(request, slug):
    category = get_object_or_404(Category, slug=slug)
    combined = sorted(
        chain(
            News.objects.filter(category=category).order_by('-date_posted'),
            PhotoNews.objects.filter(category=category).order_by('-date_posted'),
        ),
        key=lambda x: x.date_posted,
        reverse=True
    )
    return render(request, 'news/category_news.html', {
        'category':  category,
        'news_list': combined,
    })


def category_view(request, pk, slug):
    category    = get_object_or_404(Category, pk=pk, slug=slug)
    articles    = News.objects.filter(category=category).order_by('-date_posted')
    galleries   = PhotoNews.objects.filter(category=category).order_by('-date_posted')
    recent_news = News.objects.exclude(category=category).order_by('-date_posted')[:5]

    categories = Category.objects.all()
    for cat in categories:
        cat.total_count = (
            News.objects.filter(category=cat).count() +
            PhotoNews.objects.filter(category=cat).count()
        )

    return render(request, 'news/category.html', {
        'category':   category,
        'articles':   articles,
        'galleries':  galleries,
        'recent_news': recent_news,
        'categories': categories,
    })


# ─────────────────────────────────────────────
# Photo News CRUD
# ─────────────────────────────────────────────

@login_required
def create_photo_news(request):
    form = PhotoNewsForm(request.POST or None, request.FILES or None)
    image_filename = None

    if request.method == 'POST':
        if request.FILES.get('cover_image'):
            image_filename = request.FILES['cover_image'].name

        if form.is_valid():
            photo_news = form.save(commit=False)
            photo_news.author = request.user
            cover = request.FILES.get('cover_image')
            if cover:
                photo_news.cover_image = cover
            photo_news.save()

            for img in request.FILES.getlist('image')[:20]:
                PhotoNewsImage.objects.create(photonews=photo_news, image=img)

            messages.success(request, f'"{photo_news.title}" was created successfully.')
            return redirect('news:photo_news_detail', pk=photo_news.pk)

    return render(request, 'news/create_photo_news.html', {
        'form':           form,
        'image_filename': image_filename,
    })


@login_required
def photo_news_update(request, pk):
    photo_news = get_object_or_404(PhotoNews, pk=pk)
    form = PhotoNewsForm(request.POST or None, request.FILES or None, instance=photo_news)

    image_filename = None
    if getattr(photo_news, 'cover_image', None):
        image_filename = photo_news.cover_image.name.split('/')[-1].split('\\')[-1]

    if request.method == 'POST' and form.is_valid():
        updated = form.save(commit=False)
        uploaded_cover = request.FILES.get('cover_image')
        if uploaded_cover:
            updated.cover_image = uploaded_cover
            image_filename = uploaded_cover.name
        updated.save()

        for img in request.FILES.getlist('images')[:20]:
            PhotoNewsImage.objects.create(photonews=updated, image=img)

        messages.success(request, f'"{updated.title}" was updated successfully.')
        return redirect('news:news_admin')

    return render(request, 'news/photo_news_form.html', {
        'form':           form,
        'photo_news':     photo_news,
        'image_filename': image_filename,
    })


@login_required
def photo_news_delete(request, pk):
    photo_news = get_object_or_404(PhotoNews, pk=pk)
    if request.method == 'POST':
        title = photo_news.title
        photo_news.delete()
        messages.success(request, f'"{title}" was deleted successfully.')
        return redirect('news:news_admin')
    return render(request, 'news/photo_news_confirm_delete.html', {'photo_news': photo_news})


# ─────────────────────────────────────────────
# Photo News detail & list
# ─────────────────────────────────────────────

def photo_news_detail(request, pk):
    try:
        photo_news = get_object_or_404(PhotoNews, pk=pk)
    except Exception:
        photo_news = get_object_or_404(News, pk=pk)

    description = (
        getattr(photo_news, 'description', None) or
        getattr(photo_news, 'content', '') or
        getattr(photo_news, 'caption', '')
    )

    categories = Category.objects.annotate(total_count=Count('news')).order_by('-total_count')[:20]

    recent_news = list(News.objects.order_by('-date_posted')[:6])
    try:
        recent_news += list(PhotoNews.objects.order_by('-date_posted')[:4])
    except Exception:
        pass

    seen, deduped = set(), []
    for item in recent_news:
        if item.pk in seen:
            continue
        seen.add(item.pk)
        if not getattr(item, 'image', None):
            item.image = getattr(item, 'cover_image', None) or getattr(item, 'thumbnail', None)
        deduped.append(item)
        if len(deduped) >= 6:
            break

    return render(request, 'news/photo_news_detail.html', {
        'photo_news':  photo_news,
        'description': description,
        'categories':  categories,
        'recent_news': deduped,
    })


@login_required
def photo_news_list(request):
    photos = PhotoNews.objects.all().order_by('-date_posted')
    return render(request, 'news/photo_news_list.html', {'photo_posts': photos})


# ─────────────────────────────────────────────
# Admin: combined news management
# ─────────────────────────────────────────────

@login_required
@admin_required
def news_admin(request):
    """
    Combined admin list for both News and PhotoNews.
    Supports search by title, author, or category.
    """
    news_qs  = News.objects.select_related('category', 'author').order_by('-date_posted')
    photo_qs = PhotoNews.objects.select_related('category', 'author').order_by('-date_posted')

    q = request.GET.get('q', '').strip()
    if q:
        news_qs = news_qs.filter(
            Q(title__icontains=q) |
            Q(author__username__icontains=q) |
            Q(category__name__icontains=q)
        )
        photo_qs = photo_qs.filter(
            Q(title__icontains=q) |
            Q(author__username__icontains=q) |
            Q(category__name__icontains=q)
        )

    # Annotate model type for template
    for obj in news_qs:
        obj.model_name = 'news'
    for obj in photo_qs:
        obj.model_name = 'photonews'

    combined = sorted(
        chain(news_qs, photo_qs),
        key=lambda x: x.date_posted,
        reverse=True
    )

    # Stats
    published_count = News.objects.filter(is_published=True).count()
    draft_count     = News.objects.filter(is_published=False).count()
    total_count     = News.objects.count() + PhotoNews.objects.count()

    paginator = Paginator(combined, 15)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'news/news_admin.html', {
        'news_list':       page_obj,
        'page_obj':        page_obj,
        'published_count': published_count,
        'draft_count':     draft_count,
        'total_count':     total_count,
        'search_query':    q,
        'categories':      Category.objects.all(),
    })


# ─────────────────────────────────────────────
# Admin: dashboard & analytics (kept from original)
# ─────────────────────────────────────────────

@login_required
@admin_required
def news_dashboard(request):
    one_week_ago = timezone.now() - timedelta(days=7)

    category_stats = []
    for category in Category.objects.all():
        news_count  = News.objects.filter(category=category).count()
        photo_count = PhotoNews.objects.filter(category=category).count()
        category_stats.append({
            'category':        category,
            'news_count':      news_count,
            'photo_news_count': photo_count,
            'total_count':     news_count + photo_count,
        })
    category_stats.sort(key=lambda x: x['total_count'], reverse=True)

    context = {
        'total_news':          News.objects.count(),
        'total_photo_news':    PhotoNews.objects.count(),
        'total_categories':    Category.objects.count(),
        'recent_news':         News.objects.filter(date_posted__gte=one_week_ago).count(),
        'recent_photo_news':   PhotoNews.objects.filter(date_posted__gte=one_week_ago).count(),
        'category_stats':      category_stats,
        'latest_news':         News.objects.order_by('-date_posted')[:5],
        'latest_photo_news':   PhotoNews.objects.order_by('-date_posted')[:5],
        'featured_news':       News.objects.filter(is_featured=True).count(),
        'articles_with_images': News.objects.exclude(image='').count(),
    }
    return render(request, 'news/dashboard.html', context)


@login_required
@admin_required
def news_analytics(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    today        = timezone.now().date()
    last_30_days = today - timedelta(days=30)

    recent_news_trend = (
        News.objects
        .filter(date_posted__date__gte=last_30_days)
        .extra({'date': "date(date_posted)"})
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    category_stats = []
    for category in Category.objects.all():
        news_count  = News.objects.filter(category=category).count()
        photo_count = PhotoNews.objects.filter(category=category).count()
        category_stats.append({
            'category':    category,
            'news_count':  news_count,
            'photo_count': photo_count,
            'total_count': news_count + photo_count,
        })
    category_stats.sort(key=lambda x: x['total_count'], reverse=True)

    active_authors = User.objects.annotate(
        news_count=Count('news'),
        photo_news_count=Count('photonews')
    ).filter(
        Q(news_count__gt=0) | Q(photo_news_count__gt=0)
    ).order_by('-news_count')[:10]

    context = {
        'recent_news_trend':    list(recent_news_trend),
        'category_stats':       category_stats,
        'active_authors':       active_authors,
        'last_30_days':         last_30_days,
        'total_news':           News.objects.count(),
        'total_photo_news':     PhotoNews.objects.count(),
        'featured_articles':    News.objects.filter(is_featured=True).count(),
        'articles_with_images': News.objects.exclude(image='').count(),
    }
    return render(request, 'news/analytics.html', context)