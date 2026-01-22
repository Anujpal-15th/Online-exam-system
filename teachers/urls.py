"""
URL configuration for Teachers module.

All teacher-facing URLs are organized here.
"""

from django.urls import path
from . import views

app_name = 'teachers'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Question Management
    path('questions/', views.question_list, name='question_list'),
    path('questions/add/', views.add_question, name='add_question'),
    path('questions/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    path('questions/<int:question_id>/delete/', views.delete_question, name='delete_question'),
    path('questions/bulk-upload/', views.bulk_upload_questions, name='bulk_upload'),
    
    # Test Management
    path('tests/', views.test_list, name='test_list'),
    path('tests/create/', views.create_test, name='create_test'),
    path('tests/<int:test_id>/edit/', views.edit_test, name='edit_test'),
    path('tests/<int:test_id>/delete/', views.delete_test, name='delete_test'),
    path('tests/<int:test_id>/builder/', views.paper_builder, name='paper_builder'),
    path('tests/<int:test_id>/preview/', views.preview_test, name='preview_test'),
    
    # Grading and Results
    path('submissions/', views.submission_list, name='submission_list'),
    path('submissions/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),
    path('tests/<int:test_id>/analytics/', views.test_analytics, name='test_analytics'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/export/', views.export_performance, name='export_performance'),
    
    # Study Materials
    path('materials/', views.manage_materials, name='manage_materials'),
    path('materials/upload/', views.upload_material, name='upload_material'),
    path('materials/<int:material_id>/delete/', views.delete_material, name='delete_material'),
]
