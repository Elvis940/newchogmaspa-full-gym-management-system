from django import forms
from django.core.exceptions import ValidationError
from accounts.models import CustomUser
from .models import ServicePackage
from .models import Staff, StaffAttendance

class ClientForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
            'id': 'password'
        }),
        required=False
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'id': 'confirmPassword'
        }),
        required=False
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number (+250xxxxxxxxx)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            # Ensure phone number starts with +250
            if not phone_number.startswith('+250'):
                raise ValidationError('Phone number must start with +250')
            # Ensure phone number has correct length
            if len(phone_number) != 13:
                raise ValidationError('Phone number must be 12 digits total (including +250)')
            
            # Check if phone number already exists (excluding current instance if editing)
            if CustomUser.objects.filter(phone_number=phone_number).exists():
                if not self.instance or self.instance.phone_number != phone_number:
                    raise ValidationError('This phone number is already registered.')
        
        return phone_number
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email already exists (excluding current instance if editing)
            if CustomUser.objects.filter(email=email).exists():
                if not self.instance or self.instance.email != email:
                    raise ValidationError('This email address is already registered.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        # Only validate passwords if creating new user or changing password
        if not self.instance.pk or password1 or password2:
            if password1 != password2:
                raise ValidationError("Passwords don't match")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.CLIENT  # Always set role to client
        
        # Set password if provided
        if self.cleaned_data.get('password1'):
            user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
        return user
    
class ServicePackageForm(forms.ModelForm):
    class Meta:
        model = ServicePackage
        fields = ['name', 'service_type', 'description', 'price', 'tickets_included', 'validity_days', 'is_active', 'auto_renew']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter package name'
            }),
            'service_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter package description'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter price in RWF'
            }),
            'tickets_included': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '0 for unlimited'
            }),
            'validity_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'auto_renew': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_tickets_included(self):
        tickets = self.cleaned_data.get('tickets_included')
        if tickets is None:
            raise ValidationError('Please enter a valid number of tickets')
        return tickets
    
    def clean_validity_days(self):
        days = self.cleaned_data.get('validity_days')
        if days < 1:
            raise ValidationError('Validity must be at least 1 day')
        return days
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price < 0:
            raise ValidationError('Price cannot be negative')
        return price
    



class StaffForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'})
    )
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    
    class Meta:
        model = Staff
        fields = ['staff_id', 'role', 'department', 'hire_date', 'salary', 'hourly_rate', 
                 'status', 'shifts', 'qualifications', 'emergency_contact', 'emergency_phone', 'notes']
        widgets = {
            'staff_id': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'shifts': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'qualifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_staff_id(self):
        staff_id = self.cleaned_data.get('staff_id')
        if Staff.objects.filter(staff_id=staff_id).exists():
            if not self.instance or self.instance.staff_id != staff_id:
                raise ValidationError('This staff ID is already in use.')
        return staff_id

# admin_app/forms.py
class StaffAttendanceForm(forms.ModelForm):
    staff = forms.ModelChoiceField(
        queryset=Staff.objects.filter(status='active'),
        empty_label="Select staff member",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    
    class Meta:
        model = StaffAttendance
        fields = ['staff', 'date', 'check_in', 'check_out', 'status', 'hours_worked', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_in': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'check_out': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'hours_worked': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }