from django.db import models
from accounts.models import CustomUser


class StudentProfile(models.Model):
    """
    Extended profile for students with institute-specific information.
    """
    COURSE_CHOICES = [
        ('btech', 'B.Tech'),
        ('mtech', 'M.Tech'),
        ('bca', 'BCA'),
        ('mca', 'MCA'),
        ('bsc', 'B.Sc'),
        ('msc', 'M.Sc'),
        ('ba', 'BA'),
        ('ma', 'MA'),
        ('bba', 'BBA'),
        ('mba', 'MBA'),
        ('other', 'Other'),
    ]
    
    YEAR_CHOICES = [
        (1, 'First Year'),
        (2, 'Second Year'),
        (3, 'Third Year'),
        (4, 'Fourth Year'),
        (5, 'Fifth Year'),
    ]
    
    SEMESTER_CHOICES = [
        (1, 'Semester 1'),
        (2, 'Semester 2'),
        (3, 'Semester 3'),
        (4, 'Semester 4'),
        (5, 'Semester 5'),
        (6, 'Semester 6'),
        (7, 'Semester 7'),
        (8, 'Semester 8'),
        (9, 'Semester 9'),
        (10, 'Semester 10'),
    ]
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    roll_number = models.CharField(max_length=50, unique=True)
    course = models.CharField(max_length=20, choices=COURSE_CHOICES)
    branch = models.CharField(max_length=100, help_text='Department/Branch (e.g., Computer Science, Mechanical)')
    year = models.PositiveSmallIntegerField(choices=YEAR_CHOICES)
    semester = models.PositiveSmallIntegerField(choices=SEMESTER_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['roll_number']
        verbose_name = 'Student Profile'
        verbose_name_plural = 'Student Profiles'
    
    def __str__(self):
        return f"{self.user.username} - {self.roll_number}"

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
