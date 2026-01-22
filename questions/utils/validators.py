"""
Input validation and sanitization utilities.

This module provides validation functions for user inputs, form data,
and business rule enforcement.

Example Usage:
    from questions.utils.validators import validate_test_duration
    
    is_valid, error = validate_test_duration(duration_minutes)
"""

from typing import Tuple, Optional
from datetime import datetime, timedelta
from django.utils import timezone


def validate_test_duration(duration_minutes: int) -> Tuple[bool, Optional[str]]:
    """
    Validate test duration is within acceptable range.
    
    Args:
        duration_minutes: Test duration in minutes
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if duration_minutes < 1:
        return False, "Duration must be at least 1 minute"
    if duration_minutes > 480:  # 8 hours max
        return False, "Duration cannot exceed 480 minutes (8 hours)"
    return True, None


def validate_test_dates(
    start_at: Optional[datetime],
    end_at: Optional[datetime]
) -> Tuple[bool, Optional[str]]:
    """
    Validate test start and end dates.
    
    Args:
        start_at: Test start datetime
        end_at: Test end datetime
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if start_at and end_at:
        if end_at <= start_at:
            return False, "End time must be after start time"
        
        duration = end_at - start_at
        if duration < timedelta(minutes=1):
            return False, "Test window must be at least 1 minute"
            
    if start_at and start_at < timezone.now() - timedelta(days=365):
        return False, "Start time cannot be more than 1 year in the past"
        
    return True, None


def validate_max_attempts(max_attempts: int) -> Tuple[bool, Optional[str]]:
    """
    Validate maximum number of test attempts.
    
    Args:
        max_attempts: Maximum allowed attempts
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if max_attempts < 1:
        return False, "Must allow at least 1 attempt"
    if max_attempts > 10:
        return False, "Cannot allow more than 10 attempts"
    return True, None


def validate_points(points: int) -> Tuple[bool, Optional[str]]:
    """
    Validate question points value.
    
    Args:
        points: Points assigned to question
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if points < 0:
        return False, "Points cannot be negative"
    if points > 1000:
        return False, "Points cannot exceed 1000"
    return True, None


def sanitize_text_input(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize user text input by removing excessive whitespace.
    
    Args:
        text: Input text
        max_length: Optional maximum length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
        
    # Strip leading/trailing whitespace
    text = text.strip()
    
    # Replace multiple spaces with single space
    import re
    text = re.sub(r'\s+', ' ', text)
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length]
        
    return text


def validate_email_format(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
        
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
        
    if len(email) > 254:  # RFC 5321
        return False, "Email address is too long"
        
    return True, None


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """
    Validate username format and requirements.
    
    Args:
        username: Username to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"
        
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
        
    if len(username) > 150:
        return False, "Username cannot exceed 150 characters"
        
    import re
    if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
        return False, "Username can only contain letters, numbers, underscore, dot, and hyphen"
        
    return True, None


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validate password meets minimum security requirements.
    
    Args:
        password: Password to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
        
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
        
    if len(password) > 128:
        return False, "Password is too long"
        
    # Check for at least one number
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"
        
    # Check for at least one letter
    if not any(char.isalpha() for char in password):
        return False, "Password must contain at least one letter"
        
    return True, None
