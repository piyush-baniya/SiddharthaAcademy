from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from .models import Profile
import uuid

# Registration with email verification
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('register')
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return redirect('register')
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already taken!")
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_active = True  # can be False if you want only verified users to login
        user.save()
        
        # send email verification
        token = user.profile.verification_token
        verification_link = request.build_absolute_uri(f'/auth/verify-email/{token}/')
        send_mail(
            'Verify Your Email',
            f'Click the link to verify your email: {verification_link}',
            'noreply@example.com',
            [email],
            fail_silently=False
        )

        messages.success(request, "Account created! Check your email to verify your account.")
        return redirect('login')

    return render(request, 'Authentication/register.html')

# Email verification
def verify_email(request, token):
    try:
        profile = Profile.objects.get(verification_token=token)
        profile.email_verified = True
        profile.save()
        messages.success(request, "Email verified successfully! You can now login.")
    except Profile.DoesNotExist:
        messages.error(request, "Invalid verification link")
    return redirect('login')

# Login
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user:
            if user.profile.email_verified:
                login(request, user)
                return redirect('/')
            else:
                messages.error(request, "Email not verified. Check your inbox.")
                return redirect('login')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('login')

    return render(request, 'Authentication/login.html')

# Logout
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect('login')

# Forgot password
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            token = uuid.uuid4()
            user.profile.verification_token = token
            user.profile.save()
            reset_link = request.build_absolute_uri(f'/auth/reset-password/{token}/')
            send_mail(
                'Reset Your Password',
                f'Click to reset your password: {reset_link}',
                'noreply@example.com',
                [email],
                fail_silently=False
            )
            messages.success(request, "Password reset link sent to your email")
        except User.DoesNotExist:
            messages.error(request, "No account with that email")
        return redirect('forgot_password')
    return render(request, 'Authentication/forgot_password.html')

# Reset password
def reset_password(request, token):
    try:
        profile = Profile.objects.get(verification_token=token)
        user = profile.user
    except Profile.DoesNotExist:
        messages.error(request, "Invalid or expired link")
        return redirect('forgot_password')

    if request.method == 'POST':
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        if password != password2:
            messages.error(request, "Passwords do not match!")
            return redirect(f'/auth/reset-password/{token}/')
        user.set_password(password)
        user.save()
        messages.success(request, "Password reset successfully! Login now.")
        return redirect('login')

    return render(request, 'Authentication/reset_password.html')
