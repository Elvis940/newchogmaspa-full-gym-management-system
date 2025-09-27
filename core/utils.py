# core/utils.py
from email.message import EmailMessage
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_appointment_confirmation_email(appointment):
    """Send confirmation email for approved appointment"""
    subject = f"Your Appointment at New Chogma-SPA Has Been Confirmed"
    
    html_message = render_to_string('emails/appointment_confirmation.html', {
        'appointment': appointment,
        'client': appointment.client
    })
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [appointment.client.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

import qrcode
from io import BytesIO
from PIL import Image
import base64

def generate_qr_code(data):
    """Generate QR code from data and return BytesIO buffer"""
    try:
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Add data to QR code
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer
        
    except Exception as e:
        print(f"Error generating QR code: {e}")
        # Return empty buffer if generation fails
        return BytesIO()

def send_qr_code_email(user, qr_buffer):
    """Send QR code via email"""
    # Your QR code email logic here
    pass

def send_session_reminder():
    """Send session reminder"""
    # Your session reminder logic here
    pass

# core/utils.py
from django.core.mail import EmailMessage
from django.conf import settings
import io

def send_qr_code_email(user, qr_buffer, qr_data):
    """Send QR code to user via email"""
    try:
        subject = 'Your New Chogma-SPA QR Code'
        
        # Build email message
        message = f'''
Hello {user.get_full_name()},

Here is your permanent QR code for New Chogma-SPA. You can use this QR code for:
- Gym access and attendance tracking
- Quick check-in at reception
- Package management

Your current active packages:
'''

        for pkg in qr_data.get('active_packages', []):
            message += f"- {pkg['name']}: {pkg['remaining_tickets']} tickets remaining (expires: {pkg['expiry_date']})\n"

        message += '''
How to use:
1. Show this QR code at reception when you arrive
2. Staff will scan it to check you in
3. Your session will be automatically deducted from your package

You can also access your QR code anytime from your client dashboard.

Best regards,
New Chogma-SPA Team
'''

        # Create email
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        
        # Attach QR code
        qr_buffer.seek(0)  # Reset buffer position
        email.attach(
            'chogma-spa-qrcode.png',
            qr_buffer.getvalue(),
            'image/png'
        )
        
        email.send()
        return True
        
    except Exception as e:
        print(f"Error sending QR code email: {e}")
        return False

# core/utils.py - Add this function as a fallback
def generate_simple_qr_code(data):
    """Simple QR code generation fallback"""
    try:
        import qrcode
        from io import BytesIO
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer
    except Exception:
        # Return empty buffer if everything fails
        return BytesIO()