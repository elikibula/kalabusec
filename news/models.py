import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.conf import settings
from django.urls import reverse
from ckeditor_uploader.fields import RichTextUploadingField

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def total_news_count(self):
        from news.models import News, PhotoNews
        return News.objects.filter(category=self).count() + PhotoNews.objects.filter(category=self).count()

    def __str__(self):
        return self.name


class News(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)  
    content = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='news_images/', blank=True, null=True)
    video = models.FileField(upload_to='news_videos/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=False, blank=False)
    date_posted = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    

    def save(self, *args, **kwargs):
        if not self.slug:  # Auto-generate slug if not provided
            self.slug = slugify(self.title)
            # Ensure uniqueness
            while News.objects.filter(slug=self.slug).exists():
                self.slug = f"{slugify(self.title)}-{str(uuid.uuid4())[:4]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class PhotoNews(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='photo_news_covers/', null=True, blank=True)  # ✅ Add this
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_posted = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='photo_news_images/', null=True, blank=True)
    featured = models.BooleanField(default=False)  # <-- New field
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=False, blank=False, related_name='photo_news')

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('news:photo_news_detail', kwargs={'pk': self.pk})

class PhotoNewsImage(models.Model):
    photonews = models.ForeignKey(PhotoNews, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='photo_news_gallery/')
    

    def __str__(self):
        return f"Image for {self.photonews.title}"
    


