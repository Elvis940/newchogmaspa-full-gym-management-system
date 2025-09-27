from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
import uuid

from django.forms import ValidationError

class CustomUser(AbstractUser):
    # User roles
    CLIENT = 'client'
    ADMIN = 'admin'
    STAFF = 'staff'
    ROLE_CHOICES = [
        (CLIENT, 'Client'),
        (ADMIN, 'Admin'),
        (STAFF, 'Staff'),
        
    ]
    
    # Phone number validator for +250 followed by 9 digits
    phone_regex = RegexValidator(
        regex=r'^\+250\d{9}$',
        message="Phone number must be in the format: '+250xxxxxxxxx' where x is a digit (12 digits total)"
    )
    
    # Additional fields
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=CLIENT)
    phone_number = models.CharField(
        max_length=15, 
        blank=True, 
        validators=[phone_regex],
        unique=True,
        error_messages={'unique': 'A user with this phone number already exists.'}
    )
    email = models.EmailField(unique=True, error_messages={'unique': 'A user with this email already exists.'})
    qr_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    # Add related_name to avoid clashes with default User model
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="customuser_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="customuser_set",
        related_query_name="user",
    )
    
    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def clean(self):
        super().clean()
        # Ensure phone number starts with +250 if provided
        if self.phone_number and not self.phone_number.startswith('+250'):
            raise ValidationError({'phone_number': 'Phone number must start with +250'})
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


