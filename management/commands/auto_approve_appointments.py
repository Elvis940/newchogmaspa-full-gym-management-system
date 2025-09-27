from django.core.management.base import BaseCommand
from django.utils import timezone
from client.models import Appointment

class Command(BaseCommand):
    help = 'Automatically approve appointments that have been pending for more than 30 minutes'

    def handle(self, *args, **options):
        # Find appointments that need auto-approval
        pending_appointments = Appointment.objects.filter(
            status='pending',
            auto_approve_at__lte=timezone.now(),
            admin_action_required=True
        )
        
        approved_count = 0
        for appointment in pending_appointments:
            appointment.status = 'confirmed'
            appointment.admin_action_required = False
            appointment.save()
            
            # Send confirmation email
            appointment.send_confirmation_email()
            
            approved_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Auto-approved appointment for {appointment.client.get_full_name()} '
                    f'on {appointment.appointment_date} at {appointment.appointment_time}'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully auto-approved {approved_count} appointments')
        )