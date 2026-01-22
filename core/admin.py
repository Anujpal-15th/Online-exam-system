"""
Admin configuration for core models.
"""
from django.contrib import admin
from .models import TeacherProfile, AllowedDomain, BlockedUser, QuestionApproval


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'department', 'approval_status', 'documents_submitted', 'created_at']
    list_filter = ['approval_status', 'documents_submitted']
    search_fields = ['user__username', 'user__email', 'department']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AllowedDomain)
class AllowedDomainAdmin(admin.ModelAdmin):
    list_display = ['domain_name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['domain_name', 'description']


@admin.register(BlockedUser)
class BlockedUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'user', 'reason', 'blocked_at', 'blocked_by']
    list_filter = ['blocked_at']
    search_fields = ['email', 'user__username', 'reason']
    readonly_fields = ['blocked_at']


@admin.register(QuestionApproval)
class QuestionApprovalAdmin(admin.ModelAdmin):
    list_display = ['question', 'status', 'reviewed_by', 'reviewed_at', 'created_at']
    list_filter = ['status', 'reviewed_at']
    search_fields = ['question__question_text', 'admin_notes']
    readonly_fields = ['created_at', 'reviewed_at']
