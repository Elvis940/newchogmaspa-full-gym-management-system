from django.urls import path
from . import views

app_name = 'admin_app'

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='dashboard'),
    path('users/', views.user_management, name='user_management'),
    path('users/view/<int:user_id>/', views.view_client, name='view_client'),
    path('users/add/', views.add_client, name='add_client'),
    path('users/edit/<int:user_id>/', views.edit_client, name='edit_client'),
    path('users/delete/<int:user_id>/', views.delete_client, name='delete_client'),
    path('users/toggle-status/<int:user_id>/', views.toggle_client_status, name='toggle_client_status'),
    
    
      # ... existing URLs ...
    path('services/', views.service_management, name='service_management'),
    path('services/add/', views.add_service, name='add_service'),
    path('services/edit/<int:service_id>/', views.edit_service, name='edit_service'),
    path('services/toggle-status/<int:service_id>/', views.toggle_service_status, name='toggle_service_status'),
    path('services/delete/<int:service_id>/', views.delete_service, name='delete_service'),
    
     # Add appointment URLs
    path('appointments/', views.admin_appointments, name='appointments'),
    path('appointments/approve/<int:appointment_id>/', views.approve_appointment, name='approve_appointment'),
    path('appointments/reject/<int:appointment_id>/', views.reject_appointment, name='reject_appointment'),
    path('appointments/update-status/<int:appointment_id>/', views.update_appointment_status, name='update_appointment_status'),
    
     # Staff management URLs
    path('staff/', views.staff_management, name='staff_management'),
    path('staff/add/', views.add_staff, name='add_staff'),
    path('staff/edit/<int:staff_id>/', views.edit_staff, name='edit_staff'),
    path('staff/view/<int:staff_id>/', views.view_staff, name='view_staff'),
    path('staff/delete/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('staff/toggle-status/<int:staff_id>/', views.toggle_staff_status, name='toggle_staff_status'),
    path('staff/attendance/', views.staff_attendance, name='staff_attendance'),
    # admin_app/urls.py
path('staff/attendance/delete/<int:record_id>/', views.delete_attendance, name='delete_attendance'),

path('attendance-tracker/', views.attendance_tracker, name='attendance_tracker'),
    path('process-qr-scan/', views.process_qr_scan, name='process_qr_scan'),
    
    path('reports/', views.reports_dashboard, name='reports'),
    path('reports/export/', views.export_reports, name='export_reports'),
]