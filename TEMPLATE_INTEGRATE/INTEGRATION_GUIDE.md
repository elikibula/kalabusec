# School LMS - Integration Guide: Step-by-Step Setup

## 🚀 Where to Start: Complete Integration Roadmap

Follow these steps **IN ORDER** to get your School LMS fully functional.

---

## PHASE 1: ACCOUNTS APP (Start Here!)

### Step 1: Verify Project Structure

Make sure your project structure looks like this:

```
school/  (your project root)
├── manage.py
├── school_project/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/
│   ├── __init__.py
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   ├── admin.py
│   └── apps.py
├── templates/
│   ├── base/
│   │   └── base.html
│   └── accounts/
│       ├── login.html
│       ├── register.html
│       ├── profile.html
│       └── profile_edit.html
└── static/
    ├── css/
    ├── js/
    └── images/
```

### Step 2: Configure Settings.py

Open `school_project/settings.py` and ensure these settings are correct:

```python
# CRITICAL: Custom User Model MUST be set BEFORE first migration
AUTH_USER_MODEL = 'accounts.User'

# Installed Apps - ORDER MATTERS!
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'crispy_forms',
    'crispy_tailwind',
    
    # Local apps - accounts MUST come first
    'accounts',         # ← MUST BE FIRST
    'courses',
    'assignments',
    'announcements',
    'resources',
    'dashboard',
]

# Templates configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # ← Point to templates folder
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # ← Required
                'django.contrib.auth.context_processors.auth',  # ← Required
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# Login URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

### Step 3: Update accounts/models.py

Make sure your User model has ALL fields (this is critical):

```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Custom user model with role-based access"""
    
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Administrator'),
        ('parent', 'Parent'),
    ]
    
    # Role and profile fields
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True)
    
    # Student specific fields
    student_id = models.CharField(max_length=20, blank=True, unique=True, null=True)
    grade_level = models.IntegerField(blank=True, null=True)
    
    # Teacher specific fields
    employee_id = models.CharField(max_length=20, blank=True, unique=True, null=True)
    department = models.CharField(max_length=100, blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # IMPORTANT: Fix for groups/permissions clash
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    
    class Meta:
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_teacher(self):
        return self.role == 'teacher'
    
    @property
    def is_school_admin(self):
        return self.role == 'admin'
```

### Step 4: Create accounts/urls.py

```python
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
]
```

### Step 5: Update Main URLs (school_project/urls.py)

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('', include('dashboard.urls', namespace='dashboard')),  # Will create next
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

### Step 6: Create Database

**IMPORTANT: If you've run migrations before, start fresh!**

```bash
# Delete old database
del db.sqlite3

# Delete ALL migration files (except __init__.py)
# In each app's migrations folder, delete:
# - 0001_initial.py
# - 0002_*.py
# - etc.
# BUT KEEP: __init__.py

# Windows PowerShell command to help:
Get-ChildItem -Path . -Recurse -Include "0*.py" | Where-Object { $_.Directory.Name -eq "migrations" } | Remove-Item -Force
```

### Step 7: Run Migrations

```bash
# Create migrations for accounts FIRST
python manage.py makemigrations accounts

# Check what was created
# Should show: Create model User

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
# Username: admin
# Email: admin@school.edu
# Password: (your choice)
```

### Step 8: Test Accounts App

```bash
# Start server
python manage.py runserver

# Test these URLs:
# http://127.0.0.1:8000/accounts/login/      ✅ Should show login page
# http://127.0.0.1:8000/accounts/register/   ✅ Should show registration
# http://127.0.0.1:8000/admin/               ✅ Should show admin panel
```

### Step 9: Create Test Users in Admin

1. Go to http://127.0.0.1:8000/admin
2. Login with your superuser account
3. Click "Users" under ACCOUNTS
4. Click "Add User"
5. Create a student:
   - Username: `student1`
   - Password: `student123` (or your choice)
   - Click "Save and continue editing"
   - Fill in:
     - First name: John
     - Last name: Doe
     - Email: student@school.edu
     - Role: **Student**
     - Student ID: STU001
     - Grade level: 10
   - Click "Save"

6. Create a teacher:
   - Username: `teacher1`
   - Password: `teacher123`
   - First name: Jane
   - Last name: Smith
   - Email: teacher@school.edu
   - Role: **Teacher**
   - Employee ID: EMP001
   - Department: Mathematics
   - Click "Save"

### Step 10: Test Login Flow

1. Logout from admin
2. Go to http://127.0.0.1:8000/accounts/login/
3. Login as `student1`
4. You should be redirected to dashboard (we'll create this next)

---

## PHASE 2: DASHBOARD APP

### Step 1: Create dashboard/urls.py

```python
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('analytics/', views.analytics, name='analytics'),
]
```

### Step 2: Verify dashboard/views.py exists

The views should already be created from the package I provided earlier.

### Step 3: Place Templates

Copy `dashboard/home.html` to `templates/dashboard/home.html`

### Step 4: Test Dashboard

```bash
# Restart server
python manage.py runserver

# Login and you should see the dashboard
# http://127.0.0.1:8000/
```

---

## PHASE 3: COURSES APP

### Step 1: Create Subjects First

In Django admin or shell:

```python
python manage.py shell
```

```python
from courses.models import Subject

Subject.objects.create(name='Mathematics', code='MATH', description='Mathematics courses')
Subject.objects.create(name='English', code='ENG', description='English Language and Literature')
Subject.objects.create(name='Science', code='SCI', description='Science courses')
Subject.objects.create(name='History', code='HIST', description='History courses')
Subject.objects.create(name='Computer Science', code='CS', description='Computer Science courses')

exit()
```

### Step 2: Create Migrations

```bash
python manage.py makemigrations courses
python manage.py migrate courses
```

### Step 3: Update URLs

Already in main urls.py:
```python
path('courses/', include('courses.urls', namespace='courses')),
```

### Step 4: Place Templates

Copy all course templates to `templates/courses/`

### Step 5: Create Test Course

1. Login as admin
2. Go to http://127.0.0.1:8000/admin
3. Add a Course:
   - Title: Introduction to Algebra
   - Code: MATH101
   - Subject: Mathematics
   - Teacher: teacher1
   - Grade level: 10
   - Semester: Fall
   - Year: 2025
   - Save

### Step 6: Test Courses

- http://127.0.0.1:8000/courses/ ✅ Course list
- http://127.0.0.1:8000/courses/1/ ✅ Course detail

---

## PHASE 4: ASSIGNMENTS APP

```bash
python manage.py makemigrations assignments
python manage.py migrate assignments
```

Update main urls.py:
```python
path('assignments/', include('assignments.urls', namespace='assignments')),
```

---

## PHASE 5: ANNOUNCEMENTS & RESOURCES

```bash
python manage.py makemigrations announcements
python manage.py migrate announcements

python manage.py makemigrations resources
python manage.py migrate resources
```

Update main urls.py:
```python
path('announcements/', include('announcements.urls', namespace='announcements')),
path('resources/', include('resources.urls', namespace='resources')),
```

---

## 🎯 QUICK START CHECKLIST

### Immediate Actions (Do This First!)

- [ ] **1. Verify settings.py** - Check AUTH_USER_MODEL, INSTALLED_APPS, TEMPLATES
- [ ] **2. Delete old database** - `del db.sqlite3`
- [ ] **3. Delete old migrations** - Keep only `__init__.py` files
- [ ] **4. Create accounts migrations** - `python manage.py makemigrations accounts`
- [ ] **5. Run migrations** - `python manage.py migrate`
- [ ] **6. Create superuser** - `python manage.py createsuperuser`
- [ ] **7. Place templates** - Extract templates to `templates/` folder
- [ ] **8. Update URLs** - Add accounts URLs to main urls.py
- [ ] **9. Test login** - Visit /accounts/login/
- [ ] **10. Create test users** - Via admin panel

### Order of App Integration

1. ✅ **Accounts** (Start here - foundation)
2. ✅ **Dashboard** (Simple, depends on accounts)
3. ✅ **Courses** (Core functionality)
4. ✅ **Assignments** (Depends on courses)
5. ✅ **Announcements** (Independent)
6. ✅ **Resources** (Independent)

---

## 🐛 Common Issues & Solutions

### Issue: "AUTH_USER_MODEL cannot be changed"
**Solution:** You ran migrations before setting AUTH_USER_MODEL. Must start fresh:
- Delete db.sqlite3
- Delete all migration files
- Set AUTH_USER_MODEL in settings
- Run migrations again

### Issue: "No such table: accounts_user"
**Solution:** Migrations not run. Run:
```bash
python manage.py migrate
```

### Issue: Template not found
**Solution:** Check TEMPLATES['DIRS'] points to templates folder

### Issue: "Cannot resolve keyword 'role'"
**Solution:** Database doesn't have role field. Delete DB and migrations, start fresh.

---

## 📞 Need Help?

If stuck at any step:
1. Check the error message carefully
2. Verify you followed steps in order
3. Make sure all files are in correct locations
4. Check Django documentation for specific errors

---

## ✅ Success Indicators

You'll know you're successful when:
- ✅ Login page loads without errors
- ✅ Can create users in admin
- ✅ Can login as different user roles
- ✅ Dashboard shows role-specific content
- ✅ No template errors
- ✅ All URLs resolve correctly

---

**Start with Phase 1 (Accounts) and work your way through each phase. Don't skip ahead!**
