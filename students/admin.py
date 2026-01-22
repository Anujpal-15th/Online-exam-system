from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['roll_number', 'user', 'course', 'branch', 'year', 'semester', 'created_at']
    list_filter = ['course', 'year', 'semester', 'branch']
    search_fields = ['roll_number', 'user__username', 'user__email', 'branch']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Academic Details', {
            'fields': ('roll_number', 'course', 'branch', 'year', 'semester')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'date_of_birth', 'address')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
