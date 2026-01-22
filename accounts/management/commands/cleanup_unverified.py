"""
Management command to clean up old unverified user accounts.

Usage:
    python manage.py cleanup_unverified
    python manage.py cleanup_unverified --days 7
    python manage.py cleanup_unverified --dry-run
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomUser


class Command(BaseCommand):
    help = 'Delete unverified user accounts older than specified days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete accounts unverified for this many days (default: 7)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        old_unverified = CustomUser.objects.filter(
            is_active=False,
            date_joined__lt=cutoff_date
        )
        
        count = old_unverified.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS(
                f'No unverified accounts older than {days} days found.'
            ))
            return
        
        self.stdout.write(f'\nFound {count} unverified account(s) older than {days} days:')
        for user in old_unverified:
            days_old = (timezone.now() - user.date_joined).days
            self.stdout.write(f'  - {user.username} ({user.email}) - {days_old} days old')
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\n[DRY RUN] Would delete {count} account(s). Run without --dry-run to actually delete.'
            ))
        else:
            old_unverified.delete()
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Successfully deleted {count} unverified account(s).'
            ))
