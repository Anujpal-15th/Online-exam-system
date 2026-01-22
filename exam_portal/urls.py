"""
Main URL Configuration for Exam Portal.

Professional online examination system with role-based access control.

URL Structure:
    /                   - Home page
    /auth/              - Authentication & admin functionality (login, register, admin dashboard)
    /students/          - All student functionality
    /teachers/          - All teacher functionality  
    /questions/         - Question management & test operations
    /admin/             - Django admin panel
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Home
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    
    # Django Admin Panel
    path('admin/', admin.site.urls),
    
    # Authentication & Account Management
    path('auth/', include('accounts.urls')),
    
    # Role-Based Access
    path('students/', include('students.urls')),
    path('teachers/', include('teachers.urls')),
    
    # Question and Test Management
    path('questions/', include('questions.urls')),
]

# Serve media files in development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT if settings.STATIC_ROOT else settings.BASE_DIR / 'static')
