"""
Student-facing views.

This module contains all views for student functionality including:
- Student dashboard
- Exam taking interface
- Results viewing
- Study materials
- Support tickets

All views require student authentication.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from functools import wraps

# Import existing views from questions app (will be refactored later)
from questions.views import (
    student_dashboard as _student_dashboard,
    student_all_exams as _all_exams,
    student_upcoming_exams as _upcoming_exams,
    student_attempted_exams as _attempted_exams,
    student_pyqs as _pyqs,
    start_test as _start_exam,
    submit_test as _submit_exam,
    review_test as _review_exam,
    auto_save_answer as _auto_save_answer,
    mark_question_for_review as _mark_for_review,
    student_results as _results,
    download_result_report as _download_result,
    download_cumulative_report as _download_cumulative,
    student_materials as _study_materials,
    view_leaderboard as _leaderboard,
    view_certificates as _certificates,
    student_notifications as _notifications,
    mark_notification_read as _mark_notification_read,
)


def student_required(view_func):
    """Decorator to ensure only students can access a view."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'user_type') or request.user.user_type != 3:  # Student
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return wrapper


# Dashboard
@student_required
def dashboard(request):
    """Student dashboard with overview, stats, and quick actions."""
    return _student_dashboard(request)


# Exams
@student_required
def all_exams(request):
    """List all available exams."""
    return _all_exams(request)


@student_required
def upcoming_exams(request):
    """List upcoming scheduled exams."""
    return _upcoming_exams(request)


@student_required
def attempted_exams(request):
    """List exams already attempted by student."""
    return _attempted_exams(request)


@student_required
def pyqs(request):
    """Previous year questions organized by subject."""
    return _pyqs(request)


@student_required
def start_exam(request, test_id):
    """Start a new exam attempt."""
    return _start_exam(request, test_id)


@student_required
def submit_exam(request, attempt_id):
    """Submit completed exam."""
    return _submit_exam(request, attempt_id)


@student_required
def review_exam(request, attempt_id):
    """Review completed exam with answers and feedback."""
    return _review_exam(request, attempt_id)


# AJAX Endpoints
@student_required
def auto_save_answer(request):
    """Auto-save student answer during exam (AJAX)."""
    return _auto_save_answer(request)


@student_required
def mark_for_review(request):
    """Mark question for later review (AJAX)."""
    return _mark_for_review(request)


# Results
@student_required
def results(request):
    """View all test results."""
    return _results(request)


@student_required
def download_result(request, attempt_id):
    """Download individual test result as CSV."""
    return _download_result(request, attempt_id)


@student_required
def download_cumulative_report(request):
    """Download cumulative performance report."""
    return _download_cumulative(request)


# Resources
@student_required
def study_materials(request):
    """Access study materials uploaded by teachers."""
    return _study_materials(request)


@student_required
def leaderboard(request):
    """View global leaderboard rankings."""
    return _leaderboard(request)


@student_required
def certificates(request):
    """View earned certificates."""
    return _certificates(request)


# Support
@student_required
def help_support(request):
    """Submit and view support tickets."""
    from django.shortcuts import render
    from django.contrib import messages
    from accounts.models import HelpRequest
    
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        description = request.POST.get('description', '').strip()
        priority = request.POST.get('priority', 'medium')
        
        if subject and description:
            help_request = HelpRequest.objects.create(
                student=request.user,
                subject=subject,
                description=description,
                priority=priority,
                status='pending'
            )
            
            # Send email notification to admins
            try:
                from core.email_service import EmailService
                email_service = EmailService()
                email_service.send_help_request_notification(help_request, to_admin=True)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to send help request notification email: {e}")
            
            messages.success(request, 'Your help request has been submitted successfully. Our admin team will respond soon.')
            return redirect('students:help')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    # Get all help requests from this student
    help_requests = HelpRequest.objects.filter(student=request.user).order_by('-created_at')
    
    return render(request, 'students/help_support.html', {
        'help_requests': help_requests,
    })


@student_required
def delete_help_request(request, request_id):
    """Delete a help request."""
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    from accounts.models import HelpRequest
    
    help_request = get_object_or_404(HelpRequest, id=request_id, student=request.user)
    
    if request.method == 'POST':
        subject = help_request.subject
        help_request.delete()
        messages.success(request, f'Help request "{subject}" has been deleted successfully.')
        return redirect('students:help')
    
    return redirect('students:help')


@student_required
def notifications(request):
    """View all notifications."""
    return _notifications(request)


@student_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read."""
    return _mark_notification_read(request, notification_id)
