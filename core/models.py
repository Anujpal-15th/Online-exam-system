"""
Core models for Admin Dashboard functionality.
"""
from django.db import models
from django.conf import settings


class TeacherProfile(models.Model):
    """
    Extended profile for teachers with approval workflow.
    """
    APPROVAL_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, help_text='Department (e.g., Computer Science, Mathematics)')
    specialization = models.CharField(max_length=200, blank=True, help_text='Subject specialization or area of expertise')
    qualification = models.CharField(max_length=200, blank=True, help_text='Highest qualification (e.g., M.Tech, PhD)')
    experience_years = models.PositiveIntegerField(default=0, help_text='Years of teaching experience')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    office_location = models.CharField(max_length=200, blank=True, null=True)
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='approved'
    )
    documents_submitted = models.BooleanField(default=False)
    bio = models.TextField(blank=True, help_text='Professional bio or description')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['approval_status', '-created_at']),
        ]
        verbose_name = 'Teacher Profile'
        verbose_name_plural = 'Teacher Profiles'
    
    def __str__(self):
        return f"{self.user.username} - {self.department if self.department else 'No Dept'}"
    
    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
    
    def approve(self):
        """Approve teacher profile."""
        self.approval_status = 'approved'
        self.save()
    
    def reject(self):
        """Reject teacher profile."""
        self.approval_status = 'rejected'
        self.save()


class AllowedDomain(models.Model):
    """
    Email domains allowed for registration.
    """
    domain_name = models.CharField(
        max_length=100,
        unique=True,
        help_text="e.g., @college.edu or college.edu"
    )
    description = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['domain_name']
        verbose_name = 'Allowed Domain'
        verbose_name_plural = 'Allowed Domains'
    
    def __str__(self):
        return self.domain_name
    
    def clean_domain(self):
        """Ensure domain starts with @ symbol."""
        if not self.domain_name.startswith('@'):
            self.domain_name = '@' + self.domain_name
        return self.domain_name.lower()
    
    def save(self, *args, **kwargs):
        self.domain_name = self.clean_domain()
        super().save(*args, **kwargs)


class BlockedUser(models.Model):
    """
    Users who are blocked from accessing the platform.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocked_record',
        null=True,
        blank=True
    )
    email = models.EmailField(unique=True)
    reason = models.TextField(blank=True)
    blocked_at = models.DateTimeField(auto_now_add=True)
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='blocked_users'
    )
    
    class Meta:
        ordering = ['-blocked_at']
        verbose_name = 'Blocked User'
        verbose_name_plural = 'Blocked Users'
    
    def __str__(self):
        return f"Blocked: {self.email}"


class QuestionApproval(models.Model):
    """
    Approval workflow for questions.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    question = models.OneToOneField(
        'questions.Question',
        on_delete=models.CASCADE,
        related_name='approval'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_questions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"Q{self.question.id} - {self.get_status_display()}"
    
    def approve(self, admin_user):
        """Approve question."""
        from django.utils import timezone
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()
    
    def reject(self, admin_user, notes=''):
        """Reject question."""
        from django.utils import timezone
        self.status = 'rejected'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.admin_notes = notes
        self.save()
