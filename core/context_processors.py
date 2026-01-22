"""
Context processors to make data available globally across all templates.
"""

from questions.models import Notification


def notification_context(request):
    """
    Add unread notification count to all template contexts for logged-in students.
    """
    context = {}
    
    if request.user.is_authenticated and hasattr(request.user, 'user_type') and request.user.user_type == 3:
        context['unread_notifications_count'] = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
    else:
        context['unread_notifications_count'] = 0
    
    return context
