from django import template
from pytz import timezone
from core.models import UserServicePackage

register = template.Library()

@register.filter
def get_active_package(user):
    try:
        return UserServicePackage.objects.filter(
            user=user, 
            status='active',
            end_date__gte=timezone.now().date()
        ).first()
    except:
        return None