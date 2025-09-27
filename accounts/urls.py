from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import custom_logout


urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'), 
    path('register/', views.register, name= 'register'),
    path('logout/', custom_logout, name='logout'),
    # Use your custom password reset view
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/accounts/password-reset-complete/'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    
    
]
