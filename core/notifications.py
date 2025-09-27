# core/notifications.py
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Notification

def create_notification(user, notification_type, message, is_urgent=False, related_object=None):
    """Create a notification for a user"""
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        message=message,
        is_urgent=is_urgent
    )
    
    if related_object:
        notification.related_object_id = related_object.id
        notification.related_content_type = related_object.__class__.__name__.lower()
        notification.save()
    
    return notification

def send_email_notification(user, subject, template_name, context):
    """Send email notification"""
    try:
        html_message = render_to_string(f'emails/{template_name}', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def check_low_tickets():
    """Check for users with low tickets and send notifications"""
    from .models import UserServicePackage
    from django.utils import timezone
    
    low_ticket_packages = UserServicePackage.objects.filter(
        status='active',
        end_date__gte=timezone.now().date()
    )
    
    for package in low_ticket_packages:
        remaining_tickets = package.tickets_remaining()
        if 0 < remaining_tickets <= 2:
            create_notification(
                package.user,
                'low_tickets',
                f'Low tickets warning: You have only {remaining_tickets} ticket(s) remaining in your {package.service_package.name} package',
                is_urgent=remaining_tickets == 1,
                related_object=package
            )
            
            send_email_notification(
                package.user,
                f'Low Tickets Warning - {package.service_package.name}',
                'low_tickets.html',
                {
                    'package': package,
                    'remaining_tickets': remaining_tickets,
                    'client': package.user
                }
            )