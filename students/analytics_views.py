"""Student Analytics Dashboard Views"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Avg, Count, Sum, Q, Max, Min
from django.utils import timezone
from datetime import timedelta
from exams.models import TestAttempt, TestAnswer, Test
from questions.models import Question
import json


@login_required
def student_analytics(request):
    """Main analytics dashboard for students."""
    if request.user.user_type != 3:
        return redirect('questions_list')
    
    # Get all submitted attempts
    attempts = TestAttempt.objects.filter(
        student=request.user,
        is_submitted=True
    ).select_related('test').order_by('submitted_at')
    
    # Overall statistics
    total_attempts = attempts.count()
    
    if total_attempts > 0:
        # Calculate percentage scores manually since percentage_score field doesn't exist
        total_percentage = 0
        highest_score = 0
        lowest_score = 100
        total_time_spent_seconds = 0
        
        for attempt in attempts:
            if attempt.total_score is not None and attempt.test.total_marks > 0:
                percentage = (attempt.total_score / attempt.test.total_marks) * 100
                total_percentage += percentage
                highest_score = max(highest_score, percentage)
                lowest_score = min(lowest_score, percentage)
            total_time_spent_seconds += attempt.time_spent_seconds
        
        avg_score = total_percentage / total_attempts if total_attempts > 0 else 0
        total_time_spent = timedelta(seconds=total_time_spent_seconds)
        lowest_score = lowest_score if lowest_score != 100 else 0
    else:
        avg_score = 0
        highest_score = 0
        lowest_score = 0
        total_time_spent = timedelta(0)
    
    # Calculate improvement trend (last 5 vs first 5)
    recent_attempts = list(attempts[:5])
    old_attempts = list(attempts[max(0, total_attempts-5):total_attempts])
    
    # Calculate recent average
    recent_total = 0
    for attempt in recent_attempts:
        if attempt.total_score is not None and attempt.test.total_marks > 0:
            recent_total += (attempt.total_score / attempt.test.total_marks) * 100
    recent_avg = recent_total / len(recent_attempts) if recent_attempts else 0
    
    # Calculate old average
    old_total = 0
    for attempt in old_attempts:
        if attempt.total_score is not None and attempt.test.total_marks > 0:
            old_total += (attempt.total_score / attempt.test.total_marks) * 100
    old_avg = old_total / len(old_attempts) if old_attempts else 0
    
    improvement = recent_avg - old_avg if total_attempts >= 5 else 0
    
    context = {
        'total_attempts': total_attempts,
        'avg_score': round(avg_score, 2),
        'highest_score': round(highest_score, 2),
        'lowest_score': round(lowest_score, 2),
        'total_time_spent': total_time_spent,
        'improvement': round(improvement, 2),
    }
    
    return render(request, 'students/analytics.html', context)


@login_required
def analytics_chart_data(request):
    """API endpoint for chart data."""
    if request.user.user_type != 3:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    chart_type = request.GET.get('type', 'performance_trend')
    
    if chart_type == 'performance_trend':
        return _get_performance_trend(request.user)
    elif chart_type == 'subject_performance':
        return _get_subject_performance(request.user)
    elif chart_type == 'difficulty_analysis':
        return _get_difficulty_analysis(request.user)
    elif chart_type == 'time_analysis':
        return _get_time_analysis(request.user)
    elif chart_type == 'question_type_accuracy':
        return _get_question_type_accuracy(request.user)
    else:
        return JsonResponse({'error': 'Invalid chart type'}, status=400)


def _get_performance_trend(user):
    """Performance over time (last 20 attempts)."""
    attempts = TestAttempt.objects.filter(
        student=user,
        is_submitted=True
    ).select_related('test').order_by('-submitted_at')[:20]
    
    # Reverse to show chronological order
    attempts = list(reversed(attempts))
    
    labels = []
    scores = []
    
    for attempt in attempts:
        # Format label: "Test Name (Date)"
        label = f"{attempt.test.title[:15]}... ({attempt.submitted_at.strftime('%m/%d')})"
        labels.append(label)
        # Calculate percentage from total_score and test.total_marks
        if attempt.total_score is not None and attempt.test.total_marks > 0:
            percentage = (attempt.total_score / attempt.test.total_marks) * 100
        else:
            percentage = 0
        scores.append(round(percentage, 2))
    
    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'label': 'Score (%)',
            'data': scores,
            'borderColor': 'rgb(59, 130, 246)',
            'backgroundColor': 'rgba(59, 130, 246, 0.1)',
            'tension': 0.3,
            'fill': True
        }]
    })


def _get_subject_performance(user):
    """Average score by subject."""
    # Get all test attempts with subject info
    attempts = TestAttempt.objects.filter(
        student=user,
        is_submitted=True
    ).select_related('test')
    
    subject_data = {}
    
    for attempt in attempts:
        subject = attempt.test.subject or 'General'
        if subject not in subject_data:
            subject_data[subject] = {'total_score': 0, 'count': 0}
        
        # Calculate percentage from total_score and test.total_marks
        if attempt.total_score is not None and attempt.test.total_marks > 0:
            percentage = (attempt.total_score / attempt.test.total_marks) * 100
        else:
            percentage = 0
        
        subject_data[subject]['total_score'] += percentage
        subject_data[subject]['count'] += 1
    
    # Calculate averages
    labels = []
    scores = []
    colors = [
        'rgba(239, 68, 68, 0.8)',   # Red
        'rgba(59, 130, 246, 0.8)',  # Blue
        'rgba(34, 197, 94, 0.8)',   # Green
        'rgba(249, 115, 22, 0.8)',  # Orange
        'rgba(168, 85, 247, 0.8)',  # Purple
        'rgba(236, 72, 153, 0.8)',  # Pink
        'rgba(14, 165, 233, 0.8)',  # Sky
        'rgba(132, 204, 22, 0.8)',  # Lime
    ]
    
    for idx, (subject, data) in enumerate(subject_data.items()):
        labels.append(subject)
        avg = data['total_score'] / data['count'] if data['count'] > 0 else 0
        scores.append(round(avg, 2))
    
    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'label': 'Average Score (%)',
            'data': scores,
            'backgroundColor': colors[:len(labels)],
            'borderColor': colors[:len(labels)],
            'borderWidth': 1
        }]
    })


def _get_difficulty_analysis(user):
    """Performance by question difficulty."""
    # Get all test answers
    answers = TestAnswer.objects.filter(
        attempt__student=user,
        attempt__is_submitted=True,
        question__isnull=False
    ).select_related('question')
    
    difficulty_stats = {
        'easy': {'correct': 0, 'total': 0},
        'medium': {'correct': 0, 'total': 0},
        'hard': {'correct': 0, 'total': 0}
    }
    
    for answer in answers:
        difficulty = answer.question.difficulty
        if difficulty in difficulty_stats:
            difficulty_stats[difficulty]['total'] += 1
            
            # Check if correct
            if answer.score is not None and answer.question.marks > 0:
                if answer.score >= answer.question.marks * 0.5:  # 50% or more = correct
                    difficulty_stats[difficulty]['correct'] += 1
    
    labels = ['Easy', 'Medium', 'Hard']
    accuracy = []
    
    for diff in ['easy', 'medium', 'hard']:
        stats = difficulty_stats[diff]
        if stats['total'] > 0:
            acc = (stats['correct'] / stats['total']) * 100
            accuracy.append(round(acc, 2))
        else:
            accuracy.append(0)
    
    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'label': 'Accuracy (%)',
            'data': accuracy,
            'backgroundColor': [
                'rgba(34, 197, 94, 0.8)',   # Green for easy
                'rgba(249, 115, 22, 0.8)',  # Orange for medium
                'rgba(239, 68, 68, 0.8)'    # Red for hard
            ],
            'borderColor': [
                'rgb(34, 197, 94)',
                'rgb(249, 115, 22)',
                'rgb(239, 68, 68)'
            ],
            'borderWidth': 2
        }]
    })


def _get_time_analysis(user):
    """Time spent per test."""
    attempts = TestAttempt.objects.filter(
        student=user,
        is_submitted=True,
        time_spent_seconds__gt=0
    ).select_related('test').order_by('-submitted_at')[:10]
    
    # Reverse for chronological order
    attempts = list(reversed(attempts))
    
    labels = []
    time_data = []
    
    for attempt in attempts:
        labels.append(attempt.test.title[:20] + '...' if len(attempt.test.title) > 20 else attempt.test.title)
        # Convert seconds to minutes
        minutes = attempt.time_spent_seconds / 60 if attempt.time_spent_seconds else 0
        time_data.append(round(minutes, 2))
    
    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'label': 'Time (minutes)',
            'data': time_data,
            'backgroundColor': 'rgba(168, 85, 247, 0.6)',
            'borderColor': 'rgb(168, 85, 247)',
            'borderWidth': 2
        }]
    })


def _get_question_type_accuracy(user):
    """Accuracy by question type."""
    answers = TestAnswer.objects.filter(
        attempt__student=user,
        attempt__is_submitted=True,
        question__isnull=False
    ).select_related('question')
    
    type_stats = {}
    
    for answer in answers:
        q_type = answer.question.get_type_display()
        if q_type not in type_stats:
            type_stats[q_type] = {'correct': 0, 'total': 0}
        
        type_stats[q_type]['total'] += 1
        
        # Check if correct
        if answer.score is not None and answer.question.marks > 0:
            if answer.score >= answer.question.marks * 0.5:
                type_stats[q_type]['correct'] += 1
    
    labels = list(type_stats.keys())
    accuracy = []
    
    for q_type in labels:
        stats = type_stats[q_type]
        if stats['total'] > 0:
            acc = (stats['correct'] / stats['total']) * 100
            accuracy.append(round(acc, 2))
        else:
            accuracy.append(0)
    
    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'label': 'Accuracy (%)',
            'data': accuracy,
            'backgroundColor': 'rgba(14, 165, 233, 0.6)',
            'borderColor': 'rgb(14, 165, 233)',
            'borderWidth': 1
        }]
    })
