from django.contrib import admin
from .models import (Test, TestQuestion, TestAttempt, TestAnswer, 
                     Certificate, MarkedQuestion, ScheduledTest)


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
	list_display = ("id", "title", "subject", "created_by", "created_at", "scheduled_at")
	search_fields = ("title", "subject")
	list_filter = ("subject",)
	date_hierarchy = 'created_at'


@admin.register(TestQuestion)
class TestQuestionAdmin(admin.ModelAdmin):
	list_display = ("id", "test", "question", "order")
	list_filter = ("test",)


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
	list_display = ("id", "test", "student", "attempt_number", "is_submitted", "total_score", "started_at", "submitted_at")
	list_filter = ("test", "is_submitted")
	search_fields = ("student__username", "test__title")
	date_hierarchy = 'started_at'


@admin.register(TestAnswer)
class TestAnswerAdmin(admin.ModelAdmin):
	list_display = ("id", "attempt", "question", "score", "created_at")
	list_filter = ("attempt__test",)
	search_fields = ("attempt__student__username", "question__id")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
	list_display = ("id", "student", "test", "score_percentage", "issued_date")
	list_filter = ("issued_date",)
	search_fields = ("student__username", "test__title")
	ordering = ("-issued_date",)


@admin.register(MarkedQuestion)
class MarkedQuestionAdmin(admin.ModelAdmin):
	list_display = ("id", "attempt", "question", "marked_at")
	list_filter = ("marked_at",)
	search_fields = ("attempt__student__username", "question__id")
	ordering = ("-marked_at",)


@admin.register(ScheduledTest)
class ScheduledTestAdmin(admin.ModelAdmin):
	list_display = ("id", "title", "test_paper", "start_time", "end_time", "status", "is_published")
	list_filter = ("status", "is_published", "start_time")
	search_fields = ("title", "test_paper__title")
	date_hierarchy = 'start_time'
	readonly_fields = ('created_at',)
