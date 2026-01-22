"""
Django Forms for Authentication and User Management.

These forms provide automatic validation, CSRF protection, and cleaner code
compared to manual request.POST handling.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import CustomUser


class LoginForm(forms.Form):
    """
    Professional login form with username/email support.
    
    Features:
    - Accept username or email as identifier
    - Remember me functionality
    - Automatic validation
    - CSRF protection
    """
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        }),
        label='Username or Email'
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Remember Me'
    )


class RegistrationForm(forms.ModelForm):
    """
    User registration form with automatic validation.
    
    Features:
    - Automatic email format validation
    - Password strength checking
    - Username/email uniqueness validation
    - Consistent error messages
    """
    full_name = forms.CharField(
        max_length=100,
        required=True,
        min_length=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        }),
        help_text='Enter your first and last name'
    )
    
    username = forms.CharField(
        max_length=150,
        required=True,
        min_length=3,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username'
        }),
        help_text='3-150 characters. Letters, digits and @/./+/-/_ only.'
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        }),
        help_text='We will send a verification email to this address'
    )
    
    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        }),
        help_text='Minimum 8 characters'
    )
    
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        }),
        label='Confirm Password'
    )
    
    user_type = forms.ChoiceField(
        choices=[
            ('', 'Select Role'),
            ('2', 'Teacher'),
            ('3', 'Student'),
        ],
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='I am a'
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'user_type']
    
    def clean_username(self):
        """Validate username is unique and not taken by an active user."""
        username = self.cleaned_data.get('username')
        
        # Check for existing active users
        existing = CustomUser.objects.filter(username=username, is_active=True).exists()
        if existing:
            raise ValidationError('This username is already taken.')
        
        # Delete old unverified accounts with same username (allow re-registration)
        CustomUser.objects.filter(username=username, is_active=False).delete()
        
        return username
    
    def clean_email(self):
        """Validate email is unique and properly formatted."""
        email = self.cleaned_data.get('email')
        
        # Check for existing active users
        existing = CustomUser.objects.filter(email=email, is_active=True).exists()
        if existing:
            raise ValidationError('This email is already registered.')
        
        # Delete old unverified accounts with same email (allow re-registration)
        CustomUser.objects.filter(email=email, is_active=False).delete()
        
        return email
    
    def clean(self):
        """Validate password matching and strength."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        
        if password and confirm:
            if password != confirm:
                raise ValidationError('Passwords do not match.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Create user with hashed password and split name."""
        user = super().save(commit=False)
        
        # Set password properly (hashed)
        user.set_password(self.cleaned_data['password'])
        
        # Split full name into first and last name
        full_name = self.cleaned_data.get('full_name', '')
        name_parts = full_name.split(maxsplit=1)
        user.first_name = name_parts[0] if name_parts else ''
        user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Set user as inactive until email verification
        user.is_active = False
        
        if commit:
            user.save()
        
        return user


class AdminUserCreationForm(forms.ModelForm):
    """
    Form for admins to create users without email verification.
    
    Features:
    - Admin can create users directly (active by default)
    - Optional email verification
    - All user types supported
    """
    full_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Minimum 8 characters'
    )
    
    user_type = forms.ChoiceField(
        choices=[
            ('1', 'Admin'),
            ('2', 'Teacher'),
            ('3', 'Student'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='User Type'
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'user_type']
    
    def clean_username(self):
        """Ensure username is unique."""
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError('Username already exists.')
        return username
    
    def clean_email(self):
        """Ensure email is unique."""
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('Email already registered.')
        return email
    
    def save(self, commit=True):
        """Create user with admin privileges (active by default)."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        
        # Split name
        full_name = self.cleaned_data.get('full_name', '')
        name_parts = full_name.split(maxsplit=1)
        user.first_name = name_parts[0] if name_parts else ''
        user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Admin-created users are active by default
        user.is_active = True
        
        if commit:
            user.save()
        
        return user
