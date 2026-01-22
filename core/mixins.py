"""
Permission mixins for views.

Provides reusable permission checking for class-based views.
"""

from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseForbidden


class RoleRequiredMixin(UserPassesTestMixin):
    """
    Mixin to restrict access based on user roles.
    
    Usage:
        class MyView(RoleRequiredMixin, View):
            allowed_roles = [1, 2]  # Admin and Teacher
    """
    allowed_roles = []
    
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        if not hasattr(self.request.user, 'user_type'):
            return False
        return self.request.user.user_type in self.allowed_roles


class AdminRequiredMixin(RoleRequiredMixin):
    """Mixin to restrict access to admins only."""
    allowed_roles = [1]


class TeacherRequiredMixin(RoleRequiredMixin):
    """Mixin to restrict access to teachers only."""
    allowed_roles = [2]


class StudentRequiredMixin(RoleRequiredMixin):
    """Mixin to restrict access to students only."""
    allowed_roles = [3]


class OwnershipMixin:
    """
    Mixin to check if user owns the object.
    
    Usage:
        class MyView(OwnershipMixin, UpdateView):
            ownership_field = 'author'  # Field to check ownership
    """
    ownership_field = 'created_by'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Admin has access to everything
        if hasattr(self.request.user, 'user_type') and self.request.user.user_type == 1:
            return obj
        
        # Check ownership
        owner = getattr(obj, self.ownership_field, None)
        if owner != self.request.user:
            raise HttpResponseForbidden("You don't have permission to access this resource.")
        
        return obj


class AjaxRequiredMixin:
    """
    Mixin to restrict access to AJAX requests only.
    
    Usage:
        class MyView(AjaxRequiredMixin, View):
            ...
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseForbidden("AJAX request required.")
        return super().dispatch(request, *args, **kwargs)
