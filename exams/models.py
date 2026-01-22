from django.db import models
from django.conf import settings
from django.utils import timezone


class Test(models.Model):
    """
    Represents an exam/test with multiple questions.
    
    Tests can be scheduled with specific start and end times, have duration limits,
    and allow multiple attempts. Questions are added through TestQuestion relationship.
    """
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100, blank=True)
    total_marks = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    allow_immediate_review = models.BooleanField(default=True)
    randomize_order = models.BooleanField(default=False)
    max_attempts = models.PositiveIntegerField(default=1)
    questions = models.ManyToManyField('questions.Question', through='TestQuestion', related_name='tests')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subject', '-created_at']),
            models.Index(fields=['created_by', '-created_at']),
        ]

    def __str__(self):
        return self.title


class TestQuestion(models.Model):
    """Through model linking Tests and Questions."""
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    question = models.ForeignKey('questions.Question', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=1)
    section = models.CharField(max_length=100, blank=True, default='', help_text='Section name like "Section A", "Part I", etc.')

    class Meta:
        unique_together = ('test', 'question')
        ordering = ['section', 'order', 'id']
    
    def __str__(self):
        section_str = f" [{self.section}]" if self.section else ""
        return f"{self.test.title} - Q{self.order + 1}{section_str} ({self.points}pts)"


class TestAttempt(models.Model):
    """Represents a student's attempt at taking a test."""
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='test_attempts')
    attempt_number = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    total_score = models.IntegerField(null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    question_order = models.TextField(blank=True, default='')

    class Meta:
        unique_together = ('test', 'student', 'attempt_number')
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['student', '-started_at']),
            models.Index(fields=['test', '-started_at']),
        ]
    
    def __str__(self):
        status = "Submitted" if self.submitted_at else "In Progress"
        return f"{self.student.username} - {self.test.title} (Attempt #{self.attempt_number}) - {status}"


class TestAnswer(models.Model):
    """Student's answer to a specific question in a test attempt."""
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey('questions.Question', on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True)
    score = models.IntegerField(null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('attempt', 'question')
        ordering = ['question__id']
    
    def __str__(self):
        score_text = f"{self.score}pts" if self.score is not None else "Ungraded"
        return f"Answer to Q{self.question.id} ({score_text})"


class Certificate(models.Model):
    """Certificates awarded to students for test completion."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='certificates')
    attempt = models.OneToOneField(TestAttempt, on_delete=models.CASCADE, related_name='certificate')
    issued_date = models.DateTimeField(auto_now_add=True)
    certificate_code = models.CharField(max_length=50, unique=True)
    score_percentage = models.FloatField()
    
    class Meta:
        unique_together = ('student', 'test', 'attempt')
        ordering = ['-issued_date']
        indexes = [
            models.Index(fields=['student', '-issued_date']),
            models.Index(fields=['certificate_code']),
        ]
    
    def __str__(self):
        return f"Certificate - {self.student.username} - {self.test.title} ({self.score_percentage:.1f}%)"


class MarkedQuestion(models.Model):
    """Questions flagged for review during a test attempt."""
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='marked_questions')
    question = models.ForeignKey('questions.Question', on_delete=models.CASCADE)
    marked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('attempt', 'question')
        ordering = ['marked_at']
    
    def __str__(self):
        return f"Marked - Q{self.question.id} in Attempt #{self.attempt_number}"


class ScheduledTest(models.Model):
    """
    Scheduled test instances for publishing and managing test availability.
    """
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('finished', 'Finished'),
    )
    
    test_paper = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name='scheduled_instances'
    )
    title = models.CharField(max_length=200, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_published = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='scheduled_tests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['status', '-start_time']),
            models.Index(fields=['is_published', 'start_time']),
        ]
    
    def __str__(self):
        return f"{self.title or self.test_paper.title} - {self.get_status_display()}"
    
    def publish(self):
        """Publish the scheduled test."""
        self.is_published = True
        self.save()
    
    def unpublish(self):
        """Unpublish the scheduled test."""
        self.is_published = False
        self.save()
    
    def update_status(self):
        """Auto-update status based on time."""
        now = timezone.now()
        if now < self.start_time:
            self.status = 'scheduled'
        elif self.start_time <= now <= self.end_time:
            self.status = 'live'
        else:
            self.status = 'finished'
        self.save()
