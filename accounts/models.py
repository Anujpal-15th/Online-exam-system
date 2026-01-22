from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class CustomUserManager(BaseUserManager):
    """
    Custom manager that makes email required, normalizes emails, and sets sensible defaults.
    """
    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError("The username must be set")
        if not email:
            raise ValueError("The email must be set")
        email = self.normalize_email(email).lower()
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('user_type', 3)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 1)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(username, email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Custom user model with role-based access control.
    
    Extends Django's AbstractUser to add user_type field for role management.
    Supports three roles: Admin, Teacher, and Student.
    """
    ADMIN = 1
    TEACHER = 2
    STUDENT = 3

    USER_TYPE_CHOICES = (
        (ADMIN, 'admin'),
        (TEACHER, 'teacher'),
        (STUDENT, 'student'),
    )

    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default=STUDENT)
    email = models.EmailField(unique=True, blank=False, null=False)
    is_blocked = models.BooleanField(default=False)

    objects = CustomUserManager()
    
    class Meta:
        ordering = ['username']
        indexes = [
            models.Index(fields=['user_type', 'username']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

    @property
    def is_admin_role(self) -> bool:
        return self.user_type == self.ADMIN

    @property
    def is_teacher_role(self) -> bool:
        return self.user_type == self.TEACHER

    @property
    def is_student_role(self) -> bool:
        return self.user_type == self.STUDENT

    def owns(self, obj) -> bool:
        if self.is_admin_role:
            return True
        try:
            if hasattr(obj, 'author_id'):
                return obj.author_id == self.id
            if hasattr(obj, 'created_by_id'):
                return obj.created_by_id == self.id
        except Exception:
            return False
        return False

    def scope_owned_queryset(self, qs):
        if self.is_admin_role:
            return qs
        if self.is_teacher_role:
            model = qs.model
            try:
                model._meta.get_field('author')
                return qs.filter(author=self)
            except Exception:
                # Model doesn't have 'author' field, try next field
                pass
            try:
                model._meta.get_field('created_by')
                return qs.filter(created_by=self)
            except Exception:
                # Model doesn't have 'created_by' field either
                pass
        return qs


class HelpRequest(models.Model):
    """
    Model to store student help and support requests.
    
    Students can submit help requests that admins can view and respond to.
    Tracks status, priority, and admin responses.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    student = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='help_requests',
        limit_choices_to={'user_type': 3}
    )
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    admin_response = models.TextField(blank=True, null=True)
    responded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='help_responses',
        limit_choices_to={'user_type': 1}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.subject} - {self.student.username} ({self.status})"
    
    @property
    def is_resolved(self):
        return self.status in ['resolved', 'closed']
