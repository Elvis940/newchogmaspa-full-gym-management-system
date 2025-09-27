from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a password',
            'id': 'password'
        })
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'id': 'confirmPassword'
        })
    )
    user_type = forms.ChoiceField(
        label="I want to register as",
        choices=[('', 'Select account type')] + CustomUser.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'userType'
        })
    )
    terms = forms.BooleanField(
        label="I agree to the Terms of Service and Privacy Policy",
        required=True,
        error_messages={'required': 'You must accept the terms and conditions'}
    )

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'user_type', 'password1', 'password2')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name',
                'id': 'firstName'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name',
                'id': 'lastName'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email',
                'id': 'email'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your phone number (+250xxxxxxxxx)',
                'id': 'phone'
            }),
        }
        error_messages = {
            'email': {
                'unique': 'This email address is already registered.',
            },
            'phone_number': {
                'unique': 'This phone number is already registered.',
            }
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
            
            # Check if phone number already exists (excluding current instance if updating)
            if CustomUser.objects.filter(phone_number=phone_number).exists():
                if not self.instance or self.instance.phone_number != phone_number:
                    raise ValidationError('This phone number is already registered.')
        
        return phone_number

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email already exists (excluding current instance if updating)
            if CustomUser.objects.filter(email=email).exists():
                if not self.instance or self.instance.email != email:
                    raise ValidationError('This email address is already registered.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data['user_type']
        user.username = self.cleaned_data['email']  # Use email as username
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your phone number (+250xxxxxxxxx)'
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
            
            # Check if phone number already exists (excluding current user)
            if CustomUser.objects.filter(phone_number=phone_number).exclude(id=self.instance.id).exists():
                raise ValidationError('This phone number is already registered.')
        
        return phone_number
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email already exists (excluding current user)
            if CustomUser.objects.filter(email=email).exclude(id=self.instance.id).exists():
                raise ValidationError('This email address is already registered.')
        return email


