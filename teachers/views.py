"""
Teacher-facing views.

This module contains all views for teacher functionality including:
- Teacher dashboard
- Question and test management
- Grading and analytics
- Study materials management

All views require teacher authentication.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from functools import wraps

# Import existing views from accounts and questions apps
from accounts.views import teacher_dashboard as _dashboard, teacher_reports as _reports
from questions.views import (
    questions_list as _question_list,
    add_question as _add_question,
    edit_question as _edit_question,
    delete_question as _delete_question,
    tests_list as _test_list,
    add_test as _create_test,
    edit_paper as _edit_test,
    paper_builder as _paper_builder,
    submissions_list as _submission_list,
    grade_submission as _grade_submission,
    export_performance_csv as _export_performance,
    teacher_materials as _teacher_materials,
    upload_material as _upload_material,
    delete_material as _delete_material,
)


def teacher_required(view_func):
    """Decorator to ensure only teachers can access a view."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'user_type') or request.user.user_type != 2:  # Teacher
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return wrapper


# Dashboard
@teacher_required
def dashboard(request):
    """Teacher dashboard with overview and analytics."""
    return _dashboard(request)


# Question Management
@teacher_required
def question_list(request):
    """List all questions created by teacher."""
    return _question_list(request)


@teacher_required
def add_question(request):
    """Create new question."""
    return _add_question(request)


@teacher_required
def edit_question(request, question_id):
    """Edit existing question."""
    return _edit_question(request, question_id)


@teacher_required
def delete_question(request, question_id):
    """Delete question."""
    return _delete_question(request, question_id)


@teacher_required
def bulk_upload_questions(request):
    """Bulk upload questions via CSV/JSON."""
    return _add_question(request)  # Same view handles file upload


# Test Management
@teacher_required
def test_list(request):
    """List all tests created by teacher."""
    return _test_list(request)


@teacher_required
def create_test(request):
    """Create new test."""
    return _create_test(request)


@teacher_required
def edit_test(request, test_id):
    """Edit existing test."""
    return _edit_test(request, test_id)


@teacher_required
def delete_test(request, test_id):
    """Delete test."""
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    from exams.models import Test
    
    # Get test and verify ownership
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    if request.method == 'POST':
        test_title = test.title
        test.delete()
        messages.success(request, f'Test "{test_title}" has been deleted successfully.')
    else:
        messages.warning(request, 'Invalid request method.')
    
    return redirect('teachers:test_list')


@teacher_required
def paper_builder(request, test_id):
    """Build test paper by selecting questions."""
    # This redirects to edit_test which allows adding questions
    return redirect('teachers:edit_test', test_id=test_id)


@login_required
def preview_test(request, test_id):
    """Preview test before publishing - accessible by teachers and admins."""
    from django.shortcuts import get_object_or_404, render
    from exams.models import Test
    
    # Allow both teachers (type 2) and admins (type 1)
    if request.user.user_type not in [1, 2]:
        return redirect('home')
    
    test = get_object_or_404(Test, id=test_id)
    
    # Get all test questions with their details
    test_questions = test.testquestion_set.select_related('question').order_by('order')
    
    # Pass base_template based on user type
    base_template = 'dashboards/admin_base.html' if request.user.user_type == 1 else 'dashboards/teacher_base.html'
    
    return render(request, 'teachers/preview_test.html', {
        'test': test,
        'test_questions': test_questions,
        'base_template': base_template,
    })


# Grading
@teacher_required
def submission_list(request):
    """List all submissions requiring grading."""
    return _submission_list(request)


@teacher_required
def grade_submission(request, submission_id):
    """Grade individual submission."""
    return _grade_submission(request, submission_id)


@teacher_required
def test_analytics(request, test_id):
    """View test analytics and statistics."""
    from django.shortcuts import get_object_or_404, render
    from django.db.models import Avg, Count, Max, Min, Q
    from exams.models import Test, TestAttempt
    
    # Get test and verify ownership
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    # Get all submitted attempts
    attempts = TestAttempt.objects.select_related('student', 'test').filter(test=test, is_submitted=True)
    
    # Calculate statistics
    stats = attempts.aggregate(
        total_attempts=Count('id'),
        avg_score=Avg('total_score'),
        max_score=Max('total_score'),
        min_score=Min('total_score'),
        total_students=Count('student', distinct=True)
    )
    
    # Get per-student results
    student_results = attempts.values(
        'student__username', 'student__email'
    ).annotate(
        attempts_count=Count('id'),
        best_score=Max('total_score'),
        avg_score=Avg('total_score')
    ).order_by('-best_score')
    
    # Get question-level analytics
    from exams.models import TestAnswer
    question_stats = TestAnswer.objects.select_related('attempt', 'question').filter(
        attempt__test=test, attempt__is_submitted=True
    ).values(
        'question__id', 'question__question_text', 'question__type'
    ).annotate(
        total_answers=Count('id'),
        avg_score=Avg('score'),
        correct_count=Count('id', filter=Q(score__isnull=False))
    )
    
    return render(request, 'teachers/test_analytics.html', {
        'test': test,
        'stats': stats,
        'student_results': student_results,
        'question_stats': question_stats,
    })


# Reports
@teacher_required
def reports(request):
    """View comprehensive teacher reports."""
    return _reports(request)


@teacher_required
def export_performance(request):
    """Export performance data as CSV."""
    return _export_performance(request)


# Study Materials
@teacher_required
def manage_materials(request):
    """Manage study materials."""
    return _teacher_materials(request)


@teacher_required
def upload_material(request):
    """Upload new study material."""
    return _upload_material(request)


@teacher_required
def delete_material(request, material_id):
    """Delete study material."""
    return _delete_material(request, material_id)
