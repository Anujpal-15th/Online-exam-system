"""
Email Notification Service for EduExam
Handles all email notifications throughout the system
"""

from django.core.mail import EmailMultiAlternatives, send_mail, get_connection
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import logging
import threading
from queue import Queue

logger = logging.getLogger(__name__)


class EmailService:
    """Centralized email service for all notification types."""
    
    @staticmethod
    def _send_email(subject, template_name, context, recipient_email, html_template_name=None, _connection=None):
        """
        Base method to send emails with text and optional HTML content.
        
        Args:
            subject: Email subject line
            template_name: Path to text template
            context: Template context dictionary
            recipient_email: Recipient email address
            html_template_name: Optional HTML template path
            _connection: Optional reusable SMTP connection for bulk sending
        """
        try:
            # Render text content
            text_content = render_to_string(template_name, context)
            
            # Get sender email
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eduexam.com')
            
            if html_template_name:
                # Send with HTML alternative
                html_content = render_to_string(html_template_name, context)
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=from_email,
                    to=[recipient_email],
                    connection=_connection  # Reuse connection if provided
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            else:
                # Send text-only
                send_mail(
                    subject=subject,
                    message=text_content,
                    from_email=from_email,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                    connection=_connection  # Reuse connection if provided
                )
            
            logger.info(f"Email sent successfully to {recipient_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False
    
    @classmethod
    def send_test_published_notification(cls, test, student, _connection=None):
        """
        Notify student when a new test is published.
        
        Args:
            test: Test object
            student: CustomUser object (student)
            _connection: Optional reusable SMTP connection
        """
        from django.http import HttpRequest
        
        # Create mock request for email templates
        mock_request = HttpRequest()
        mock_request.META['HTTP_HOST'] = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
        mock_request.META['wsgi.url_scheme'] = 'https' if getattr(settings, 'USE_HTTPS', False) else 'http'
        
        subject = f'New Test Available: {test.title}'
        context = {
            'student': student,
            'test': test,
            'site_name': 'EduExam',
            'request': mock_request,
        }
        return cls._send_email(
            subject=subject,
            template_name='emails/test_published.txt',
            context=context,
            recipient_email=student.email,
            html_template_name='emails/test_published.html',
            _connection=_connection
        )
    
    @classmethod
    def send_grade_notification(cls, attempt):
        """
        Notify student when their test has been graded.
        
        Args:
            attempt: TestAttempt object
        """
        from django.http import HttpRequest
        
        # Create mock request for email templates
        mock_request = HttpRequest()
        mock_request.META['HTTP_HOST'] = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
        mock_request.META['wsgi.url_scheme'] = 'https' if getattr(settings, 'USE_HTTPS', False) else 'http'
        
        percentage = (attempt.total_score / attempt.test.total_marks * 100) if attempt.test.total_marks > 0 else 0
        status = 'Passed' if percentage >= 50 else 'Failed'
        
        subject = f'Your test "{attempt.test.title}" has been graded'
        context = {
            'student': attempt.student,
            'attempt': attempt,
            'test': attempt.test,
            'percentage': round(percentage, 2),
            'status': status,
            'site_name': 'EduExam',
            'request': mock_request,
        }
        return cls._send_email(
            subject=subject,
            template_name='emails/grade_notification.txt',
            context=context,
            recipient_email=attempt.student.email,
            html_template_name='emails/grade_notification.html'
        )
    
    @classmethod
    def send_test_reminder(cls, test, student, hours_remaining, _connection=None):
        """
        Send reminder to student about upcoming test deadline.
        
        Args:
            test: Test object
            student: CustomUser object
            hours_remaining: Hours until test deadline
            _connection: Optional reusable SMTP connection
        """
        from django.http import HttpRequest
        
        # Create mock request for email templates
        mock_request = HttpRequest()
        mock_request.META['HTTP_HOST'] = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
        mock_request.META['wsgi.url_scheme'] = 'https' if getattr(settings, 'USE_HTTPS', False) else 'http'
        
        subject = f'Reminder: Test "{test.title}" - {hours_remaining}h remaining'
        context = {
            'student': student,
            'test': test,
            'hours_remaining': hours_remaining,
            'site_name': 'EduExam',
            'request': mock_request,
        }
        return cls._send_email(
            subject=subject,
            template_name='emails/test_reminder.txt',
            context=context,
            recipient_email=student.email,
            html_template_name='emails/test_reminder.html',
            _connection=_connection
        )
    
    @classmethod
    def send_test_submission_confirmation(cls, attempt):
        """
        Send confirmation to student after test submission.
        
        Args:
            attempt: TestAttempt object
        """
        from django.http import HttpRequest
        
        # Create mock request for email templates
        mock_request = HttpRequest()
        mock_request.META['HTTP_HOST'] = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
        mock_request.META['wsgi.url_scheme'] = 'https' if getattr(settings, 'USE_HTTPS', False) else 'http'
        
        subject = f'Test Submitted: {attempt.test.title}'
        context = {
            'student': attempt.student,
            'attempt': attempt,
            'test': attempt.test,
            'site_name': 'EduExam',
            'request': mock_request,
        }
        return cls._send_email(
            subject=subject,
            template_name='emails/test_submission.txt',
            context=context,
            recipient_email=attempt.student.email,
            html_template_name='emails/test_submission.html'
        )
    
    @classmethod
    def send_account_blocked_notification(cls, user, reason=''):
        """
        Notify user that their account has been blocked.
        
        Args:
            user: CustomUser object
            reason: Optional reason for blocking
        """
        subject = 'Your EduExam Account Has Been Blocked'
        context = {
            'user': user,
            'reason': reason,
            'site_name': 'EduExam',
        }
        return cls._send_email(
            subject=subject,
            template_name='emails/account_blocked.txt',
            context=context,
            recipient_email=user.email,
            html_template_name='emails/account_blocked.html'
        )
    
    @classmethod
    def send_account_unblocked_notification(cls, user):
        """
        Notify user that their account has been unblocked.
        
        Args:
            user: CustomUser object
        """
        subject = 'Your EduExam Account Has Been Reactivated'
        context = {
            'user': user,
            'site_name': 'EduExam',
        }
        return cls._send_email(
            subject=subject,
            template_name='emails/account_unblocked.txt',
            context=context,
            recipient_email=user.email,
            html_template_name='emails/account_unblocked.html'
        )
    
    @classmethod
    def send_certificate_notification(cls, certificate):
        """
        Notify student when they earn a certificate.
        
        Args:
            certificate: Certificate object
        """
        from django.http import HttpRequest
        
        # Create mock request for email templates
        mock_request = HttpRequest()
        mock_request.META['HTTP_HOST'] = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
        mock_request.META['wsgi.url_scheme'] = 'https' if getattr(settings, 'USE_HTTPS', False) else 'http'
        
        subject = f'Certificate Earned: {certificate.test_attempt.test.title}'
        context = {
            'student': certificate.test_attempt.student,
            'certificate': certificate,
            'test': certificate.test_attempt.test,
            'attempt': certificate.test_attempt,
            'site_name': 'EduExam',
            'request': mock_request,
        }
        return cls._send_email(
            subject=subject,
            template_name='emails/certificate_earned.txt',
            context=context,
            recipient_email=certificate.test_attempt.student.email,
            html_template_name='emails/certificate_earned.html'
        )
    
    @classmethod
    def send_welcome_email(cls, user):
        """
        Send welcome email to newly registered user.
        
        Args:
            user: CustomUser object
        """
        from django.http import HttpRequest
        
        # Create mock request for email templates
        mock_request = HttpRequest()
        mock_request.META['HTTP_HOST'] = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
        mock_request.META['wsgi.url_scheme'] = 'https' if getattr(settings, 'USE_HTTPS', False) else 'http'
        
        role_name = user.get_user_type_display()
        subject = f'Welcome to EduExam - {role_name} Account Created'
        context = {
            'user': user,
            'role_name': role_name,
            'site_name': 'EduExam',
            'request': mock_request,
        }
        return cls._send_email(
            subject=subject,
            template_name='emails/welcome.txt',
            context=context,
            recipient_email=user.email,
            html_template_name='emails/welcome.html'
        )
    
    @classmethod
    def send_bulk_notification(cls, subject, message, recipients):
        """
        Send bulk email to multiple recipients.
        
        Args:
            subject: Email subject
            message: Email message (plain text)
            recipients: List of email addresses
        """
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eduexam.com')
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipients,
                fail_silently=False,
            )
            logger.info(f"Bulk email sent to {len(recipients)} recipients: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send bulk email: {str(e)}")
            return False
    
    @classmethod
    def send_bulk_emails_async(cls, email_tasks):
        """
        Send multiple emails asynchronously in background thread with connection reuse.
        
        Args:
            email_tasks: List of tuples (method_name, args, kwargs)
                        Example: [('send_test_published_notification', (test, student), {})]
        
        Returns:
            Thread object (for testing/waiting if needed)
        """
        def worker():
            # Open a persistent connection for all emails
            connection = get_connection(
                backend=getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend'),
                fail_silently=True,
            )
            connection.open()
            
            success_count = 0
            fail_count = 0
            
            try:
                for method_name, args, kwargs in email_tasks:
                    try:
                        method = getattr(cls, method_name)
                        # Call the method (it will use the existing connection)
                        method(*args, **kwargs, _connection=connection)
                        success_count += 1
                    except Exception as e:
                        fail_count += 1
                        logger.error(f"Failed to send email via {method_name}: {str(e)}")
            finally:
                connection.close()
                logger.info(f"Bulk async email completed: {success_count} sent, {fail_count} failed")
        
        # Start background thread
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread
    
    @classmethod
    def send_help_request_notification(cls, help_request, to_admin=True):
        """
        Notify admin about new help request or notify student about response.
        
        Args:
            help_request: HelpRequest object
            to_admin: If True, notify admin; if False, notify student
        """
        if to_admin:
            # Notify admin about new help request
            subject = f'New Help Request: {help_request.subject}'
            context = {
                'help_request': help_request,
                'student': help_request.student,
                'site_name': 'EduExam',
            }
            # Get admin emails
            from accounts.models import CustomUser
            admin_emails = list(CustomUser.objects.filter(
                user_type=1, is_active=True
            ).values_list('email', flat=True))
            
            if admin_emails:
                return cls.send_bulk_notification(
                    subject=subject,
                    message=f"Student: {help_request.student.get_full_name()}\n"
                            f"Subject: {help_request.subject}\n"
                            f"Message: {help_request.message}\n\n"
                            f"Please log in to respond.",
                    recipients=admin_emails
                )
        else:
            # Notify student about response
            subject = f'Response to Your Help Request: {help_request.subject}'
            context = {
                'help_request': help_request,
                'student': help_request.student,
                'site_name': 'EduExam',
            }
            return cls._send_email(
                subject=subject,
                template_name='emails/help_request_response.txt',
                context=context,
                recipient_email=help_request.student.email,
                html_template_name='emails/help_request_response.html'
            )
