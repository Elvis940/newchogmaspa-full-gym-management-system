# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Appointment, UserServicePackage
from datetime import timedelta

@receiver(post_save, sender=Appointment)
def create_user_service_package(sender, instance, created, **kwargs):
    """
    Create UserServicePackage when appointment is confirmed by admin
    """
    if instance.status == 'confirmed' and not created:  # Only when status changes to confirmed
        # Check if package already exists to avoid duplicates
        if not UserServicePackage.objects.filter(
            user=instance.client, 
            service_package=instance.service,
            status='active'
        ).exists():
            
            UserServicePackage.objects.create(
                user=instance.client,
                service_package=instance.service,
                start_date=instance.appointment_date,
                end_date=instance.appointment_date + timedelta(days=instance.service.validity_days),
                total_tickets=instance.service.tickets_included,
                tickets_used=0,
                status='active'
            )

# Don't forget to import signals in apps.py or __init__.py