from django.contrib import admin
from .models import CustomUser, HelpRequest


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "user_type", "is_active", "is_staff")
    list_filter = ("user_type", "is_active", "is_staff")
    search_fields = ("username", "email")
    ordering = ("id",)


@admin.register(HelpRequest)
class HelpRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "student", "status", "priority", "created_at", "resolved_at")
    list_filter = ("status", "priority", "created_at")
    search_fields = ("subject", "description", "student__username", "student__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
