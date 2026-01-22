"""Views for tag management."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Count, Q
from .models import Tag, Question
import json


@login_required
def tag_list(request):
    """Display all tags with question counts."""
    if request.user.user_type not in (1, 2):
        return redirect('student_dashboard')
    
    # Get user's tags and global tags
    tags = Tag.objects.filter(
        Q(created_by=request.user) | Q(is_global=True)
    ).annotate(
        question_count=Count('questions', filter=Q(questions__author=request.user))
    ).order_by('-question_count', 'name')
    
    context = {
        'tags': tags,
        'total_tags': tags.count(),
    }
    return render(request, 'questions/tags/tag_list.html', context)


@login_required
def create_tag(request):
    """Create a new tag."""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            
            name = data.get('name', '').strip()
            color = data.get('color', '#3b82f6').strip()
            description = data.get('description', '').strip()
            is_global = data.get('is_global', False) if request.user.user_type == 1 else False
            
            if not name:
                return JsonResponse({'success': False, 'error': 'Tag name is required'})
            
            # Check for duplicate
            if Tag.objects.filter(created_by=request.user, name__iexact=name).exists():
                return JsonResponse({'success': False, 'error': 'Tag with this name already exists'})
            
            tag = Tag.objects.create(
                name=name,
                color=color,
                description=description,
                created_by=request.user,
                is_global=is_global
            )
            
            return JsonResponse({
                'success': True,
                'tag': {
                    'id': tag.id,
                    'name': tag.name,
                    'slug': tag.slug,
                    'color': tag.color,
                    'description': tag.description,
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return render(request, 'questions/tags/create_tag.html')


@login_required
def edit_tag(request, tag_id):
    """Edit an existing tag."""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    tag = get_object_or_404(Tag, id=tag_id, created_by=request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            
            name = data.get('name', '').strip()
            color = data.get('color', tag.color).strip()
            description = data.get('description', '').strip()
            is_global = data.get('is_global', tag.is_global) if request.user.user_type == 1 else tag.is_global
            
            if not name:
                return JsonResponse({'success': False, 'error': 'Tag name is required'})
            
            # Check for duplicate (excluding current tag)
            if Tag.objects.filter(created_by=request.user, name__iexact=name).exclude(id=tag.id).exists():
                return JsonResponse({'success': False, 'error': 'Tag with this name already exists'})
            
            tag.name = name
            tag.color = color
            tag.description = description
            tag.is_global = is_global
            tag.save()
            
            return JsonResponse({
                'success': True,
                'tag': {
                    'id': tag.id,
                    'name': tag.name,
                    'slug': tag.slug,
                    'color': tag.color,
                    'description': tag.description,
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    context = {'tag': tag}
    return render(request, 'questions/tags/edit_tag.html', context)


@login_required
def delete_tag(request, tag_id):
    """Delete a tag."""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    tag = get_object_or_404(Tag, id=tag_id, created_by=request.user)
    
    if request.method == 'POST':
        tag_name = tag.name
        tag.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Tag "{tag_name}" deleted successfully'})
        
        messages.success(request, f'Tag "{tag_name}" deleted successfully')
        return redirect('tag_list')
    
    context = {'tag': tag}
    return render(request, 'questions/tags/delete_tag.html', context)


@login_required
def assign_tags(request):
    """Assign tags to multiple questions (bulk operation)."""
    if request.user.user_type not in (1, 2) or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    
    try:
        data = json.loads(request.body)
        question_ids = data.get('question_ids', [])
        tag_ids = data.get('tag_ids', [])
        action = data.get('action', 'add')  # 'add' or 'remove'
        
        if not question_ids or not tag_ids:
            return JsonResponse({'success': False, 'error': 'Questions and tags are required'})
        
        questions = Question.objects.filter(id__in=question_ids, author=request.user)
        tags = Tag.objects.filter(id__in=tag_ids).filter(
            Q(created_by=request.user) | Q(is_global=True)
        )
        
        if action == 'add':
            for question in questions:
                question.tags.add(*tags)
            message = f'Tags added to {questions.count()} questions'
        else:  # remove
            for question in questions:
                question.tags.remove(*tags)
            message = f'Tags removed from {questions.count()} questions'
        
        return JsonResponse({'success': True, 'message': message})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_tags_json(request):
    """Get all available tags as JSON (for autocomplete/dropdowns)."""
    if request.user.user_type not in (1, 2):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    tags = Tag.objects.filter(
        Q(created_by=request.user) | Q(is_global=True)
    ).values('id', 'name', 'slug', 'color', 'description')
    
    return JsonResponse({'success': True, 'tags': list(tags)})
