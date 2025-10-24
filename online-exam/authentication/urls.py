from django.urls import path
from .views import (
     register_view, login_view, logout_view,
    student_dashboard, teacher_dashboard, admin_dashboard,
    admin_users, admin_create_user, admin_delete_user, admin_activity,
    teacher_reports,
    dashboard_home,
)



 
urlpatterns = [
    path('register/', register_view, name='register'),  
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
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
]