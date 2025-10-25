from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
     register_view, login_view, logout_view,
    student_dashboard, teacher_dashboard, admin_dashboard,
    admin_users, admin_create_user, admin_delete_user, admin_activity,
    teacher_reports,
    dashboard_home,
    verify_email,
    resend_verification,
)



 
urlpatterns = [
    path('register/', register_view, name='register'),  
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    # Email verification
    path('verify-email/<uidb64>/<token>/', verify_email, name='verify_email'),
    path('resend-verification/', resend_verification, name='resend_verification'),
    path('dashboard/student/', student_dashboard, name='student_dashboard'),
    path('dashboard/teacher/', teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/', dashboard_home, name='dashboard_home'),
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    # Admin management
    path('admin/users/', admin_users, name='admin_users'),
    path('admin/users/create/', admin_create_user, name='admin_create_user'),
    path('admin/users/delete/<int:id>/', admin_delete_user, name='admin_delete_user'),
    path('admin/activity/', admin_activity, name='admin_activity'),
    # Teacher reports
    path('teacher/reports/', teacher_reports, name='teacher_reports'),

    # Password reset
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='authentication/password_reset_form.html',
             email_template_name='authentication/password_reset_email.html',
             subject_template_name='authentication/password_reset_subject.txt',
             success_url='/auth/password-reset/done/'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='authentication/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='authentication/password_reset_confirm.html',
             success_url='/auth/reset/done/'
         ),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='authentication/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]