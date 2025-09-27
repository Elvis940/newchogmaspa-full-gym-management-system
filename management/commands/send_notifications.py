# management/commands/send_notifications.py
from django.core.management.base import BaseCommand
from core.notifications import run_all_notification_checks

class Command(BaseCommand):
    help = 'Send scheduled notifications and reminders'
    
    def handle(self, *args, **options):
        run_all_notification_checks()
        self.stdout.write(
            self.style.SUCCESS('Successfully sent all notifications')
        )