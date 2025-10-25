from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        (1, 'admin'),
        (2, 'teacher'),
        (3, 'student'),
    )

    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default=1)  # default = admin
    email = models.EmailField(unique=True, blank=False, null=False)
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
