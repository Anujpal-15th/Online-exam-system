"""
URL configuration for Students module.

All student-facing URLs are organized here.
"""

from django.urls import path
from . import views
from . import analytics_views

app_name = 'students'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Exams
    path('exams/', views.all_exams, name='all_exams'),
    path('exams/upcoming/', views.upcoming_exams, name='upcoming_exams'),
    path('exams/attempted/', views.attempted_exams, name='attempted_exams'),
    path('exams/pyqs/', views.pyqs, name='pyqs'),
    path('exams/<int:test_id>/start/', views.start_exam, name='start_exam'),
    path('exams/attempt/<int:attempt_id>/submit/', views.submit_exam, name='submit_exam'),
    path('exams/attempt/<int:attempt_id>/review/', views.review_exam, name='review_exam'),
    
    # AJAX endpoints for exam taking
    path('api/save-answer/', views.auto_save_answer, name='auto_save_answer'),
    path('api/mark-question/', views.mark_for_review, name='mark_for_review'),
    
    # Results and Performance
    path('results/', views.results, name='results'),
    path('results/<int:attempt_id>/download/', views.download_result, name='download_result'),
    path('results/cumulative/download/', views.download_cumulative_report, name='download_cumulative'),
    
    # Analytics Dashboard
    path('analytics/', analytics_views.student_analytics, name='analytics'),
    path('api/analytics/chart-data/', analytics_views.analytics_chart_data, name='analytics_chart_data'),
    
    # Resources
    path('materials/', views.study_materials, name='study_materials'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('certificates/', views.certificates, name='certificates'),
    
    # Support
    path('help/', views.help_support, name='help'),
    path('help/<int:request_id>/delete/', views.delete_help_request, name='delete_help_request'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
]
