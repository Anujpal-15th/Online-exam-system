"""
Management command to send test reminders to students.

Usage:
    python manage.py send_test_reminders

This command should be run periodically (e.g., via cron job or task scheduler)
to notify students about upcoming tests within the next 24 hours.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from exams.models import Test
from questions.models import Notification


class Command(BaseCommand):
    help = 'Send test reminder notifications to students for tests starting within 24 hours'

    def handle(self, *args, **options):
        now = timezone.now()
        tomorrow = now + timedelta(hours=24)
        
        # Find tests starting within next 24 hours
        upcoming_tests = Test.objects.filter(
            start_at__gte=now,
            start_at__lte=tomorrow
        )
        
        User = get_user_model()
        students = User.objects.filter(user_type=3)
        
        notification_count = 0
        
        for test in upcoming_tests:
            # Check if reminder was already sent (avoid duplicate reminders)
            existing_reminders = Notification.objects.filter(
                notification_type='test_reminder',
                title__contains=test.title,
                created_at__gte=now - timedelta(hours=24)
            ).count()
            
            if existing_reminders > 0:
                self.stdout.write(
                    self.style.WARNING(f'Reminder already sent for: {test.title}')
                )
                continue
            
            # Send reminder to all students
            for student in students:
                hours_until_test = int((test.start_at - now).total_seconds() / 3600)
                
                Notification.objects.create(
                    user=student,
                    title=f"Test Reminder: {test.title}",
                    message=f"Reminder: The test '{test.title}' starts in {hours_until_test} hours on {test.start_at.strftime('%B %d, %Y at %I:%M %p')}. Make sure you're prepared!",
                    notification_type='test_reminder',
                    link=f'/questions/start/{test.id}/'
                )
                notification_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'Sent reminders for: {test.title} ({students.count()} students)')
            )
        
        if notification_count == 0:
            self.stdout.write(
                self.style.WARNING('No upcoming tests found or reminders already sent')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully sent {notification_count} test reminder notifications')
            )
