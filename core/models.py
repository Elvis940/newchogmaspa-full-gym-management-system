# core/models.py
from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from accounts.models import CustomUser
from admin_app.models import ServicePackage

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    client = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='appointments')
    service = models.ForeignKey(ServicePackage, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    tickets_included = models.PositiveIntegerField(default=0, help_text="Number of tickets included in the package")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_action_required = models.BooleanField(default=True)
    auto_approve_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['appointment_date', 'appointment_time']
    
    def __str__(self):
        return f"{self.client.get_full_name()} - {self.service.name} on {self.appointment_date} at {self.appointment_time}"
    
    def is_past_due(self):
        return timezone.now() > timezone.make_aware(
            timezone.datetime.combine(self.appointment_date, self.appointment_time)
        )
    
    def save(self, *args, **kwargs):
        # Check if status is changing to 'confirmed'
        if self.pk:  # Only for existing instances
            old_status = Appointment.objects.get(pk=self.pk).status
            if old_status != 'confirmed' and self.status == 'confirmed':
                # Create UserServicePackage when admin confirms
                from datetime import timedelta
                UserServicePackage.objects.create(
                    user=self.client,
                    service_package=self.service,
                    start_date=self.appointment_date,
                    end_date=self.appointment_date + timedelta(days=self.service.validity_days),
                    total_tickets=self.service.tickets_included,
                    tickets_used=0,
                    status='active'
                )
        
        # Set auto_approve_at when appointment is created
        if not self.pk and self.status == 'pending':
            self.auto_approve_at = timezone.now() + timezone.timedelta(minutes=30)
            self.admin_action_required = True
            
            # Set tickets_included from the service package
            if self.service:
                self.tickets_included = self.service.tickets_included
                
        super().save(*args, **kwargs)
    
    def send_confirmation_email(self):
        """Send confirmation email to client when appointment is approved"""
        subject = f"Your Appointment at New Chogma-SPA Has Been Confirmed"
        
        html_message = render_to_string('emails/appointment_confirmation.html', {
            'appointment': self,
            'client': self.client
        })
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [self.client.email],
                html_message=html_message,
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

class UserServicePackage(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='service_packages')
    service_package = models.ForeignKey(ServicePackage, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField()
    end_date = models.DateField()
    total_tickets = models.PositiveIntegerField(default=0)
    tickets_used = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    auto_renew = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-purchase_date']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.service_package.name}"
    
    def is_active(self):
        return self.status == 'active' and self.end_date >= timezone.now().date()
    
    def days_remaining(self):
        return (self.end_date - timezone.now().date()).days
    
    def tickets_remaining(self):
        return self.total_tickets - self.tickets_used
    
    def use_ticket(self):
        """Deduct one ticket from the package and create notifications for low tickets"""
        if self.tickets_used < self.total_tickets:
            self.tickets_used += 1
            remaining_tickets = self.total_tickets - self.tickets_used
            
            # Create notification for low tickets (2 or fewer remaining)
            if remaining_tickets <= 2 and remaining_tickets > 0:
                # Import here to avoid circular imports
                from core.notifications import create_notification, send_email_notification
                
                create_notification(
                    self.user,
                    'low_tickets',
                    f'Low tickets warning: You have only {remaining_tickets} ticket(s) remaining in your {self.service_package.name} package',
                    is_urgent=remaining_tickets == 1,
                    related_object=self
                )
                
                # Send email notification
                send_email_notification(
                    self.user,
                    f'Low Tickets Warning - {self.service_package.name}',
                    'low_tickets.html',
                    {
                        'package': self,
                        'remaining_tickets': remaining_tickets,
                        'client': self.user
                    }
                )
            
            self.save()
            
            # Check if package should be expired after using ticket
            if remaining_tickets == 0:
                self.status = 'expired'
                self.save()
                
            return True
        return False

class AttendanceRecord(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='attendance_records')
    service_package = models.ForeignKey(ServicePackage, on_delete=models.CASCADE)
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    session_type = models.CharField(max_length=20)  # gym, sauna, massage
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-check_in_time']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.session_type} - {self.check_in_time}"

# ONLY ONE NOTIFICATION MODEL - REMOVED THE DUPLICATE
class Notification(models.Model):
    TYPE_CHOICES = [
        ('session_reminder', 'Session Reminder'),
        ('package_expiry', 'Package Expiry'),
        ('low_tickets', 'Low Tickets'),
        ('attendance', 'Attendance Confirmation'),
        ('appointment_reminder', 'Appointment Reminder'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    related_object_id = models.PositiveIntegerField(null=True, blank=True)  # For linking to appointments/packages
    related_content_type = models.CharField(max_length=50, null=True, blank=True)  # e.g., 'appointment', 'package'
    is_urgent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_notification_type_display()}"