"""
URL configuration for Accounts module.

Authentication, registration, and account management.
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    register_view, login_view, logout_view,
    teacher_dashboard, admin_dashboard,
    admin_users, admin_create_user, admin_delete_user, admin_block_user, admin_activity,
    admin_questions, admin_tests, admin_submissions,
    admin_help, admin_delete_question, admin_delete_test, admin_respond_help, admin_delete_help,
    teacher_reports,
    dashboard_home,
    profile_view,
    verify_email,
    resend_verification,
    teacher_notifications, admin_notifications,
    mark_teacher_notification_read, mark_admin_notification_read,
)

urlpatterns = [
    path('register/', register_view, name='register'),  
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    # Email verification
    path('verify-email/<uidb64>/<token>/', verify_email, name='verify_email'),
    path('resend-verification/', resend_verification, name='resend_verification'),
    # Profile
    path('profile/', profile_view, name='profile'),
    # Notifications
    path('teacher/notifications/', teacher_notifications, name='teacher_notifications'),
    path('teacher/notifications/mark-read/<int:notification_id>/', mark_teacher_notification_read, name='mark_teacher_notification_read'),
    path('admin/notifications/', admin_notifications, name='admin_notifications'),
    path('admin/notifications/mark-read/<int:notification_id>/', mark_admin_notification_read, name='mark_admin_notification_read'),
    # Dashboards
    path('dashboard/teacher/', teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/', dashboard_home, name='dashboard_home'),
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    # Admin management
    path('admin/users/', admin_users, name='admin_users'),
    path('admin/users/create/', admin_create_user, name='admin_create_user'),
    path('admin/users/delete/<int:id>/', admin_delete_user, name='admin_delete_user'),
    path('admin/users/block/<int:id>/', admin_block_user, name='admin_block_user'),
    path('admin/activity/', admin_activity, name='admin_activity'),
    path('admin/questions/', admin_questions, name='admin_questions'),
    path('admin/questions/delete/<int:id>/', admin_delete_question, name='admin_delete_question'),
    path('admin/tests/', admin_tests, name='admin_tests'),
    path('admin/tests/delete/<int:id>/', admin_delete_test, name='admin_delete_test'),
    path('admin/submissions/', admin_submissions, name='admin_submissions'),
    path('admin/help/', admin_help, name='admin_help'),
    path('admin/help/<int:id>/respond/', admin_respond_help, name='admin_respond_help'),
    path('admin/help/<int:id>/delete/', admin_delete_help, name='admin_delete_help'),
    # Teacher reports
    path('teacher/reports/', teacher_reports, name='teacher_reports'),
    # Password reset
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset_form.html',
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt',
             success_url='/auth/password-reset/done/'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url='/auth/reset/done/'
         ),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]
