# ResultManagement/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from decimal import Decimal

from management.models import Class, Subject, Student, Teacher, Examination, ClassSubject
from .models import ExamConfiguration, StudentResult, StudentOverallResult

def is_admin_or_teacher(user):
    """Check if user is admin or a teacher"""
    return user.is_superuser or Teacher.objects.filter(user=user).exists()

def is_admin(user):
    """Check if user is admin"""
    return user.is_superuser

def get_teacher(user):
    """Get teacher instance from user"""
    try:
        return Teacher.objects.get(user=user)
    except Teacher.DoesNotExist:
        return None

# ============ EXAM CONFIGURATION VIEWS ============

@login_required
@user_passes_test(is_admin)
def exam_configuration_list(request):
    """List all exam configurations"""
    configurations = ExamConfiguration.objects.select_related(
        'examination', 'classroom', 'subject'
    ).order_by('-created_at')
    
    return render(request, 'ResultManagement/exam_config_list.html', {
        'configurations': configurations
    })

@login_required
@user_passes_test(is_admin)
def exam_configuration_setup(request):
    """Setup exam configuration for selected exam and class"""
    examinations = Examination.objects.all().order_by('-date')
    classes = Class.objects.all().order_by('name')
    
    if request.method == 'POST':
        exam_id = request.POST.get('examination')
        class_id = request.POST.get('classroom')
        
        if not exam_id or not class_id:
            messages.error(request, "Please select both examination and class.")
            return render(request, 'ResultManagement/exam_config_setup.html', {
                'examinations': examinations,
                'classes': classes
            })
        
        examination = get_object_or_404(Examination, id=exam_id)
        classroom = get_object_or_404(Class, id=class_id)
        
        # Get subjects for this class that are part of the examination
        class_subjects = ClassSubject.objects.filter(
            classroom=classroom,
            subject=examination.subject
        ).select_related('subject')
        
        if not class_subjects.exists():
            messages.error(request, "No subjects found for this class and examination combination.")
            return render(request, 'ResultManagement/exam_config_setup.html', {
                'examinations': examinations,
                'classes': classes
            })
        
        return redirect('result:exam_configuration_create', exam_id=exam_id, class_id=class_id)
    
    return render(request, 'ResultManagement/exam_config_setup.html', {
        'examinations': examinations,
        'classes': classes
    })

@login_required
@user_passes_test(is_admin)
def exam_configuration_create(request, exam_id, class_id):
    """Create exam configurations for all subjects in a class"""
    examination = get_object_or_404(Examination, id=exam_id)
    classroom = get_object_or_404(Class, id=class_id)
    
    # Get all subjects for this class
    class_subjects = ClassSubject.objects.filter(classroom=classroom).select_related('subject')
    
    if request.method == 'POST':
        created_count = 0
        updated_count = 0
        
        for class_subject in class_subjects:
            subject = class_subject.subject
            
            # Get form data for this subject
            full_theory = request.POST.get(f'full_theory_{subject.id}')
            pass_theory = request.POST.get(f'pass_theory_{subject.id}')
            has_practical = request.POST.get(f'has_practical_{subject.id}') == 'on'
            full_practical = request.POST.get(f'full_practical_{subject.id}', 0) if has_practical else 0
            pass_practical = request.POST.get(f'pass_practical_{subject.id}', 0) if has_practical else 0
            
            if not full_theory or not pass_theory:
                continue
                
            # Create or update configuration
            config, created = ExamConfiguration.objects.update_or_create(
                examination=examination,
                classroom=classroom,
                subject=subject,
                defaults={
                    'full_theory_marks': Decimal(full_theory),
                    'pass_theory_marks': Decimal(pass_theory),
                    'has_practical': has_practical,
                    'full_practical_marks': Decimal(full_practical or 0),
                    'pass_practical_marks': Decimal(pass_practical or 0),
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        if created_count > 0 or updated_count > 0:
            messages.success(request, f"Configuration saved! Created: {created_count}, Updated: {updated_count}")
        else:
            messages.warning(request, "No configurations were saved. Please check your inputs.")
            
        return redirect('result:exam_configuration_list')
    
    # Get existing configurations
    existing_configs = {}
    for config in ExamConfiguration.objects.filter(examination=examination, classroom=classroom):
        existing_configs[config.subject.id] = config
    
    return render(request, 'ResultManagement/exam_config_create.html', {
        'examination': examination,
        'classroom': classroom,
        'class_subjects': class_subjects,
        'existing_configs': existing_configs,
    })

# ============ MARKS ENTRY VIEWS ============

@login_required
@user_passes_test(is_admin_or_teacher)
def marks_entry_dashboard(request):
    """Dashboard for marks entry"""
    user = request.user
    teacher = get_teacher(user)
    
    if user.is_superuser:
        # Admin can see all exam configurations
        configurations = ExamConfiguration.objects.select_related(
            'examination', 'classroom', 'subject'
        ).order_by('-examination__date')
    elif teacher:
        # Teacher can only see configurations for subjects they teach
        configurations = ExamConfiguration.objects.filter(
            subject__in=teacher.class_subjects.values('subject')
        ).select_related('examination', 'classroom', 'subject').order_by('-examination__date')
    else:
        configurations = ExamConfiguration.objects.none()
    
    return render(request, 'ResultManagement/marks_entry_dashboard.html', {
        'configurations': configurations,
        'is_admin': user.is_superuser,
    })

@login_required
@user_passes_test(is_admin_or_teacher)
def enter_marks(request, config_id):
    """Enter marks for students in a specific exam configuration"""
    config = get_object_or_404(ExamConfiguration, id=config_id)
    user = request.user
    teacher = get_teacher(user)
    
    # Security check: Only admin or subject teacher can enter marks
    if not user.is_superuser:
        if not teacher:
            return HttpResponseForbidden("Access denied.")
        
        # Check if teacher teaches this subject in this class
        class_subject = ClassSubject.objects.filter(
            classroom=config.classroom,
            subject=config.subject,
            teacher=teacher
        ).first()
        
        if not class_subject:
            messages.error(request, "You don't have permission to enter marks for this subject.")
            return redirect('result:marks_entry_dashboard')
    
    # Get students in this class
    students = Student.objects.filter(
        classroom=config.classroom,
        is_active=True
    ).order_by('roll_number')
    
    if request.method == 'POST':
        saved_count = 0
        
        for student in students:
            theory_marks = request.POST.get(f'theory_{student.id}')
            practical_marks = request.POST.get(f'practical_{student.id}') if config.has_practical else None
            
            # Validate marks
            if theory_marks is not None and theory_marks != '':
                try:
                    theory_marks = Decimal(theory_marks)
                    if theory_marks < 0 or theory_marks > config.full_theory_marks:
                        messages.error(request, f"Invalid theory marks for {student}. Must be between 0 and {config.full_theory_marks}")
                        continue
                except (ValueError, TypeError):
                    theory_marks = None
            else:
                theory_marks = None
                
            if config.has_practical and practical_marks is not None and practical_marks != '':
                try:
                    practical_marks = Decimal(practical_marks)
                    if practical_marks < 0 or practical_marks > config.full_practical_marks:
                        messages.error(request, f"Invalid practical marks for {student}. Must be between 0 and {config.full_practical_marks}")
                        continue
                except (ValueError, TypeError):
                    practical_marks = None
            else:
                practical_marks = None
            
            # Save or update result
            result, created = StudentResult.objects.update_or_create(
                examination=config.examination,
                student=student,
                subject=config.subject,
                defaults={
                    'exam_config': config,
                    'theory_marks': theory_marks,
                    'practical_marks': practical_marks,
                    'entered_by': teacher if teacher else None,
                }
            )
            saved_count += 1
        
        if saved_count > 0:
            messages.success(request, f"Marks saved for {saved_count} students.")
            
            # Update overall results for affected students
            for student in students:
                overall_result, created = StudentOverallResult.objects.get_or_create(
                    examination=config.examination,
                    student=student
                )
                overall_result.calculate_overall_result()
        
        return redirect('result:enter_marks', config_id=config_id)
    
    # Get existing results
    existing_results = {}
    for result in StudentResult.objects.filter(
        examination=config.examination,
        subject=config.subject,
        student__in=students
    ):
        existing_results[result.student.id] = result
    
    return render(request, 'ResultManagement/enter_marks.html', {
        'config': config,
        'students': students,
        'existing_results': existing_results,
    })

# ============ EXTRACURRICULAR GRADES VIEWS ============

@login_required
def extracurricular_grades_dashboard(request):
    """Dashboard for extracurricular grades entry"""
    user = request.user
    teacher = get_teacher(user)
    
    if user.is_superuser:
        # Admin can see all classes
        classes = Class.objects.all().order_by('name')
    elif teacher:
        # Teacher can only see classes they are class teacher of
        classes = Class.objects.filter(class_teacher=teacher)
    else:
        classes = Class.objects.none()
    
    examinations = Examination.objects.all().order_by('-date')
    
    return render(request, 'ResultManagement/extracurricular_dashboard.html', {
        'classes': classes,
        'examinations': examinations,
    })

@login_required
def enter_extracurricular_grades(request, exam_id, class_id):
    """Enter extracurricular grades for students"""
    examination = get_object_or_404(Examination, id=exam_id)
    classroom = get_object_or_404(Class, id=class_id)
    user = request.user
    teacher = get_teacher(user)
    
    # Security check: Only admin or class teacher can enter extracurricular grades
    if not user.is_superuser:
        if not teacher or classroom.class_teacher != teacher:
            messages.error(request, "You don't have permission to enter extracurricular grades for this class.")
            return redirect('result:extracurricular_grades_dashboard')
    
    students = Student.objects.filter(
        classroom=classroom,
        is_active=True
    ).order_by('roll_number')
    
    if request.method == 'POST':
        saved_count = 0
        
        for student in students:
            grade = request.POST.get(f'grade_{student.id}', '').strip()
            remarks = request.POST.get(f'remarks_{student.id}', '').strip()
            
            # Get or create overall result
            overall_result, created = StudentOverallResult.objects.get_or_create(
                examination=examination,
                student=student
            )
            
            overall_result.extracurricular_grade = grade
            overall_result.extracurricular_remarks = remarks
            overall_result.extracurricular_entered_by = teacher if teacher else None
            overall_result.save()
            
            saved_count += 1
        
        messages.success(request, f"Extracurricular grades saved for {saved_count} students.")
        return redirect('result:enter_extracurricular_grades', exam_id=exam_id, class_id=class_id)
    
    # Get existing overall results
    existing_results = {}
    for result in StudentOverallResult.objects.filter(examination=examination, student__in=students):
        existing_results[result.student.id] = result
    
    return render(request, 'ResultManagement/enter_extracurricular.html', {
        'examination': examination,
        'classroom': classroom,
        'students': students,
        'existing_results': existing_results,
    })

# ============ RESULTS VIEW ============

@login_required
@user_passes_test(is_admin_or_teacher)
def view_results(request):
    """View student results"""
    examinations = Examination.objects.all().order_by('-date')
    classes = Class.objects.all().order_by('name')
    
    exam_id = request.GET.get('exam')
    class_id = request.GET.get('class')
    
    results = []
    examination = None
    classroom = None
    
    if exam_id and class_id:
        examination = get_object_or_404(Examination, id=exam_id)
        classroom = get_object_or_404(Class, id=class_id)
        
        # Get all students and their results
        students = Student.objects.filter(classroom=classroom, is_active=True).order_by('roll_number')
        
        for student in students:
            # Get overall result
            overall_result = StudentOverallResult.objects.filter(
                examination=examination,
                student=student
            ).first()
            
            # Get subject results
            subject_results = StudentResult.objects.filter(
                examination=examination,
                student=student
            ).select_related('subject', 'exam_config')
            
            results.append({
                'student': student,
                'overall_result': overall_result,
                'subject_results': subject_results,
            })
    
    return render(request, 'ResultManagement/view_results.html', {
        'examinations': examinations,
        'classes': classes,
        'examination': examination,
        'classroom': classroom,
        'results': results,
    })

# ============ AJAX VIEWS ============

@csrf_exempt
@login_required
def check_marks_status(request):
    """AJAX view to check if marks are pass/fail in real-time"""
    if request.method == 'POST':
        data = json.loads(request.body)
        config_id = data.get('config_id')
        theory_marks = data.get('theory_marks')
        practical_marks = data.get('practical_marks')
        
        try:
            config = ExamConfiguration.objects.get(id=config_id)
        except ExamConfiguration.DoesNotExist:
            return JsonResponse({'error': 'Invalid configuration'})
        
        response = {
            'theory_status': 'pass',
            'practical_status': 'pass',
            'overall_status': 'pass'
        }
        
        # Check theory marks
        if theory_marks is not None and theory_marks != '':
            try:
                theory_marks = float(theory_marks)
                if theory_marks < float(config.pass_theory_marks):
                    response['theory_status'] = 'fail'
            except (ValueError, TypeError):
                response['theory_status'] = 'invalid'
        
        # Check practical marks
        if config.has_practical:
            if practical_marks is not None and practical_marks != '':
                try:
                    practical_marks = float(practical_marks)
                    if practical_marks < float(config.pass_practical_marks):
                        response['practical_status'] = 'fail'
                except (ValueError, TypeError):
                    response['practical_status'] = 'invalid'
        
        # Overall status
        if response['theory_status'] == 'fail' or response['practical_status'] == 'fail':
            response['overall_status'] = 'fail'
        elif response['theory_status'] == 'invalid' or response['practical_status'] == 'invalid':
            response['overall_status'] = 'invalid'
        
        return JsonResponse(response)
    
    return JsonResponse({'error': 'Invalid request method'})


















from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import get_object_or_404
from io import BytesIO
import os

try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False

from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import get_object_or_404
from io import BytesIO
from xhtml2pdf import pisa
from django.contrib.staticfiles import finders

@login_required
def generate_result_pdf(request, student_id, exam_id):
    """Generate PDF result card using xhtml2pdf (Windows compatible)"""
    
    # Get student and exam data
    student = get_object_or_404(Student, id=student_id)
    exam = get_object_or_404(Examination, id=exam_id)
    
    # Get student's overall result
    overall_result = StudentOverallResult.objects.filter(
        student=student, 
        examination=exam
    ).first()
    
    if not overall_result:
        messages.error(request, "No results found for this student in this exam.")
        return redirect('result:view_results')
    
    # Get all subject results
    subject_results = StudentResult.objects.filter(
        student=student,
        examination=exam
    ).select_related('subject', 'exam_config').order_by('subject__name')
    
    # School information
    school_info = {
        'name': 'Siddhartha Academy',
        'address': 'Sallaghari,Srijana Nagar-Bhaktapur',
        'phone': '01- 6615178'
    }
    
    # Context data
    context = {
        'student': student,
        'exam': exam,
        'overall_result': overall_result,
        'subject_results': subject_results,
        'school_info': school_info,
        'attendance_days': 59,
        'total_days': 67,
        'current_date': exam.date,
    }
    
    # Get template and render HTML
    template = get_template('ResultManagement/result_card_pdf.html')
    html_string = template.render(context)
    
    # Create PDF
    result = BytesIO()
    pdf = pisa.pisaDocument(
        BytesIO(html_string.encode("UTF-8")), 
        result,
        encoding='UTF-8'
    )
    
    if not pdf.err:
        filename = f"result_card_{student.first_name}_{student.last_name}_{student.roll_number}.pdf"
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    return HttpResponse("Error generating PDF", status=500)

def generate_pdf_xhtml2pdf(request, context):
    """Alternative PDF generation using xhtml2pdf"""
    template = get_template('ResultManagement/result_card_pdf.html')
    html_string = template.render(context)
    
    # Create PDF
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_string.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="result_card_{context["student"].roll_number}_{context["exam"].name}.pdf"'
        return response
    
    return HttpResponse("Error generating PDF", status=500)

@login_required
def view_result_html(request, student_id, exam_id):
    """View result card as HTML (for testing/preview)"""
    
    student = get_object_or_404(Student, id=student_id)
    exam = get_object_or_404(Examination, id=exam_id)
    
    overall_result = StudentOverallResult.objects.filter(
        student=student, 
        examination=exam
    ).first()
    
    if not overall_result:
        return HttpResponse("No results found for this student in this exam.", status=404)
    
    subject_results = StudentResult.objects.filter(
        student=student,
        examination=exam
    ).select_related('subject', 'exam_config').order_by('subject__name')
    
    school_info = {
        'name': 'Siddhartha Academy',
        'address': 'Sallaghari,Srijana Nagar-Bhaktapur',
        'phone': '01- 6615178'
    }
    
    context = {
        'student': student,
        'exam': exam,
        'overall_result': overall_result,
        'subject_results': subject_results,
        'school_info': school_info,
        'attendance_days': 59,
        'total_days': 67,
        'current_date': exam.date,
    }
    
    return render(request, 'ResultManagement/result_card_pdf.html', context)


@login_required
@user_passes_test(is_admin)
def generate_class_results_pdf(request, exam_id, class_id):
    """Generate PDF for all students in a class"""
    
    examination = get_object_or_404(Examination, id=exam_id)
    classroom = get_object_or_404(Class, id=class_id)
    
    # Get all students with results
    students = Student.objects.filter(
        classroom=classroom,
        is_active=True,
        overall_results__examination=examination
    ).order_by('roll_number')
    
    if not students:
        messages.error(request, "No students with results found for this class and exam.")
        return redirect('result:view_results')
    
    # Create a ZIP file containing all PDFs
    import zipfile
    from django.http import HttpResponse
    
    zip_filename = f"{examination.name}_{classroom.name}_results.zip"
    
    # Create zip file in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        
        for student in students:
            # Generate PDF for each student
            overall_result = StudentOverallResult.objects.filter(
                student=student, examination=examination
            ).first()
            
            if overall_result:
                subject_results = StudentResult.objects.filter(
                    student=student, examination=examination
                ).select_related('subject', 'exam_config').order_by('subject__name')
                
                school_info = {
                    'name': 'Siddhartha Academy',
                    'address': 'Sallaghari,Srijana Nagar-Bhaktapur',
                    'phone': '01- 6615178'
                }
                
                context = {
                    'student': student,
                    'exam': examination,
                    'overall_result': overall_result,
                    'subject_results': subject_results,
                    'school_info': school_info,
                    'attendance_days': 59,
                    'total_days': 67,
                    'current_date': examination.date,
                }
                
                template = get_template('ResultManagement/result_card_pdf.html')
                html_string = template.render(context)
    
    zip_buffer.seek(0)
    
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
    
    return response