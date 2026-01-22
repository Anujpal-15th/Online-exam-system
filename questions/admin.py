from django.contrib import admin
from .models import (Question, Submission, QuestionOption, 
                     Notification, Resource, Subject, QuestionFolder, MaterialFolder, Tag)
# Test, TestQuestion, TestAttempt, TestAnswer, Certificate, MarkedQuestion moved to exams app


class QuestionOptionInline(admin.TabularInline):
	model = QuestionOption
	extra = 1


@admin.register(QuestionFolder)
class QuestionFolderAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "parent", "created_by", "get_question_count", "is_archived", "created_at")
	list_filter = ("is_archived", "created_by", "created_at")
	search_fields = ("name", "description")
	ordering = ("order", "name")
	fieldsets = (
		("Folder Information", {
			"fields": ("name", "description", "parent")
		}),
		("Appearance", {
			"fields": ("color", "icon", "order")
		}),
		("Settings", {
			"fields": ("is_archived", "created_by")
		}),
	)
	readonly_fields = ("created_by",)
	
	def get_question_count(self, obj):
		return obj.get_question_count()
	get_question_count.short_description = "Questions"


@admin.register(MaterialFolder)
class MaterialFolderAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "parent", "created_by", "get_material_count", "is_archived", "created_at")
	list_filter = ("is_archived", "created_by", "created_at")
	search_fields = ("name", "description")
	ordering = ("order", "name")
	fieldsets = (
		("Folder Information", {
			"fields": ("name", "description", "parent")
		}),
		("Appearance", {
			"fields": ("color", "icon", "order")
		}),
		("Settings", {
			"fields": ("is_archived", "created_by")
		}),
	)
	readonly_fields = ("created_by",)
	
	def get_material_count(self, obj):
		return obj.get_material_count()
	get_material_count.short_description = "Materials"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
	list_display = ("id", "type", "subject", "topic", "difficulty", "author", "created_at")
	list_filter = ("type", "difficulty", "subject")
	search_fields = ("question_text", "subject", "topic")
	ordering = ("-created_at",)
	inlines = [QuestionOptionInline]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
	list_display = ("id", "student", "question", "graded", "score", "submitted_at", "graded_at")
	list_filter = ("graded",)
	search_fields = ("student__username", "question__id")
	ordering = ("-submitted_at",)


# Test-related admin moved to exams/admin.py


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "title", "is_read", "created_at")
	list_filter = ("is_read", "created_at")
	search_fields = ("user__username", "title", "message")
	ordering = ("-created_at",)


# Certificate admin moved to exams/admin.py


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
	list_display = ("id", "title", "subject", "uploaded_by", "created_at")
	list_filter = ("subject", "created_at")
	search_fields = ("title", "description", "subject")
	ordering = ("-created_at",)


# MarkedQuestion admin moved to exams/admin.py


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "code", "category", "is_active", "created_by", "created_at")
	list_filter = ("category", "is_active", "created_at")
	search_fields = ("name", "code", "category", "description")
	ordering = ("category", "name")
	fieldsets = (
		("Subject Information", {
			"fields": ("name", "code", "category", "description")
		}),
		("Status", {
			"fields": ("is_active", "created_by")
		}),
	)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "slug", "color", "created_by", "is_global", "created_at")
	list_filter = ("is_global", "created_by", "created_at")
	search_fields = ("name", "slug", "description")
	ordering = ("name",)
	prepopulated_fields = {"slug": ("name",)}
	fieldsets = (
		("Tag Information", {
			"fields": ("name", "slug", "description")
		}),
		("Appearance", {
			"fields": ("color",)
		}),
		("Settings", {
			"fields": ("created_by", "is_global")
		}),
	)
