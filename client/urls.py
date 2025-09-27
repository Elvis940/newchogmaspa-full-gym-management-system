from django.urls import path
from . import views

app_name = 'client'

urlpatterns = [
    path('dashboard/', views.client_dashboard, name='dashboard'),
    path('profile/', views.client_profile, name='profile'),
    path('services/', views.client_services, name='services'),  # Add this line
    path('appointments/', views.client_appointments, name='appointments'),
    path('appointments/book/', views.book_appointment, name='book_appointment'),
    path('appointments/cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
    path('appointments/get-slots/', views.get_available_slots_for_date, name='get_available_slots'),
   
    
    # ... other URLs ...
    path('gym-sessions/', views.gym_sessions, name='gym_sessions'),
    path('generate-qr/', views.generate_user_qr, name='generate_qr'),
    path('download-history/<str:format_type>/', views.download_attendance_history, name='download_history'),
    path('services/get-details/<int:service_id>/', views.get_service_details, name='get_service_details'),
    # In your urls.py
    path('clear-attendance-history/', views.clear_attendance_history, name='clear_attendance_history'),
    path('my-qrcode/', views.client_qr_code, name='client_qr_code'),
    
    
path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('clear-attendance-history/', views.clear_attendance_history, name='clear_attendance_history'),

]