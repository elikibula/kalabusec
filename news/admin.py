from django.contrib import admin
from .models import News, Category, PhotoNews, PhotoNewsImage


class PhotoNewsImageInline(admin.TabularInline):
    model = PhotoNewsImage
    extra = 1  # Number of empty image fields displayed

@admin.register(PhotoNews)
class PhotoNewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'date_posted', 'featured')
    list_filter = ('featured', 'date_posted')
    search_fields = ('title', 'author__username')
    inlines = [PhotoNewsImageInline]

@admin.register(PhotoNewsImage)
class PhotoNewsImageAdmin(admin.ModelAdmin):
    list_display = ('photonews', 'image')

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}  # Auto-generate slug in admin
    list_display = ('title', 'slug', 'author', 'category', 'is_featured', 'date_posted')
    list_filter = ('category', 'is_featured')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}  # Auto-generate slug from name

