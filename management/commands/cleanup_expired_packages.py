# management/commands/cleanup_expired_packages.py
from django.core.management.base import BaseCommand
from client import models
from core.models import UserServicePackage
from django.utils import timezone

class Command(BaseCommand):
    help = 'Clean up expired packages and packages with no tickets'
    
    def handle(self, *args, **options):
        # Expire packages that are past their end date
        expired_packages = UserServicePackage.objects.filter(
            status='active',
            end_date__lt=timezone.now().date()
        )
        expired_count = expired_packages.update(status='expired')
        
        # Expire packages with no tickets left
        empty_packages = UserServicePackage.objects.filter(
            status='active',
            total_tickets=models.F('tickets_used')
        )
        empty_count = empty_packages.update(status='expired')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully expired {expired_count} outdated packages and {empty_count} empty packages')
        )