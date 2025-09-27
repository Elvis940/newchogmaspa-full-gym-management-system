from django.core.management.base import BaseCommand
from core.notifications import check_low_tickets

class Command(BaseCommand):
    help = 'Check for users with low tickets and send notifications'
    
    def handle(self, *args, **options):
        check_low_tickets()
        self.stdout.write(
            self.style.SUCCESS('Successfully checked for low tickets and sent notifications')
        )