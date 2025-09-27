from django import forms
from django.utils import timezone
from datetime import datetime, time
from core.models import Appointment
from admin_app.models import ServicePackage

class AppointmentForm(forms.ModelForm):
    service = forms.ModelChoiceField(
        queryset=ServicePackage.objects.filter(is_active=True),
        empty_label="Select a service",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'min': timezone.now().date()}),
        initial=timezone.now().date()
    )
    appointment_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        initial=time(9, 0)
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any special requests or notes'})
    )
    tickets_included = forms.IntegerField(
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'readonly': 'readonly',
            'placeholder': 'Select a service to see tickets included'
        })
    )
    
    class Meta:
        model = Appointment
        fields = ['service', 'appointment_date', 'appointment_time', 'notes', 'tickets_included']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If we're editing an existing appointment, set the tickets_included value
        if self.instance and self.instance.pk:
            self.fields['tickets_included'].initial = self.instance.tickets_included
    
    def clean_appointment_date(self):
        date = self.cleaned_data.get('appointment_date')
        if date < timezone.now().date():
            raise forms.ValidationError("Appointment date cannot be in the past.")
        return date
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('appointment_date')
        time_val = cleaned_data.get('appointment_time')
        service = cleaned_data.get('service')
        
        # Set tickets_included from the selected service
        if service:
            cleaned_data['tickets_included'] = service.tickets_included
        
        if date and time_val:
            # Check if the appointment datetime is in the past
            appointment_datetime = timezone.make_aware(
                datetime.combine(date, time_val)
            )
            if appointment_datetime < timezone.now():
                raise forms.ValidationError("Appointment date and time cannot be in the past.")
            
            # Check for existing appointments at the same time
            existing_appointments = Appointment.objects.filter(
                appointment_date=date,
                appointment_time=time_val,
                status__in=['pending', 'confirmed']
            )
            if self.instance and self.instance.pk:
                existing_appointments = existing_appointments.exclude(pk=self.instance.pk)
                
            if existing_appointments.exists():
                raise forms.ValidationError("This time slot is already booked. Please choose another time.")
        
        return cleaned_data
    
    def save(self, commit=True):
        appointment = super().save(commit=False)
        
        # Set tickets_included from the service
        if appointment.service:
            appointment.tickets_included = appointment.service.tickets_included
        
        if commit:
            appointment.save()
        
        return appointment


class GymSessionCheckForm(forms.Form):
    session_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'max': timezone.now().date(),
            'class': 'form-control'
        }),
        initial=timezone.now().date(),
        label="Session Date"
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        }),
        initial=timezone.now().time().strftime('%H:%M'),
        label="Start Time"
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        }),
        required=True,  # Changed to required
        label="End Time"
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Describe your workout or any notes...'
        }),
        required=False,
        help_text="Optional notes about your session",
        label="Session Notes"
    )