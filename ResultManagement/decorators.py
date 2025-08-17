# ResultManagement/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from management.models import Teacher, ClassSubject

def admin_required(view_func):
    """Decorator to ensure only admin users can access the view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not request.user.is_superuser:
            messages.error(request, "Access denied. Admin privileges required.")
            return redirect('result:marks_entry_dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def subject_teacher_required(view_func):
    """Decorator to ensure only subject teacher or admin can access the view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Get teacher instance
        try:
            teacher = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            messages.error(request, "Access denied. Teacher account required.")
            return redirect('result:marks_entry_dashboard')
        
        # Check if accessing marks entry for specific configuration
        config_id = kwargs.get('config_id')
        if config_id:
            from .models import ExamConfiguration
            try:
                config = ExamConfiguration.objects.get(id=config_id)
                # Check if teacher teaches this subject in this class
                class_subject = ClassSubject.objects.filter(
                    classroom=config.classroom,
                    subject=config.subject,
                    teacher=teacher
                ).exists()
                
                if not class_subject:
                    messages.error(request, "Access denied. You don't teach this subject in this class.")
                    return redirect('result:marks_entry_dashboard')
                    
            except ExamConfiguration.DoesNotExist:
                messages.error(request, "Invalid configuration.")
                return redirect('result:marks_entry_dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def class_teacher_required(view_func):
    """Decorator to ensure only class teacher or admin can access the view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Get teacher instance
        try:
            teacher = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            messages.error(request, "Access denied. Teacher account required.")
            return redirect('result:extracurricular_grades_dashboard')
        
        # Check if accessing extracurricular entry for specific class
        class_id = kwargs.get('class_id')
        if class_id:
            from management.models import Class
            try:
                classroom = Class.objects.get(id=class_id)
                if classroom.class_teacher != teacher:
                    messages.error(request, "Access denied. You are not the class teacher for this class.")
                    return redirect('result:extracurricular_grades_dashboard')
                    
            except Class.DoesNotExist:
                messages.error(request, "Invalid class.")
                return redirect('result:extracurricular_grades_dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def rate_limit(max_requests=100, window_seconds=3600):
    """Simple rate limiting decorator"""
    request_counts = {}
    
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            import time
            
            # Get client IP
            client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
            current_time = time.time()
            
            # Clean old requests
            request_counts[client_ip] = [
                req_time for req_time in request_counts.get(client_ip, [])
                if current_time - req_time < window_seconds
            ]
            
            # Check rate limit
            if len(request_counts.get(client_ip, [])) >= max_requests:
                return HttpResponseForbidden("Rate limit exceeded. Please try again later.")
            
            # Add current request
            if client_ip not in request_counts:
                request_counts[client_ip] = []
            request_counts[client_ip].append(current_time)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def secure_headers(view_func):
    """Add security headers to the response"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
    return _wrapped_view