
import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import CustomUser
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Staff, StaffAttendance
from .forms import StaffForm, StaffAttendanceForm
from .forms import ClientForm
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from core.models import Appointment, AttendanceRecord, Notification, UserServicePackage
# admin_app/views.py
import secrets
import string

# admin_app/views.py
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.conf import settings


@login_required
def admin_dashboard(request):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get actual data from database
    from django.utils import timezone
    from datetime import timedelta
    from core.models import Appointment, AttendanceRecord
    from .models import Staff
    
    # Calculate statistics
    total_clients = CustomUser.objects.filter(role=CustomUser.CLIENT).count()
    
    # Today's appointments
    today = timezone.now().date()
    today_appointments = Appointment.objects.filter(appointment_date=today).count()
    
    # Active staff members
    active_staff = Staff.objects.filter(status='active').count()
    
    # Pending approvals
    pending_approvals = Appointment.objects.filter(
        status='pending', 
        admin_action_required=True
    ).count()
    
    # Today's attendance
    today_attendance = AttendanceRecord.objects.filter(
        check_in_time__date=today
    )
    today_attendance_count = today_attendance.count()
    
    # Service type breakdown
    gym_sessions_count = today_attendance.filter(session_type='gym').count()
    massage_count = today_attendance.filter(session_type='massage').count()
    sauna_count = today_attendance.filter(session_type='sauna').count()
    
    # Recent signups (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_signups = CustomUser.objects.filter(
        role=CustomUser.CLIENT,
        date_joined__gte=seven_days_ago
    ).order_by('-date_joined')[:5]
    
    # Pending appointments for approval
    pending_appointments = Appointment.objects.filter(
        status='pending',
        admin_action_required=True
    ).select_related('client', 'service').order_by('appointment_date', 'appointment_time')[:5]
    
    context = {
        'user': request.user,
        'total_clients': total_clients,
        'today_appointments': today_appointments,
        'active_staff': active_staff,
        'pending_approvals': pending_approvals,
        'today_attendance_count': today_attendance_count,
        'gym_sessions_count': gym_sessions_count,
        'massage_count': massage_count,
        'sauna_count': sauna_count,
        'recent_signups': recent_signups,
        'pending_appointments': pending_appointments,
        'active_tab': 'dashboard',
    }
    return render(request, 'admin/dashboard.html', context)


@login_required
def user_management(request):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get only CLIENT users, not admins
    users = CustomUser.objects.filter(role=CustomUser.CLIENT).order_by('-date_joined')
    
    # Get statistics for CLIENTS only
    total_users_count = users.count()
    active_users_count = users.filter(is_active=True).count()
    inactive_users_count = users.filter(is_active=False).count()
    admin_count = CustomUser.objects.filter(role=CustomUser.ADMIN).count()
    
    context = {
        'user': request.user,
        'users': users,
        'total_users_count': total_users_count,
        'active_users_count': active_users_count,
        'inactive_users_count': inactive_users_count,
        'admin_count': admin_count,
        'active_tab': 'user_management',
    }
    return render(request, 'admin/user_management.html', context)

@login_required
def view_client(request, user_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get the client user - ensure it's a client, not admin
    client = get_object_or_404(CustomUser, id=user_id, role=CustomUser.CLIENT)
    
    # Get real data from the database
    from core.models import AttendanceRecord, UserServicePackage, Appointment
    from django.db.models import Sum, Count
    from django.utils import timezone
    
    # Calculate real statistics
    total_sessions_used = AttendanceRecord.objects.filter(user=client).count()
    
    # Get active package information
    active_package = UserServicePackage.objects.filter(
        user=client, 
        status='active',
        end_date__gte=timezone.now().date()
    ).first()
    
    if active_package:
        remaining_sessions = active_package.tickets_remaining()
        total_sessions = active_package.total_tickets
        package_name = active_package.service_package.name
        package_price = active_package.service_package.price
        start_date = active_package.start_date
        end_date = active_package.end_date
    else:
        remaining_sessions = 0
        total_sessions = 0
        package_name = None
        package_price = 0
        start_date = None
        end_date = None
    
    # Calculate total spent (sum of all service package prices)
    total_spent = UserServicePackage.objects.filter(user=client).aggregate(
        total=Sum('service_package__price')
    )['total'] or 0
    
    # Count upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        client=client,
        appointment_date__gte=timezone.now().date(),
        status__in=['pending', 'confirmed']
    ).count()
    
    # Get real attendance history (last 10 visits)
    attendance_history = AttendanceRecord.objects.filter(
        user=client
    ).select_related('service_package').order_by('-check_in_time')[:10]
    
    # Format attendance history for template
    formatted_attendance = []
    for record in attendance_history:
        duration = "N/A"
        if record.check_out_time:
            duration_seconds = (record.check_out_time - record.check_in_time).total_seconds()
            hours = int(duration_seconds // 3600)
            minutes = int((duration_seconds % 3600) // 60)
            duration = f"{hours}h {minutes}m"
        
        formatted_attendance.append({
            'date': record.check_in_time.strftime('%Y-%m-%d'),
            'service': record.service_package.name,
            'duration': duration,
            'check_in': record.check_in_time.strftime('%H:%M'),
            'check_out': record.check_out_time.strftime('%H:%M') if record.check_out_time else 'N/A'
        })
    
    # Get payment history (from UserServicePackage purchases)
    payment_history = UserServicePackage.objects.filter(
        user=client
    ).select_related('service_package').order_by('-purchase_date')[:5]
    
    # Format payment history for template
    formatted_payments = []
    for package in payment_history:
        formatted_payments.append({
            'date': package.purchase_date.strftime('%Y-%m-%d'),
            'amount': float(package.service_package.price),
            'service': package.service_package.name,
            'status': 'Completed'
        })
    
    client_data = {
        'total_sessions_used': total_sessions_used,
        'remaining_sessions': remaining_sessions,
        'total_sessions': total_sessions,
        'total_spent': total_spent,
        'upcoming_appointments': upcoming_appointments,
        'attendance_history': formatted_attendance,
        'payment_history': formatted_payments,
        'current_package': {
            'name': package_name,
            'price': float(package_price) if package_price else 0,
            'sessions': total_sessions,
            'start_date': start_date.strftime('%Y-%m-%d') if start_date else 'N/A',
            'end_date': end_date.strftime('%Y-%m-%d') if end_date else 'N/A',
            'remaining_sessions': remaining_sessions
        } if active_package else None
    }
    
    context = {
        'user': request.user,
        'client': client,
        'client_data': client_data,
        'active_tab': 'user_management',
    }
    return render(request, 'admin/client_detail.html', context)

@login_required
def add_client(request):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f'Client {client.get_full_name()} has been added successfully!')
            return redirect('admin_app:user_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ClientForm()
    
    context = {
        'form': form,
        'title': 'Add New Client',
        'action_url': 'admin_app:add_client',
        'active_tab': 'user_management',
    }
    return render(request, 'admin/client_form.html', context)

@login_required
def edit_client(request, user_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get the client user
    client = get_object_or_404(CustomUser, id=user_id, role=CustomUser.CLIENT)
    
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            client = form.save()
            messages.success(request, f'Client {client.get_full_name()} has been updated successfully!')
            return redirect('admin_app:user_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ClientForm(instance=client)
    
    context = {
        'form': form,
        'client': client,
        'title': f'Edit Client - {client.get_full_name()}',
        'action_url': 'admin_app:edit_client',
        'active_tab': 'user_management',
    }
    return render(request, 'admin/client_form.html', context)

from django.http import JsonResponse

@login_required
def delete_client(request, user_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            client = get_object_or_404(CustomUser, id=user_id, role=CustomUser.CLIENT)
            client_name = client.get_full_name()
            client.delete()
            return JsonResponse({'success': True, 'message': f'Client {client_name} has been deleted successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def toggle_client_status(request, user_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            client = get_object_or_404(CustomUser, id=user_id, role=CustomUser.CLIENT)
            client.is_active = not client.is_active
            client.save()
            
            action = "activated" if client.is_active else "deactivated"
            return JsonResponse({
                'success': True, 
                'message': f'Client {client.get_full_name()} has been {action} successfully!',
                'is_active': client.is_active
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


from .models import ServicePackage
from .forms import ServicePackageForm

@login_required
def service_management(request):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get all service packages
    services = ServicePackage.objects.all().order_by('service_type', 'price')
    
    # Get statistics
    total_services = services.count()
    active_services = services.filter(is_active=True).count()
    
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
        'total_services': total_services,
        'active_services': active_services,
        'active_tab': 'services',
    }
    return render(request, 'admin/service_management.html', context)

@login_required
def add_service(request):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = ServicePackageForm(request.POST)
        if form.is_valid():
            service = form.save()
            messages.success(request, f'Service package "{service.name}" has been added successfully!')
            return redirect('admin_app:service_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ServicePackageForm()
    
    context = {
        'form': form,
        'title': 'Add New Service Package',
        'action_url': 'admin_app:add_service',
        'active_tab': 'services',
    }
    return render(request, 'admin/service_form.html', context)

@login_required
def edit_service(request, service_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get the service package
    service = get_object_or_404(ServicePackage, id=service_id)
    
    if request.method == 'POST':
        form = ServicePackageForm(request.POST, instance=service)
        if form.is_valid():
            service = form.save()
            messages.success(request, f'Service package "{service.name}" has been updated successfully!')
            return redirect('admin_app:service_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ServicePackageForm(instance=service)
    
    context = {
        'form': form,
        'service': service,
        'title': f'Edit Service Package - {service.name}',
        'action_url': 'admin_app:edit_service',
        'active_tab': 'services',
    }
    return render(request, 'admin/service_form.html', context)

@login_required
def toggle_service_status(request, service_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            service = get_object_or_404(ServicePackage, id=service_id)
            service.is_active = not service.is_active
            service.save()
            
            action = "activated" if service.is_active else "deactivated"
            return JsonResponse({
                'success': True, 
                'message': f'Service package "{service.name}" has been {action} successfully!',
                'is_active': service.is_active
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def delete_service(request, service_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            service = get_object_or_404(ServicePackage, id=service_id)
            service_name = service.name
            service.delete()
            return JsonResponse({'success': True, 'message': f'Service package "{service_name}" has been deleted successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})




@login_required
def admin_appointments(request):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    date_filter = request.GET.get('date', '')
    
    # Get all appointments with related data for better performance
    appointments = Appointment.objects.all().select_related('client', 'service').order_by('-appointment_date', '-appointment_time')
    
    # Apply filters
    if status_filter != 'all':
        appointments = appointments.filter(status=status_filter)
    
    if date_filter:
        appointments = appointments.filter(appointment_date=date_filter)
    
    # Count appointments by status
    pending_count = Appointment.objects.filter(status='pending', admin_action_required=True).count()
    confirmed_count = Appointment.objects.filter(status='confirmed').count()
    cancelled_count = Appointment.objects.filter(status='cancelled').count()
    completed_count = Appointment.objects.filter(status='completed').count()
    rejected_count = Appointment.objects.filter(status='rejected').count()
    total_count = Appointment.objects.count()
    
    context = {
        'user': request.user,
        'appointments': appointments,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'cancelled_count': cancelled_count,
        'completed_count': completed_count,
        'rejected_count': rejected_count,
        'total_count': total_count,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'active_tab': 'appointments',
    }
    return render(request, 'admin/appointments.html', context)

@login_required
def approve_appointment(request, appointment_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            appointment = get_object_or_404(Appointment, id=appointment_id)
            
            # DEBUG: Check appointment status
            print(f"DEBUG - Appointment {appointment_id} status: {appointment.status}")
            print(f"DEBUG - Auto-approve at: {appointment.auto_approve_at}")
            print(f"DEBUG - Current time: {timezone.now()}")
            
            # If appointment is already confirmed, just return success
            if appointment.status == 'confirmed':
                return JsonResponse({
                    'success': True, 
                    'message': 'Appointment was already approved',
                    'email_sent': False,
                    'new_status': 'confirmed'
                })
            
            # If appointment is not pending, return error
            if appointment.status != 'pending':
                return JsonResponse({
                    'success': False, 
                    'error': f'Appointment is not pending approval. Current status: {appointment.status}'
                })
            
            # MANUAL APPROVAL BY ADMIN - Update status
            appointment.status = 'confirmed'
            appointment.admin_action_required = False
            appointment.auto_approve_at = None  # Clear auto-approve time since admin manually approved
            appointment.save()
            
            # CREATE OR UPDATE USER SERVICE PACKAGE (ONLY AFTER MANUAL APPROVAL)
            from datetime import timedelta
            
            # FIRST: Check if there are any existing active packages and deactivate them
            UserServicePackage.objects.filter(
                user=appointment.client,
                service_package=appointment.service,
                status='active'
            ).update(status='expired')
            
            # THEN: Create new package (this ensures only one active package exists)
            UserServicePackage.objects.create(
                user=appointment.client,
                service_package=appointment.service,
                start_date=appointment.appointment_date,
                end_date=appointment.appointment_date + timedelta(days=appointment.service.validity_days),
                total_tickets=appointment.service.tickets_included,
                tickets_used=0,
                status='active'
            )
            
            # Send confirmation email - use direct import path
            try:
                from core.utils import send_appointment_confirmation_email
                email_sent = send_appointment_confirmation_email(appointment)
            except ImportError:
                # Fallback: use the model method if utility function doesn't exist
                print("DEBUG - Could not import send_appointment_confirmation_email, using model method")
                email_sent = appointment.send_confirmation_email()
            
            return JsonResponse({
                'success': True, 
                'message': f'Appointment has been approved successfully!',
                'email_sent': email_sent,
                'new_status': 'confirmed'
            })
        except Exception as e:
            import traceback
            print(f"DEBUG - Error in approve_appointment: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def reject_appointment(request, appointment_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            appointment = get_object_or_404(Appointment, id=appointment_id)
            
            if appointment.status != 'pending':
                return JsonResponse({'success': False, 'error': 'Appointment is not pending approval'})
            
            appointment.status = 'rejected'
            appointment.admin_action_required = False
            appointment.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Appointment has been rejected!',
                'new_status': 'rejected'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def update_appointment_status(request, appointment_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            appointment = get_object_or_404(Appointment, id=appointment_id)
            new_status = request.POST.get('status')
            
            if new_status not in dict(Appointment.STATUS_CHOICES).keys():
                return JsonResponse({'success': False, 'error': 'Invalid status'})
            
            appointment.status = new_status
            
            # If confirming, send email
            if new_status == 'confirmed':
                appointment.send_confirmation_email()
            
            appointment.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Appointment status updated to {new_status}!',
                'new_status': new_status
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})




@login_required
def staff_management(request):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get filter parameters
    role_filter = request.GET.get('role', 'all')
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    # Get all staff members
    staff_members = Staff.objects.all().select_related('user')
    
    # Apply filters
    if role_filter != 'all':
        staff_members = staff_members.filter(role=role_filter)
    
    if status_filter != 'all':
        staff_members = staff_members.filter(status=status_filter)
    
    if search_query:
        staff_members = staff_members.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(staff_id__icontains=search_query) |
            Q(department__icontains=search_query)
        )
    
    # Get statistics
    total_staff = Staff.objects.count()
    active_staff = Staff.objects.filter(status='active').count()
    trainers_count = Staff.objects.filter(role='trainer', status='active').count()
    receptionists_count = Staff.objects.filter(role='receptionist', status='active').count()
    
    # Get today's attendance
    today = timezone.now().date()
    today_attendance = StaffAttendance.objects.filter(date=today)
    present_today = today_attendance.filter(status='present').count()
    
    context = {
        'user': request.user,
        'staff_members': staff_members,
        'total_staff': total_staff,
        'active_staff': active_staff,
        'trainers_count': trainers_count,
        'receptionists_count': receptionists_count,
        'present_today': present_today,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'search_query': search_query,
        'active_tab': 'staff',
    }
    return render(request, 'admin/staff_management.html', context)



@login_required
def add_staff(request):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            # Get form data
            email = request.POST.get('email')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            phone_number = request.POST.get('phone_number')
            
            # Generate a secure random password
            temp_password = get_random_string(12)
            
            # Create user - pass email as username and separately for email field
            user = CustomUser.objects.create_user(
                username=email,  # Use email as username
                email=email,     # Set email field
                password=temp_password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role=CustomUser.STAFF,
                is_active=True,
            )
            
            # Create staff profile
            staff = form.save(commit=False)
            staff.user = user
            staff.save()
            
            # Send welcome email with temporary password (optional)
            try:
                send_mail(
                    'Welcome to New Chogma-SPA Staff',
                    f'Hello {staff.full_name},\n\n'
                    f'Your staff account has been created.\n'
                    f'Email: {user.email}\n'
                    f'Temporary Password: {temp_password}\n\n'
                    f'Please change your password after first login.\n\n'
                    f'Best regards,\nNew Chogma-SPA Team',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,  # Set to True to avoid errors if email fails
                )
                messages.success(request, f'Staff member {staff.full_name} has been added successfully! Welcome email sent.')
            except Exception as e:
                # If email fails, show the password in the message
                messages.success(request, f'Staff member {staff.full_name} has been added successfully! Temporary password: {temp_password}')
            
            return redirect('admin_app:staff_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffForm()
    
    context = {
        'form': form,
        'title': 'Add New Staff Member',
        'action_url': 'admin_app:add_staff',
        'active_tab': 'staff',
    }
    return render(request, 'admin/staff_form.html', context)
@login_required
def edit_staff(request, staff_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    staff = get_object_or_404(Staff, id=staff_id)
    
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            # Update user information
            staff.user.first_name = request.POST.get('first_name')
            staff.user.last_name = request.POST.get('last_name')
            staff.user.email = request.POST.get('email')
            staff.user.phone_number = request.POST.get('phone_number')
            staff.user.save()
            
            # Update staff profile
            staff = form.save()
            
            messages.success(request, f'Staff member {staff.full_name} has been updated successfully!')
            return redirect('admin_app:staff_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # Prepopulate form with user data
        initial_data = {
            'first_name': staff.user.first_name,
            'last_name': staff.user.last_name,
            'email': staff.user.email,
            'phone_number': staff.user.phone_number,
        }
        form = StaffForm(instance=staff, initial=initial_data)
    
    context = {
        'form': form,
        'staff': staff,
        'title': f'Edit Staff Member - {staff.full_name}',
        'action_url': 'admin_app:edit_staff',
        'active_tab': 'staff',
    }
    return render(request, 'admin/staff_form.html', context)

@login_required
def view_staff(request, staff_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    staff = get_object_or_404(Staff, id=staff_id)
    
    # Get attendance records (last 30 days)
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    attendance_records = StaffAttendance.objects.filter(
        staff=staff, 
        date__gte=thirty_days_ago
    ).order_by('-date')
    
    # Calculate statistics
    total_days = attendance_records.count()
    present_days = attendance_records.filter(status='present').count()
    absent_days = attendance_records.filter(status='absent').count()
    attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0
    
    context = {
        'user': request.user,
        'staff': staff,
        'attendance_records': attendance_records,
        'total_days': total_days,
        'present_days': present_days,
        'absent_days': absent_days,
        'attendance_rate': round(attendance_rate, 1),
        'active_tab': 'staff',
    }
    return render(request, 'admin/staff_detail.html', context)

@login_required
def delete_staff(request, staff_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            staff = get_object_or_404(Staff, id=staff_id)
            staff_name = staff.full_name
            user = staff.user
            
            # Deactivate user instead of deleting
            user.is_active = False
            user.save()
            
            staff.status = 'terminated'
            staff.save()
            
            return JsonResponse({'success': True, 'message': f'Staff member {staff_name} has been deactivated successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def toggle_staff_status(request, staff_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            staff = get_object_or_404(Staff, id=staff_id)
            
            if staff.status == 'active':
                staff.status = 'inactive'
                staff.user.is_active = False
                action = "deactivated"
            else:
                staff.status = 'active'
                staff.user.is_active = True
                action = "activated"
            
            staff.user.save()
            staff.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Staff member {staff.full_name} has been {action} successfully!',
                'is_active': staff.status == 'active'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def staff_attendance(request):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    date_filter = request.GET.get('date', timezone.now().date())
    staff_filter = request.GET.get('staff', '')
    
    # Get attendance for the selected date
    attendance_records = StaffAttendance.objects.filter(date=date_filter).select_related('staff')
    
    # Apply staff filter if provided
    if staff_filter:
        attendance_records = attendance_records.filter(staff_id=staff_filter)
    
    # Get all active staff for form
    active_staff = Staff.objects.filter(status='active')
    
    # Calculate statistics
    present_count = attendance_records.filter(status='present').count()
    absent_count = attendance_records.filter(status='absent').count()
    other_count = attendance_records.count() - present_count - absent_count
    
    if request.method == 'POST':
        form = StaffAttendanceForm(request.POST)
        if form.is_valid():
            # Check if attendance record already exists for this staff and date
            staff = form.cleaned_data['staff']
            date = form.cleaned_data['date']
            
            existing_record = StaffAttendance.objects.filter(staff=staff, date=date).first()
            
            if existing_record:
                # Update existing record
                for field in ['check_in', 'check_out', 'status', 'hours_worked', 'notes']:
                    if form.cleaned_data[field] is not None:
                        setattr(existing_record, field, form.cleaned_data[field])
                existing_record.save()
                messages.success(request, f'Attendance updated for {staff.full_name}')
            else:
                # Create new record
                attendance = form.save()
                messages.success(request, f'Attendance recorded for {attendance.staff.full_name}')
            
            return redirect('admin_app:staff_attendance')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffAttendanceForm(initial={'date': date_filter})
    
    context = {
        'user': request.user,
        'attendance_records': attendance_records,
        'active_staff': active_staff,
        'date_filter': date_filter,
        'present_count': present_count,
        'absent_count': absent_count,
        'other_count': other_count,
        'form': form,
        'active_tab': 'staff',
    }
    return render(request, 'admin/staff_attendance.html', context)


# admin_app/views.py
@login_required
def delete_attendance(request, record_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            attendance = get_object_or_404(StaffAttendance, id=record_id)
            staff_name = attendance.staff.full_name
            attendance.delete()
            
            return JsonResponse({'success': True, 'message': f'Attendance record for {staff_name} has been deleted successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def attendance_tracker(request):
    """Admin view for scanning QR codes and tracking attendance"""
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get today's attendance records
    today = timezone.now().date()
    attendance_records = AttendanceRecord.objects.filter(
        check_in_time__date=today
    ).select_related('user', 'service_package').order_by('-check_in_time')
    
    # Add active package information to each record
    for record in attendance_records:
        try:
            record.active_package = UserServicePackage.objects.filter(
                user=record.user, 
                status='active',
                end_date__gte=today
            ).first()
        except:
            record.active_package = None
    
    # Get statistics
    today_attendance_count = attendance_records.count()
    active_clients_count = CustomUser.objects.filter(
        role=CustomUser.CLIENT, 
        is_active=True
    ).count()
    gym_sessions_count = attendance_records.filter(
        session_type='gym'
    ).count()
    
    context = {
        'user': request.user,
        'attendance_records': attendance_records,
        'today_attendance_count': today_attendance_count,
        'active_clients_count': active_clients_count,
        'gym_sessions_count': gym_sessions_count,
        'active_tab': 'attendance_tracker',
    }
    return render(request, 'admin/attendance_tracker.html', context)
@login_required
def process_qr_scan(request):
    """Process QR code scan from admin - also handles manual check-ins"""
    if request.user.role != CustomUser.ADMIN:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            # Parse the request data
            data = json.loads(request.body)
            qr_data_str = data.get('qr_data', '{}')
            
            print(f"Received data: {qr_data_str}")  # Debug log
            
            # Parse the data
            try:
                checkin_data = json.loads(qr_data_str)
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False, 
                    'error': 'Invalid data format'
                })
            
            user = None
            service_type = 'gym'  # Default service type
            
            # Handle manual check-in
            if checkin_data.get('manual_checkin'):
                client_email = checkin_data.get('client_email')
                service_type = checkin_data.get('service_type', 'gym')  # Get service type or default to gym
                
                if not client_email:
                    return JsonResponse({
                        'success': False, 
                        'error': 'Client email is required for manual check-in'
                    })
                
                try:
                    user = CustomUser.objects.get(email=client_email, role=CustomUser.CLIENT)
                except CustomUser.DoesNotExist:
                    return JsonResponse({
                        'success': False, 
                        'error': f'Client with email {client_email} not found'
                    })
            
            # Handle QR code check-in
            else:
                user_id = checkin_data.get('user_id')
                if not user_id:
                    return JsonResponse({
                        'success': False, 
                        'error': 'User ID not found in check-in data'
                    })
                
                try:
                    user = CustomUser.objects.get(id=user_id)
                except CustomUser.DoesNotExist:
                    return JsonResponse({
                        'success': False, 
                        'error': 'User not found'
                    })
                
                # For QR codes, try to get service_type from the QR data or use default
                service_type = checkin_data.get('service_type', 'gym')
            
            # Get user's active packages for the requested service type
            active_packages = UserServicePackage.objects.filter(
                user=user,
                status='active',
                end_date__gte=timezone.now().date(),
                service_package__service_type=service_type
            )
            
            if not active_packages.exists():
                return JsonResponse({
                    'success': False, 
                    'error': f'No active {service_type} package found for this user'
                })
            
            # Find package with remaining tickets
            package_with_tickets = None
            for package in active_packages:
                if package.tickets_remaining() > 0:
                    package_with_tickets = package
                    break
            
            if not package_with_tickets:
                return JsonResponse({
                    'success': False, 
                    'error': 'No tickets remaining in any active package'
                })
            
            # CREATE ATTENDANCE RECORD
            attendance = AttendanceRecord.objects.create(
                user=user,
                service_package=package_with_tickets.service_package,
                session_type=service_type,
                notes='Manual check-in at reception' if checkin_data.get('manual_checkin') else 'Scanned via QR code at reception'
            )
            
            # Deduct ticket from package
            package_with_tickets.tickets_used += 1
            remaining_tickets = package_with_tickets.tickets_remaining()
            package_with_tickets.save()
            
            # Check if low ticket notification should be sent (2 or fewer tickets remaining)
            if remaining_tickets <= 2 and remaining_tickets > 0:
                # Create notification
                notification = Notification.objects.create(
                    user=user,
                    notification_type='low_tickets',
                    message=f'Low tickets warning: You have only {remaining_tickets} ticket(s) remaining in your {package_with_tickets.service_package.name} package',
                    is_urgent=remaining_tickets == 1,
                    related_object_id=package_with_tickets.id,
                    related_content_type='package'
                )
                
                # Send email notification - SIMPLIFIED VERSION
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    
                    subject = f'Low Tickets Alert - {package_with_tickets.service_package.name}'
                    
                    # Create simple text email instead of HTML template
                    message = f"""
Hello {user.get_full_name()},

This is a reminder that you have only {remaining_tickets} ticket(s) remaining 
in your {package_with_tickets.service_package.name} package.

Package Details:
- Package Name: {package_with_tickets.service_package.name}
- Remaining Tickets: {remaining_tickets}
- Total Tickets: {package_with_tickets.total_tickets}
- Expiry Date: {package_with_tickets.end_date}

To avoid interruption of your services, we recommend booking a new appointment 
to renew your package.

You can book a new appointment here: {request.scheme}://{request.get_host()}/client/book-appointment/

If you have any questions or need assistance, please contact our support team.

Best regards,
New Chogma-SPA Team
"""
                    
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=True,  # Set to True to avoid errors if email fails
                    )
                    print(f"Low ticket email sent to {user.email}")
                except Exception as e:
                    print(f"Error sending email notification: {e}")
                    # Continue even if email fails
            
            # Check if package should be expired (no tickets left)
            if remaining_tickets == 0:
                package_with_tickets.status = 'expired'
                package_with_tickets.save()
                
                # Create expiration notification
                Notification.objects.create(
                    user=user,
                    notification_type='package_expiry',
                    message=f'Your {package_with_tickets.service_package.name} package has expired. All tickets have been used.',
                    is_urgent=True,
                    related_object_id=package_with_tickets.id,
                    related_content_type='package'
                )
            
            # Get user's attendance history
            attendance_history = AttendanceRecord.objects.filter(
                user=user
            ).order_by('-check_in_time')[:5]  # Last 5 visits
            
            # Prepare response data
            response_data = {
                'success': True,
                'message': f'Welcome {user.get_full_name()}! Attendance recorded successfully.',
                'user_info': {
                    'name': user.get_full_name(),
                    'email': user.email,
                    'phone': user.phone_number or 'Not provided',
                    'member_since': user.date_joined.strftime('%Y-%m-%d')
                },
                'package_info': {
                    'name': package_with_tickets.service_package.name,
                    'remaining_tickets': remaining_tickets,
                    'total_tickets': package_with_tickets.total_tickets,
                    'expiry_date': package_with_tickets.end_date.strftime('%Y-%m-%d')
                },
                'attendance_info': {
                    'check_in_time': attendance.check_in_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'total_visits': AttendanceRecord.objects.filter(user=user).count(),
                    'recent_visits': [{
                        'date': record.check_in_time.strftime('%Y-%m-%d'),
                        'service': record.service_package.name,
                        'time': record.check_in_time.strftime('%H:%M')
                    } for record in attendance_history]
                }
            }
            
            return JsonResponse(response_data)
            
        except CustomUser.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
        except Exception as e:
            import traceback
            print(f"Error in process_qr_scan: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# admin_app/views.py
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Avg, Q
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import CustomUser
from core.models import AttendanceRecord, UserServicePackage, Appointment, ServicePackage
import csv
import json

@login_required
def reports_dashboard(request):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get filter parameters with defaults
    start_date_str = request.GET.get('start_date', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
    service_filter = request.GET.get('service_type', 'all')
    
    # Convert to date objects
    try:
        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # Fallback to default dates if parsing fails
        start_date_obj = (timezone.now() - timedelta(days=30)).date()
        end_date_obj = timezone.now().date()
    
    # Base queryset for the date range
    base_attendance = AttendanceRecord.objects.filter(
        check_in_time__date__gte=start_date_obj,
        check_in_time__date__lte=end_date_obj
    )
    
    # Apply service filter if needed
    if service_filter != 'all':
        base_attendance = base_attendance.filter(session_type=service_filter)
    
    # Calculate summary statistics
    total_clients = CustomUser.objects.filter(role=CustomUser.CLIENT).count()
    total_visits = base_attendance.count()
    
    # Calculate revenue
    revenue = base_attendance.aggregate(
        total_revenue=Sum('service_package__price')
    )['total_revenue'] or 0
    
    # New clients in date range
    new_clients = CustomUser.objects.filter(
        role=CustomUser.CLIENT,
        date_joined__date__gte=start_date_obj,
        date_joined__date__lte=end_date_obj
    ).count()
    
    # Average visit frequency
    visit_counts = base_attendance.values('user').annotate(visit_count=Count('id'))
    visit_frequency = visit_counts.aggregate(avg_visits=Avg('visit_count'))['avg_visits'] or 0
    
    # Occupancy rate (simplified calculation)
    total_days = (end_date_obj - start_date_obj).days + 1
    max_possible_visits = total_clients * total_days
    occupancy_rate = (total_visits / max_possible_visits * 100) if max_possible_visits > 0 else 0
    
    # Service statistics
    service_stats = base_attendance.values(
        'session_type'
    ).annotate(
        visits=Count('id'),
        revenue=Sum('service_package__price')
    ).order_by('-revenue')
    
    # Add service names
    service_name_map = {
        'gym': 'Gym Session',
        'sauna': 'Sauna',
        'massage': 'Massage',
        # Add other service types as needed
    }
    
    for stat in service_stats:
        stat['name'] = service_name_map.get(stat['session_type'], stat['session_type'].title())
        stat['avg_revenue'] = stat['revenue'] / stat['visits'] if stat['visits'] > 0 else 0
    
    # Top clients by visits and spending
    top_clients = base_attendance.values(
        'user__id', 'user__first_name', 'user__last_name'
    ).annotate(
        visit_count=Count('id'),
        total_spent=Sum('service_package__price')
    ).order_by('-total_spent')[:10]
    
    # Package performance
    package_stats = UserServicePackage.objects.filter(
        purchase_date__date__gte=start_date_obj,
        purchase_date__date__lte=end_date_obj
    ).values(
        'service_package__name'
    ).annotate(
        count=Count('id'),
        total_revenue=Sum('service_package__price')
    ).order_by('-total_revenue')
    
    # Calculate utilization rate for packages
    for package in package_stats:
        package_name = package['service_package__name']
        package_data = UserServicePackage.objects.filter(
            service_package__name=package_name
        ).aggregate(
            total_tickets=Sum('total_tickets'),
            used_tickets=Sum('tickets_used')
        )
        
        total_tickets = package_data['total_tickets'] or 0
        used_tickets = package_data['used_tickets'] or 0
        
        package['utilization_rate'] = (used_tickets / total_tickets * 100) if total_tickets > 0 else 0
    
    # Recent attendance records
    recent_attendance = base_attendance.select_related(
        'user', 'service_package'
    ).order_by('-check_in_time')[:20]
    
    # Add duration to each record
    for record in recent_attendance:
        if record.check_out_time:
            duration = record.check_out_time - record.check_in_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes = remainder // 60
            record.duration = f"{int(hours)}h {int(minutes)}m"
        else:
            record.duration = "N/A"
    
    # Prepare data for charts
    # Revenue by day - FIXED: Use a different approach for date extraction
    revenue_by_day = []
    current_date = start_date_obj
    while current_date <= end_date_obj:
        daily_revenue = base_attendance.filter(
            check_in_time__date=current_date
        ).aggregate(
            daily_revenue=Sum('service_package__price')
        )['daily_revenue'] or 0
        
        revenue_by_day.append({
            'day': current_date,
            'daily_revenue': daily_revenue
        })
        current_date += timedelta(days=1)
    
    revenue_dates = [entry['day'].strftime('%Y-%m-%d') for entry in revenue_by_day]
    revenue_data = [float(entry['daily_revenue']) for entry in revenue_by_day]
    
    # Service distribution
    service_labels = [stat['name'] for stat in service_stats]
    service_data = [stat['visits'] for stat in service_stats]
    
    # Peak hours - FIXED: Use a different approach for hour extraction
    hour_data = [0] * 24  # Initialize for 24 hours
    hour_labels = [f"{hour:02d}:00" for hour in range(24)]
    
    # Get hour distribution
    for hour in range(24):
        hour_count = base_attendance.filter(
            check_in_time__hour=hour
        ).count()
        hour_data[hour] = hour_count
    
    context = {
        'user': request.user,
        'start_date': start_date_obj,
        'end_date': end_date_obj,
        'service_filter': service_filter,
        'total_clients': total_clients,
        'total_visits': total_visits,
        'revenue': revenue,
        'new_clients': new_clients,
        'avg_visit_frequency': visit_frequency,
        'occupancy_rate': occupancy_rate,
        'service_stats': service_stats,
        'top_clients': top_clients,
        'package_stats': package_stats,
        'recent_attendance': recent_attendance,
        'revenue_dates': json.dumps(revenue_dates),
        'revenue_data': revenue_data,
        'service_labels': json.dumps(service_labels),
        'service_data': service_data,
        'hour_labels': json.dumps(hour_labels),
        'hour_data': hour_data,
        'active_tab': 'reports',
    }
    
    return render(request, 'admin/reports.html', context)

@login_required
def export_reports(request):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Get export parameters
    export_format = request.GET.get('format', 'csv')
    export_range = request.GET.get('range', 'current')
    
    # Determine date range based on export_range
    end_date = timezone.now().date()
    
    if export_range == 'last_week':
        start_date = end_date - timedelta(days=7)
    elif export_range == 'last_month':
        start_date = end_date - timedelta(days=30)
    elif export_range == 'last_quarter':
        start_date = end_date - timedelta(days=90)
    elif export_range == 'last_year':
        start_date = end_date - timedelta(days=365)
    else:  # current or default
        start_date_str = request.GET.get('start_date', (end_date - timedelta(days=30)).strftime('%Y-%m-%d'))
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = end_date - timedelta(days=30)
    
    # Get the data
    base_attendance = AttendanceRecord.objects.filter(
        check_in_time__date__gte=start_date,
        check_in_time__date__lte=end_date
    )
    
    # Prepare data based on format
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="reports_{start_date}_{end_date}.csv"'
        
        writer = csv.writer(response)
        # Write header
        writer.writerow(['Date', 'Client', 'Service', 'Duration', 'Revenue', 'Staff'])
        
        # Write data
        for record in base_attendance.select_related('user', 'service_package'):
            duration = "N/A"
            if record.check_out_time:
                duration_seconds = (record.check_out_time - record.check_in_time).total_seconds()
                hours = int(duration_seconds // 3600)
                minutes = int((duration_seconds % 3600) // 60)
                duration = f"{hours}h {minutes}m"
            
            staff_name = "Self-checkin"
            if hasattr(record, 'staff') and record.staff:
                staff_name = record.staff.user.get_full_name() if hasattr(record.staff, 'user') else str(record.staff)
            
            writer.writerow([
                record.check_in_time.strftime('%Y-%m-%d'),
                f"{record.user.first_name} {record.user.last_name}",
                record.service_package.name,
                duration,
                record.service_package.price,
                staff_name
            ])
        
        return response
    
    elif export_format == 'json':
        # Prepare data for JSON export
        export_data = {
            'metadata': {
                'export_date': timezone.now().isoformat(),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'format': 'json'
            },
            'summary': {
                'total_visits': base_attendance.count(),
                'total_revenue': base_attendance.aggregate(
                    total_revenue=Sum('service_package__price')
                )['total_revenue'] or 0,
                'unique_clients': base_attendance.values('user').distinct().count()
            },
            'records': []
        }
        
        # Add records
        for record in base_attendance.select_related('user', 'service_package'):
            duration = None
            if record.check_out_time:
                duration_seconds = (record.check_out_time - record.check_in_time).total_seconds()
                duration = duration_seconds
            
            staff_info = None
            if hasattr(record, 'staff') and record.staff:
                staff_info = {
                    'id': record.staff.id,
                    'name': record.staff.user.get_full_name() if hasattr(record.staff, 'user') else str(record.staff)
                }
                
            export_data['records'].append({
                'date': record.check_in_time.isoformat(),
                'client': {
                    'id': record.user.id,
                    'name': f"{record.user.first_name} {record.user.last_name}",
                    'email': record.user.email
                },
                'service': {
                    'id': record.service_package.id,
                    'name': record.service_package.name,
                    'type': record.session_type,
                    'price': float(record.service_package.price)
                },
                'duration': duration,
                'staff': staff_info
            })
        
        response = HttpResponse(json.dumps(export_data, indent=2), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="reports_{start_date}_{end_date}.json"'
        return response
    
    else:  # Default to CSV
        return export_reports(request)