"""
API views for subject management.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import Subject
import json


@login_required
@require_http_methods(["GET"])
def get_subjects(request):
    """Get all active subjects grouped by category."""
    subjects = Subject.objects.filter(is_active=True).order_by('category', 'name')
    
    # Group by category
    subjects_by_category = {}
    for subject in subjects:
        category = subject.category or 'Other'
        if category not in subjects_by_category:
            subjects_by_category[category] = []
        subjects_by_category[category].append({
            'id': subject.id,
            'name': subject.name,
            'code': subject.code,
            'category': subject.category
        })
    
    return JsonResponse({
        'success': True,
        'subjects': subjects_by_category,
        'all_subjects': list(subjects.values('id', 'name', 'code', 'category'))
    })


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def add_subject(request):
    """Add a new custom subject."""
    # Only teachers and admins can add subjects
    if request.user.user_type not in [1, 2]:
        return JsonResponse({
            'success': False,
            'error': 'Only teachers and admins can add subjects'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        subject_name = data.get('name', '').strip()
        category = data.get('category', 'Other').strip()
        code = data.get('code', '').strip()
        
        if not subject_name:
            return JsonResponse({
                'success': False,
                'error': 'Subject name is required'
            }, status=400)
        
        # Check if subject already exists
        if Subject.objects.filter(name__iexact=subject_name).exists():
            return JsonResponse({
                'success': False,
                'error': 'Subject already exists'
            }, status=400)
        
        # Create new subject
        subject = Subject.objects.create(
            name=subject_name,
            category=category,
            code=code,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'subject': {
                'id': subject.id,
                'name': subject.name,
                'code': subject.code,
                'category': subject.category
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
