from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... your urls ...
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

app_name = 'news'

urlpatterns = [
    # ── Public list ──────────────────────────────
    path('',                                views.news_list,         name='news_list'),

    # ── Admin (must come BEFORE <slug> catch-all) ─
    path('admin/',                          views.news_admin,        name='news_admin'),
    path('admin/dashboard/',                views.news_dashboard,    name='news_dashboard'),
    path('admin/analytics/',                views.news_analytics,    name='news_analytics'),
    path('ckeditor/', include('ckeditor_uploader.urls')),

    # ── Auth: create/edit ────────────────────────
    path('create/',                         views.create_news,       name='news_create'),
    path('photo/create/',                   views.create_photo_news, name='photo_news_create'),
    path('photo/<int:pk>/edit/',            views.photo_news_update, name='photo_news_update'),
    path('photo/<int:pk>/delete/',          views.photo_news_delete, name='photo_news_delete'),
    path('photo/<int:pk>/',                 views.photo_news_detail, name='photo_news_detail'),
    path('photos/',                         views.photo_news_list,   name='photo_news_list'),

    # ── Category ─────────────────────────────────
    path('category/<slug:slug>/',           views.category_news,     name='category_news'),
    path('category/<int:pk>/<slug:slug>/',  views.category_view,     name='category_view'),

    # ── Slug catch-all (must be LAST) ────────────
    path('<int:pk>/edit/',                  views.update_news,       name='news_update_pk'),
    path('<slug:slug>/edit/',               views.update_news,       name='news_update'),
    path('<int:pk>/delete/',                views.delete_news,       name='news_delete'),
    path('<slug:slug>/',                    views.news_detail,       name='news_detail'),  
]

