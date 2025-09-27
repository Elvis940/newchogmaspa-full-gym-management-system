from django.db import models
from django.core.validators import MinValueValidator
# admin_app/models.py
from django.db import models
from accounts.models import CustomUser
from django.core.validators import MinValueValidator, MaxValueValidator

from accounts.models import CustomUser
class ServicePackage(models.Model):
    SERVICE_TYPES = [
        ('gym', 'Gym'),
        ('sauna', 'Sauna'),
        ('massage', 'Massage'),
    ]
    
    DURATION_UNITS = [
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ]
    
    name = models.CharField(max_length=100)
    service_type = models.CharField(max_length=10, choices=SERVICE_TYPES)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], help_text="Price in RWF")
    tickets_included = models.PositiveIntegerField(help_text="Number of tickets included (0 for unlimited)")
    validity_days = models.PositiveIntegerField(help_text="Package validity in days")
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=False, help_text="Auto-renew package when expired")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['service_type', 'price']
        verbose_name = 'Service Package'
        verbose_name_plural = 'Service Packages'
    
    def __str__(self):
        return f"{self.name} - {self.price} RWF"
    
    def is_unlimited(self):
        return self.tickets_included == 0
    
    def get_service_type_display(self):
        return dict(self.SERVICE_TYPES).get(self.service_type, self.service_type)
    
    def get_price_rwf(self):
        return f"{self.price:,.2f} RWF"



class Staff(models.Model):
    STAFF_ROLES = [
        ('receptionist', 'Receptionist'),
        ('trainer', 'Trainer'),
        ('therapist', 'Therapist'),
        ('cleaner', 'Cleaner'),
        ('manager', 'Manager'),
        ('other', 'Other'),
    ]
    
    STAFF_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
    ]
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='staff_profile')
    staff_id = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=STAFF_ROLES)
    department = models.CharField(max_length=100, blank=True)
    hire_date = models.DateField()
    salary = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True)
    status = models.CharField(max_length=20, choices=STAFF_STATUS, default='active')
    shifts = models.TextField(blank=True, help_text="Work schedule/shifts")
    qualifications = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=15, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-hire_date']
        verbose_name_plural = 'Staff'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"
    
    @property
    def full_name(self):
        return self.user.get_full_name()
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def phone(self):
        return self.user.phone_number

class StaffAttendance(models.Model):
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('early_departure', 'Early Departure'),
        ('sick_leave', 'Sick Leave'),
        ('vacation', 'Vacation'),
    ]
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='present')
    hours_worked = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['staff', 'date']
    
    def __str__(self):
        return f"{self.staff.full_name} - {self.date} - {self.status}"    