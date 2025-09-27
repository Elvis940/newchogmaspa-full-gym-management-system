from email.message import EmailMessage
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .forms import CustomUserCreationForm
from .models import CustomUser
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import CustomUser
from django.db.models import Q
from django.contrib.auth import logout

def home(request):
    return render(request, 'home.html')


def custom_logout(request):
    logout(request)
    return redirect('/')


def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = CustomUser.objects.get(email=email)
            
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build reset link
            reset_link = f"{request.scheme}://{request.get_host()}/accounts/password-reset-confirm/{uid}/{token}/"
            
            # Render HTML email content
            html_content = render_to_string('accounts/password_reset_email.html', {
                'user': user,
                'reset_link': reset_link,
            })
            
            # Create plain text version
            text_content = f"""
Password Reset Request - New Chogma-SPA

Hello {user.get_full_name() or user.username},

You're receiving this email because you requested a password reset for your New Chogma-SPA account.

Please click the link below to reset your password:
{reset_link}

This link will expire in 24 hours for security reasons.

If you didn't request this password reset, please ignore this email. Your account remains secure.

Best regards,
The New Chogma-SPA Team
            """
            
            # Create email message with both HTML and plain text alternatives
            subject = 'Password Reset Request - New Chogma-SPA'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [user.email]
            
            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            messages.success(request, 'Password reset instructions have been sent to your email.')
            return redirect('accounts:password_reset_done')
            
        except CustomUser.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
    
    return render(request, 'accounts/password_reset.html')

def login(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')
        
        # Check if identifier is email or username
        try:
            validate_email(identifier)
            is_email = True
        except ValidationError:
            is_email = False
        
        # Authenticate user
        if is_email:
            try:
                user = CustomUser.objects.get(email=identifier)
                user = authenticate(request, username=user.username, password=password)
            except CustomUser.DoesNotExist:
                user = None
        else:
            user = authenticate(request, username=identifier, password=password)
        
        if user is not None:
            auth_login(request, user)
            # Redirect to appropriate dashboard based on user role
            if user.role == CustomUser.ADMIN:
                return redirect('admin_app:dashboard')
            else:
                return redirect('client:dashboard')
        else:
            messages.error(request, 'Invalid login credentials. Please try again.')
    
    return render(request, 'accounts/login.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please login with your credentials.')
            return redirect('accounts:login')
        else:
            # Pass the form with errors back to the template
            return render(request, 'accounts/register.html', {'form': form})
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})



@login_required
def view_client(request, user_id):
    # Ensure only admins can access this view
    if request.user.role != CustomUser.ADMIN:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('accounts:login')
    
    # Get the client user
    client = get_object_or_404(CustomUser, id=user_id, role=CustomUser.CLIENT)
    
    # Sample data - you would replace this with actual data from your database
    client_data = {
        'total_sessions_used': 15,
        'remaining_sessions': 5,
        'total_spent': 450,
        'upcoming_appointments': 2,
        'attendance_history': [
            {'date': '2024-01-15', 'service': 'Gym Session', 'duration': '2 hours'},
            {'date': '2024-01-14', 'service': 'Massage', 'duration': '1 hour'},
            {'date': '2024-01-12', 'service': 'Sauna', 'duration': '30 mins'},
        ],
        'payment_history': [
            {'date': '2024-01-10', 'amount': 150, 'service': 'Monthly Package', 'status': 'Completed'},
            {'date': '2023-12-10', 'amount': 150, 'service': 'Monthly Package', 'status': 'Completed'},
            {'date': '2023-11-10', 'amount': 150, 'service': 'Monthly Package', 'status': 'Completed'},
        ],
        'current_package': {
            'name': 'Premium Monthly Package',
            'price': 150,
            'sessions': 20,
            'start_date': '2024-01-10',
            'end_date': '2024-02-10',
            'remaining_sessions': 5
        }
    }
    
    context = {
        'user': request.user,
        'client': client,
        'client_data': client_data,
        'active_tab': 'user_management',
    }
    return render(request, 'admin/client_detail.html', context)


