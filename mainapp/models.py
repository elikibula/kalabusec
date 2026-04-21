from django.db import models


class AboutPage(models.Model):
    school_name = models.CharField(max_length=200, default="Kalabu Secondary School")
    title = models.CharField(max_length=200, default="About Us")
    intro = models.TextField(help_text="Introductory paragraph about the school")
    mission = models.TextField()
    vision = models.TextField()
    history_summary = models.TextField(blank=True, null=True)
    hero_image = models.ImageField(upload_to='about/hero/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "About Page"
        verbose_name_plural = "About Page"

    def __str__(self):
        return self.school_name
    
    def save(self, *args, **kwargs):
        if not self.pk and AboutPage.objects.exists():
            raise ValueError("Only one AboutPage instance is allowed.")
        super().save(*args, **kwargs)


class TimelineEvent(models.Model):
    about_page = models.ForeignKey(
        AboutPage,
        on_delete=models.CASCADE,
        related_name='timeline_events'
    )
    year = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_image = models.ImageField(upload_to='about/timeline/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'year']

    def __str__(self):
        return f"{self.year} - {self.title}"


class Department(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class StaffMember(models.Model):
    STAFF_TYPE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
    )

    full_name = models.CharField(max_length=200)
    job_title = models.CharField(max_length=200)
    staff_type = models.CharField(max_length=20, choices=STAFF_TYPE_CHOICES)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='staff_members'
    )
    photo = models.ImageField(upload_to='about/staff/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['staff_type', 'order', 'full_name']

    def __str__(self):
        return self.full_name


class HistoricalImage(models.Model):
    about_page = models.ForeignKey(
        AboutPage,
        on_delete=models.CASCADE,
        related_name='historical_images'
    )
    title = models.CharField(max_length=200, blank=True, null=True)
    image = models.ImageField(upload_to='about/history/')
    caption = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title if self.title else f"Historical Image {self.pk}"