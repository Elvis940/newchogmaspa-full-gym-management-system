import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from requests import request
from accounts.models import CustomUser
from django.utils import timezone
from datetime import timedelta
from accounts.forms import UserProfileForm
from admin_app.models import ServicePackage
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from core.models import UserServicePackage, AttendanceRecord, Notification
from core.utils import generate_qr_code, send_qr_code_email, send_session_reminder
from django.shortcuts import render, redirect, get_object_or_404
from datetime import timedelta, datetime
from core.models import Appointment
from .forms import AppointmentForm, GymSessionCheckForm


@login_required
def client_dashboard(request):
    # Ensure only clients can access this view
    if request.user.role != CustomUser.CLIENT:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get user-specific real data
    user = request.user
    today = timezone.now().date()
    
    # Get active packages with remaining tickets
    active_packages = UserServicePackage.objects.filter(
        user=user,
        status='active',
        end_date__gte=today
    )
    
    # Calculate remaining tickets across all active packages
    total_tickets = sum(package.total_tickets for package in active_packages)
    tickets_used = sum(package.tickets_used for package in active_packages)
    tickets_remaining = total_tickets - tickets_used
    
    # Calculate utilization percentage
    utilization_percent = (tickets_used / total_tickets * 100) if total_tickets > 0 else 0
    
    # Get upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        client=user,
        appointment_date__gte=today,
        status__in=['pending', 'confirmed']
    ).order_by('appointment_date', 'appointment_time')[:5]
    
    # Get attendance history
    attendance_history = AttendanceRecord.objects.filter(
        user=user
    ).order_by('-check_in_time')[:5]
    
    context = {
        'user': user,
        'active_packages': active_packages,
        'upcoming_appointments': upcoming_appointments,
        'attendance_history': attendance_history,
        'tickets_remaining': tickets_remaining,
        'utilization_percent': utilization_percent,
        'active_tab': 'dashboard',
    }
    return render(request, 'client/dashboard.html', context)



@login_required
def client_profile(request):
    # Ensure only clients can access this view
    if request.user.role != CustomUser.CLIENT:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('client:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileForm(instance=user)
    
    context = {
        'user': user,
        'form': form,
        'active_tab': 'profile',
    }
    return render(request, 'client/profile.html', context)

@login_required
def client_services(request):
    # Ensure only clients can access this view
    if request.user.role != CustomUser.CLIENT:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get all active service packages
    services = ServicePackage.objects.filter(is_active=True).order_by('service_type', 'price')
    
    # Group by service type for display
    service_types = {
        'gym': services.filter(service_type='gym'),
        'sauna': services.filter(service_type='sauna'),
        'massage': services.filter(service_type='massage'),
    }
    
    context = {
        'user': request.user,
        'services': services,
        'service_types': service_types,
        'active_tab': 'services',
    }
    return render(request, 'client/services.html', context)


@login_required
def client_appointments(request):
    # Ensure only clients can access this view
    if request.user.role != CustomUser.CLIENT:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get user's appointments
    appointments = Appointment.objects.filter(client=request.user).order_by('-appointment_date', '-appointment_time')
    
    # Separate into upcoming and past appointments
    today = timezone.now().date()
    upcoming_appointments = appointments.filter(appointment_date__gte=today, status__in=['pending', 'confirmed'])
    past_appointments = appointments.filter(appointment_date__lt=today) | appointments.filter(status__in=['cancelled', 'completed', 'rejected'])
    
    context = {
        'user': request.user,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'active_tab': 'appointments',
    }
    return render(request, 'client/appointments.html', context)

@login_required
def book_appointment(request):
    # Ensure only clients can access this view
    if request.user.role != CustomUser.CLIENT:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.client = request.user
            
            # Save the appointment (status will be 'pending' by default)
            appointment.save()
            
            # DON'T create UserServicePackage here - wait for admin confirmation
            messages.success(request, 'Your appointment has been booked successfully! It will be active once confirmed by admin.')
            return redirect('client:appointments')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AppointmentForm()
    
    # Get available time slots for today
    today = timezone.now().date()
    available_slots = get_available_time_slots(today)
    
    context = {
        'user': request.user,
        'form': form,
        'available_slots': available_slots,
        'active_tab': 'appointments',
    }
    return render(request, 'client/book_appointment.html', context)

@login_required
def cancel_appointment(request, appointment_id):
    # Ensure only clients can access this view
    if request.user.role != CustomUser.CLIENT:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            appointment = get_object_or_404(Appointment, id=appointment_id, client=request.user)
            
            # Only allow cancelling if appointment is in the future
            if appointment.is_past_due():
                return JsonResponse({'success': False, 'error': 'Cannot cancel past appointments'})
            
            # If appointment was confirmed, remove the tickets from UserServicePackage
            if appointment.status == 'confirmed':
                try:
                    # Use filter() instead of get() to handle multiple packages
                    user_packages = UserServicePackage.objects.filter(
                        user=request.user,
                        service_package=appointment.service,
                        status='active'
                    )
                    
                    if user_packages.exists():
                        # Get the most recent active package
                        user_package = user_packages.latest('purchase_date')
                        
                        # Reduce tickets (but don't go below 0)
                        if user_package.tickets_used >= appointment.service.tickets_included:
                            user_package.tickets_used -= appointment.service.tickets_included
                        else:
                            user_package.tickets_used = 0
                        user_package.save()
                    else:
                        # Package doesn't exist, nothing to remove
                        pass
                except UserServicePackage.DoesNotExist:
                    # Package doesn't exist, nothing to remove
                    pass
                except Exception as e:
                    # Log other errors but don't prevent cancellation
                    print(f"Error adjusting tickets during cancellation: {e}")
            
            appointment.status = 'cancelled'
            appointment.save()
            
            return JsonResponse({'success': True, 'message': 'Appointment cancelled successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def get_available_time_slots(date):
    # This function would typically check against existing appointments
    # and business hours to generate available time slots
    # For now, we'll return a simple list of times
    
    # Business hours: 8 AM to 8 PM
    start_time = datetime.strptime('08:00', '%H:%M').time()
    end_time = datetime.strptime('20:00', '%H:%M').time()
    
    # Generate time slots every 30 minutes
    available_slots = []
    current_time = start_time
    
    while current_time < end_time:
        available_slots.append(current_time.strftime('%H:%M'))
        # Add 30 minutes
        current_time = (datetime.combine(date, current_time) + timedelta(minutes=30)).time()
    
    return available_slots

@login_required
def get_available_slots_for_date(request):
    # Replace request.is_ajax() with a check for the X-Requested-With header
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        date_str = request.GET.get('date')
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            available_slots = get_available_time_slots(date)
            
            # Remove already booked slots
            booked_appointments = Appointment.objects.filter(
                appointment_date=date,
                status__in=['pending', 'confirmed']
            ).values_list('appointment_time', flat=True)
            
            # Convert to string format for comparison
            booked_slots = [t.strftime('%H:%M') for t in booked_appointments]
            available_slots = [slot for slot in available_slots if slot not in booked_slots]
            
            return JsonResponse({'success': True, 'slots': available_slots})
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})
@login_required
def gym_sessions(request):
    # Ensure only clients can access this view
    if request.user.role != CustomUser.CLIENT:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get the current user
    user = request.user
    today = timezone.now().date()
    
    # Get user's active service packages (only non-expired ones with remaining tickets)
    active_packages = UserServicePackage.objects.filter(
        user=user, 
        status='active',
        end_date__gte=today
    )
    
    # Filter out packages that have no tickets left
    active_packages_with_tickets = []
    low_ticket_notification = None
    
    for package in active_packages:
        remaining_tickets = package.tickets_remaining()
        if remaining_tickets > 0:
            active_packages_with_tickets.append(package)
            
            # Check for low tickets (2 or fewer remaining)
            if remaining_tickets <= 2:
                # Create notification if it doesn't exist
                notification, created = Notification.objects.get_or_create(
                    user=user,
                    notification_type='low_tickets',
                    related_object_id=package.id,
                    defaults={
                        'message': f'Low tickets warning: You have only {remaining_tickets} ticket(s) remaining in your {package.service_package.name} package',
                        'is_urgent': remaining_tickets == 1,
                        'related_content_type': 'package'
                    }
                )
                
                # Store the first low ticket notification for display
                if not low_ticket_notification:
                    low_ticket_notification = {
                        'message': notification.message,
                        'remaining_tickets': remaining_tickets,
                        'package_name': package.service_package.name
                    }
        else:
            # Auto-expire packages with no tickets left
            package.status = 'expired'
            package.save()
            
            # Create expiration notification
            Notification.objects.create(
                user=user,
                notification_type='package_expiry',
                message=f'Your {package.service_package.name} package has expired. All tickets have been used.',
                is_urgent=True,
                related_object_id=package.id,
                related_content_type='package'
            )
    
    # Calculate statistics based on PACKAGES with remaining tickets
    total_tickets = sum(package.total_tickets for package in active_packages_with_tickets)
    tickets_used = sum(package.tickets_used for package in active_packages_with_tickets)
    tickets_remaining = total_tickets - tickets_used
    
    # Calculate utilization percentages
    utilization_percent = (tickets_used / total_tickets * 100) if total_tickets > 0 else 0
    remaining_percent = (tickets_remaining / total_tickets * 100) if total_tickets > 0 else 0
    
    # Get user's upcoming appointments (only confirmed ones)
    upcoming_appointments = Appointment.objects.filter(
        client=user,
        appointment_date__gte=today,
        status='confirmed'  # Only show confirmed appointments
    ).order_by('appointment_date', 'appointment_time')
    
    # Get attendance history - simplified
    attendance_history = AttendanceRecord.objects.filter(user=user).order_by('-check_in_time')[:10]
    
    # Get user notifications (including low ticket warnings)
    notifications = Notification.objects.filter(
        user=user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    context = {
        'user': user,
        'active_packages': active_packages_with_tickets,
        'upcoming_appointments': upcoming_appointments,
        'attendance_history': attendance_history,
        'total_tickets': total_tickets,
        'tickets_used': tickets_used,
        'tickets_remaining': tickets_remaining,
        'utilization_percent': utilization_percent,
        'remaining_percent': remaining_percent,
        'today': today,
        'active_tab': 'gym_sessions',
        'notifications': notifications,
        'unread_notifications_count': notifications.count(),
        'low_ticket_notification': low_ticket_notification,
    }
    return render(request, 'client/gym_sessions.html', context)
@login_required
def generate_user_qr(request):
    """Generate and send permanent QR code to user"""
    try:
        # Get user's active packages
        active_packages = UserServicePackage.objects.filter(
            user=request.user, 
            status='active',
            end_date__gte=timezone.now().date()
        )
        
        # Generate QR code data
        qr_data = {
            'user_id': str(request.user.id),
            'user_name': request.user.get_full_name(),
            'email': request.user.email,
            'phone': request.user.phone_number or "Not provided",
            'service_type': 'gym',  # Default service type
        }
        
        # Add active packages info
        if active_packages.exists():
            qr_data['active_packages'] = [{
                'name': pkg.service_package.name,
                'remaining_tickets': pkg.tickets_remaining(),
                'expiry_date': pkg.end_date.strftime('%Y-%m-%d'),
                'service_type': pkg.service_package.service_type
            } for pkg in active_packages]
        
        # Convert to JSON string for QR code
        qr_data_str = json.dumps(qr_data)
        
        # Generate QR code
        qr_buffer = generate_qr_code(qr_data_str)
        
        # Send QR code via email
        if send_qr_code_email(request.user, qr_buffer, qr_data):
            messages.success(request, 'Your permanent QR code has been sent to your email address!')
        else:
            messages.warning(request, 'QR code generated but email could not be sent.')
        
    except Exception as e:
        messages.error(request, f'Error generating QR code: {str(e)}')
    
    return redirect('client:client_qr_code')


@login_required
def get_service_details(request, service_id):
    """Get service details including tickets for AJAX requests"""
    try:
        service = ServicePackage.objects.get(id=service_id, is_active=True)
        return JsonResponse({
            'success': True,
            'tickets_included': service.tickets_included,
            'price': float(service.price)  # Convert Decimal to float for JSON
        })
    except ServicePackage.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Service not found'
        })
        
@login_required
def download_attendance_history(request, format_type):
    """Download attendance history in various formats"""
    attendance_records = AttendanceRecord.objects.filter(user=request.user).order_by('-check_in_time')
    
    if format_type == 'pdf':
        return generate_attendance_pdf(request, attendance_records)
    elif format_type == 'excel':
        return generate_attendance_excel(request, attendance_records)
    elif format_type == 'csv':
        # Simple CSV implementation
        import csv
        from io import StringIO
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="attendance_history_{request.user.username}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Service', 'Check-in Time', 'Check-out Time', 'Duration', 'Status', 'Notes'])
        
        for record in attendance_records:
            if record.check_out_time:
                duration = record.check_out_time - record.check_in_time
                hours = duration.total_seconds() / 3600
                duration_str = f"{hours:.1f} hours"
                status = 'Completed'
            else:
                duration_str = "N/A"
                status = 'In Progress'
            
            writer.writerow([
                record.check_in_time.strftime("%Y-%m-%d"),
                record.service_package.name,
                record.check_in_time.strftime("%H:%M"),
                record.check_out_time.strftime("%H:%M") if record.check_out_time else "N/A",
                duration_str,
                status,
                record.notes or ''
            ])
        
        return response
        
    else:
        messages.error(request, 'Invalid format requested. Please choose CSV, PDF, or Excel.')
        return redirect('client:gym_sessions')

    
def generate_attendance_pdf(request, records):
    """Generate PDF report of attendance records"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO
        
        # Create a file-like buffer to receive PDF data
        buffer = BytesIO()
        
        # Create the PDF object
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Add logo and title
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, height - 100, "New Chogma-SPA - Attendance History")
        p.setFont("Helvetica", 12)
        p.drawString(100, height - 120, f"Client: {request.user.get_full_name()}")
        p.drawString(100, height - 140, f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Draw a line
        p.line(100, height - 150, width - 100, height - 150)
        
        # Table headers
        y_position = height - 170
        headers = ["Date", "Service", "Check-in", "Check-out", "Duration", "Status"]
        col_widths = [80, 100, 80, 80, 80, 80]
        
        p.setFont("Helvetica-Bold", 10)
        x_position = 50
        for i, header in enumerate(headers):
            p.drawString(x_position, y_position, header)
            x_position += col_widths[i]
        
        # Table data
        p.setFont("Helvetica", 9)
        y_position -= 20
        
        for record in records:
            if y_position < 100:  # New page if needed
                p.showPage()
                y_position = height - 50
                p.setFont("Helvetica", 9)
            
            # Format data
            date = record.check_in_time.strftime("%Y-%m-%d")
            service = record.service_package.name
            check_in = record.check_in_time.strftime("%H:%M")
            check_out = record.check_out_time.strftime("%H:%M") if record.check_out_time else "N/A"
            
            if record.check_out_time:
                duration = record.check_out_time - record.check_in_time
                hours = duration.total_seconds() / 3600
                duration_str = f"{hours:.1f}h"
            else:
                duration_str = "N/A"
            
            status = "Completed" if record.check_out_time else "In Progress"
            
            # Draw row
            x_position = 50
            row_data = [date, service, check_in, check_out, duration_str, status]
            
            for i, data in enumerate(row_data):
                # Handle text that might be too long
                if len(str(data)) > 15:
                    data = str(data)[:12] + "..."
                p.drawString(x_position, y_position, str(data))
                x_position += col_widths[i]
            
            y_position -= 15
        
        # Finalize PDF
        p.save()
        
        # File response
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="attendance_history_{request.user.username}.pdf"'
        return response
        
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('client:gym_sessions')

def generate_attendance_excel(request, records):
    """Generate Excel report of attendance records"""
    try:
        import pandas as pd
        from io import BytesIO
        
        # Prepare data
        data = []
        for record in records:
            if record.check_out_time:
                duration = record.check_out_time - record.check_in_time
                hours = duration.total_seconds() / 3600
                duration_str = f"{hours:.1f} hours"
            else:
                duration_str = "N/A"
            
            data.append({
                'Date': record.check_in_time.strftime("%Y-%m-%d"),
                'Service': record.service_package.name,
                'Check-in Time': record.check_in_time.strftime("%H:%M"),
                'Check-out Time': record.check_out_time.strftime("%H:%M") if record.check_out_time else "N/A",
                'Duration': duration_str,
                'Status': 'Completed' if record.check_out_time else 'In Progress',
                'Notes': record.notes or ''
            })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Create Excel file
        output = BytesIO()
        
        # Use xlsxwriter engine for better compatibility
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Attendance History', index=False)
            
            # Auto-adjust columns width
            worksheet = writer.sheets['Attendance History']
            
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(max_len, 50))
        
        output.seek(0)
        
        # File response
        response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="attendance_history_{request.user.username}.xlsx"'
        return response
        
    except Exception as e:
        messages.error(request, f'Error generating Excel: {str(e)}')
        return redirect('client:gym_sessions')
    
@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read for current user"""
    try:
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
def use_ticket(self):
    """Deduct one ticket from the package and create notifications for low tickets"""
    if self.tickets_used < self.total_tickets:
        self.tickets_used += 1
        remaining_tickets = self.total_tickets - self.tickets_used
        
        # Create notification for low tickets (2 or fewer remaining)
        if remaining_tickets <= 2 and remaining_tickets > 0:
            from core.notifications import create_notification
            create_notification(
                self.user,
                'low_tickets',
                f'Low tickets warning: You have only {remaining_tickets} ticket(s) remaining in your {self.service_package.name} package',
                is_urgent=remaining_tickets == 1,  # Most urgent if only 1 ticket left
                related_object=self
            )
            
            # Also send email notification
            from core.notifications import send_email_notification
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

@login_required
@require_POST
def clear_attendance_history(request):
    """Clear all attendance history for current user"""
    try:
        deleted_count = AttendanceRecord.objects.filter(user=request.user).delete()[0]
        messages.success(request, f'Successfully cleared {deleted_count} attendance records.')
        return JsonResponse({'success': True, 'message': f'Cleared {deleted_count} records'})
    except Exception as e:
        messages.error(request, f'Error clearing history: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)})
    
    
@login_required
def client_qr_code(request):
    """Display the client's permanent QR code"""
    if request.user.role != CustomUser.CLIENT:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get user's active packages
    active_packages = UserServicePackage.objects.filter(
        user=request.user, 
        status='active',
        end_date__gte=timezone.now().date()
    )
    
    # Generate QR code data
    qr_data = {
        'user_id': str(request.user.id),
        'user_name': request.user.get_full_name(),
        'email': request.user.email,
        'phone': request.user.phone_number or "Not provided",
        'service_type': 'gym',  # Default service type for QR codes
    }
    
    # Add active packages info
    if active_packages.exists():
        qr_data['active_packages'] = [{
            'name': pkg.service_package.name,
            'remaining_tickets': pkg.tickets_remaining(),
            'expiry_date': pkg.end_date.strftime('%Y-%m-%d'),
            'service_type': pkg.service_package.service_type  # Include service type
        } for pkg in active_packages]
    
    context = {
        'user': request.user,
        'qr_data': json.dumps(qr_data),
        'active_packages': active_packages,
        'active_tab': 'qrcode',
    }
    return render(request, 'client/client_qr_code.html', context)