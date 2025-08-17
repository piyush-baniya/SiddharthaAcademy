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



# Add to views.py
from playwright.sync_api import sync_playwright
import tempfile
import os

@login_required
def generate_result_pdf(request, student_id, exam_id):
    """Generate PDF using Playwright - exact HTML rendering"""
    
    student = get_object_or_404(Student, id=student_id)
    exam = get_object_or_404(Examination, id=exam_id)
    
    overall_result = StudentOverallResult.objects.filter(
        student=student, examination=exam
    ).first()
    
    if not overall_result:
        messages.error(request, "No results found for this student.")
        return redirect('result:view_results')
    
    subject_results = StudentResult.objects.filter(
        student=student, examination=exam
    ).select_related('subject', 'exam_config').order_by('subject__name')
    
    context = {
        'student': student,
        'exam': exam,
        'overall_result': overall_result,
        'subject_results': subject_results,
        'school_info': {
            'name': 'Siddhartha Academy',
            'address': 'Sallaghari,Srijana Nagar-Bhaktapur',
            'phone': '01- 6615178'
        },
        'attendance_days': 59,
        'total_days': 67,
        'current_date': exam.date,
    }
    
    # Use your existing HTML template
    template = get_template('ResultManagement/result_card_pdf.html')
    html_content = template.render(context)
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # Set page content
            page.set_content(html_content)
            
            # Generate PDF with exact HTML rendering
            pdf_bytes = page.pdf(
                format='A4',
                print_background=True,  # Include background colors/images
                margin={
                    'top': '10mm',
                    'bottom': '10mm',
                    'left': '8mm',
                    'right': '8mm'
                }
            )
            
            browser.close()
            
            filename = f"result_{student.first_name}_{student.last_name}_{student.roll_number}.pdf"
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
    except Exception as e:
        messages.error(request, f"PDF generation failed: {str(e)}")
        return redirect('result:view_results')
    



























# Updated views.py - Playwright Bulk PDF Generation

from playwright.sync_api import sync_playwright
import zipfile
from io import BytesIO
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import get_template
from django.contrib.auth.decorators import login_required, user_passes_test

@login_required
@user_passes_test(is_admin)
def generate_class_results_pdf(request, exam_id, class_id):
    """Generate PDF for all students in a class using Playwright - FIXED ASYNC ISSUE"""
    
    examination = get_object_or_404(Examination, id=exam_id)
    classroom = get_object_or_404(Class, id=class_id)
    
    # Get all students with results - DEBUG: Print count
    students = Student.objects.filter(
        classroom=classroom,
        is_active=True,
        overall_results__examination=examination
    ).order_by('roll_number')
    
    print(f"DEBUG: Found {students.count()} students")
    
    if not students:
        messages.error(request, "No students with results found for this class and exam.")
        return redirect('result:view_results')
    
    # CRITICAL FIX: Gather ALL data BEFORE starting Playwright
    # This prevents async context issues
    students_data = []
    
    for student in students:
        overall_result = StudentOverallResult.objects.filter(
            student=student, examination=examination
        ).first()
        
        if overall_result:
            subject_results = StudentResult.objects.filter(
                student=student, examination=examination
            ).select_related('subject', 'exam_config').order_by('subject__name')
            
            # Convert QuerySet to list to avoid async issues
            subject_results_list = list(subject_results)
            
            student_data = {
                'student': student,
                'overall_result': overall_result,
                'subject_results': subject_results_list,
                'context': {
                    'student': student,
                    'exam': examination,
                    'overall_result': overall_result,
                    'subject_results': subject_results_list,
                    'school_info': {
                        'name': 'Siddhartha Academy',
                        'address': 'Sallaghari,Srijana Nagar-Bhaktapur',
                        'phone': '01- 6615178'
                    },
                    'attendance_days': 59,
                    'total_days': 67,
                    'current_date': examination.date,
                }
            }
            students_data.append(student_data)
    
    print(f"DEBUG: Prepared data for {len(students_data)} students")
    
    if not students_data:
        messages.error(request, "No students have complete result data.")
        return redirect('result:view_results')
    
    zip_filename = f"{examination.name}_{classroom.name}_results.zip"
    pdf_count = 0
    error_count = 0
    
    try:
        # Create zip file in memory
        zip_buffer = BytesIO()
        
        with sync_playwright() as p:
            # Launch browser once for all PDFs (more efficient)
            browser = p.chromium.launch(headless=True)
            print("DEBUG: Browser launched")
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                
                for student_data in students_data:
                    try:
                        student = student_data['student']
                        context = student_data['context']
                        
                        print(f"DEBUG: Processing student {student.first_name} {student.last_name}")
                        
                        # Render HTML using pre-gathered data
                        template = get_template('ResultManagement/result_card_pdf.html')
                        html_content = template.render(context)
                        
                        print(f"DEBUG: HTML content length: {len(html_content)}")
                        
                        # Create new page for this student
                        page = browser.new_page()
                        
                        # Set page content with timeout
                        page.set_content(html_content, wait_until='domcontentloaded', timeout=30000)
                        
                        # Wait a bit more for any dynamic content
                        page.wait_for_timeout(1000)
                        
                        # Generate PDF with exact HTML rendering
                        pdf_bytes = page.pdf(
                            format='A4',
                            print_background=True,  # Include background colors/images
                            margin={
                                'top': '10mm',
                                'bottom': '10mm',
                                'left': '8mm',
                                'right': '8mm'
                            }
                        )
                        
                        print(f"DEBUG: Generated PDF size: {len(pdf_bytes)} bytes")
                        
                        # Close the page
                        page.close()
                        
                        # Validate PDF bytes
                        if len(pdf_bytes) > 0:
                            # Add PDF to ZIP with student name
                            pdf_filename = f"{student.first_name}_{student.last_name}_{student.roll_number}.pdf"
                            zip_file.writestr(pdf_filename, pdf_bytes)
                            pdf_count += 1
                            print(f"DEBUG: Added {pdf_filename} to ZIP")
                        else:
                            print(f"ERROR: Empty PDF generated for {student}")
                            error_count += 1
                            
                    except Exception as e:
                        # Log error but continue with other students
                        print(f"ERROR generating PDF for {student_data['student']}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        error_count += 1
                        continue
            
            # Close browser
            browser.close()
            print(f"DEBUG: Browser closed. Generated {pdf_count} PDFs, {error_count} errors")
        
        # Check if ZIP has content
        zip_buffer.seek(0)
        zip_size = len(zip_buffer.getvalue())
        print(f"DEBUG: ZIP file size: {zip_size} bytes")
        
        if zip_size <= 22:  # Empty ZIP file is ~22 bytes
            messages.error(request, f"No PDFs were generated successfully. Check server logs for details. Processed {len(students_data)} students, {error_count} errors.")
            return redirect('result:view_results')
        
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        messages.success(request, f"Generated {pdf_count} PDFs successfully!")
        return response
        
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Bulk PDF generation failed: {str(e)}")
        return redirect('result:view_results')


# ALTERNATIVE SIMPLE VERSION - Add this as backup

@login_required
@user_passes_test(is_admin)
def generate_class_results_pdf_simple(request, exam_id, class_id):
    """Simplified version for debugging"""
    
    examination = get_object_or_404(Examination, id=exam_id)
    classroom = get_object_or_404(Class, id=class_id)
    
    # Simplified query - get ALL active students first
    students = Student.objects.filter(
        classroom=classroom,
        is_active=True
    ).order_by('roll_number')
    
    print(f"DEBUG: Found {students.count()} active students in {classroom.name}")
    
    if not students:
        messages.error(request, "No active students found in this class.")
        return redirect('result:view_results')
    
    # Filter students who actually have results
    students_with_results = []
    for student in students:
        overall_result = StudentOverallResult.objects.filter(
            student=student, examination=examination
        ).first()
        if overall_result:
            students_with_results.append(student)
    
    print(f"DEBUG: Found {len(students_with_results)} students with results")
    
    if not students_with_results:
        messages.error(request, f"No students have results for {examination.name} in {classroom.name}")
        return redirect('result:view_results')
    
    # Try to generate just ONE PDF first
    try:
        student = students_with_results[0]  # Test with first student
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Get student data
            overall_result = StudentOverallResult.objects.filter(
                student=student, examination=examination
            ).first()
            
            subject_results = StudentResult.objects.filter(
                student=student, examination=examination
            ).select_related('subject', 'exam_config').order_by('subject__name')
            
            context = {
                'student': student,
                'exam': examination,
                'overall_result': overall_result,
                'subject_results': subject_results,
                'school_info': {
                    'name': 'Siddhartha Academy',
                    'address': 'Sallaghari,Srijana Nagar-Bhaktapur',
                    'phone': '01- 6615178'
                },
                'attendance_days': 59,
                'total_days': 67,
                'current_date': examination.date,
            }
            
            # Test HTML rendering
            template = get_template('ResultManagement/result_card_pdf.html')
            html_content = template.render(context)
            
            print(f"DEBUG: HTML content length: {len(html_content)}")
            
            # Set content and generate PDF
            page.set_content(html_content, wait_until='domcontentloaded')
            pdf_bytes = page.pdf(format='A4', print_background=True)
            
            browser.close()
            
            # Return single PDF for testing
            if len(pdf_bytes) > 0:
                filename = f"test_{student.first_name}_{student.last_name}.pdf"
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                messages.success(request, f"Test PDF generated successfully! Size: {len(pdf_bytes)} bytes")
                return response
            else:
                messages.error(request, "Generated PDF is empty")
                return redirect('result:view_results')
                
    except Exception as e:
        print(f"CRITICAL ERROR in simple version: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Test PDF generation failed: {str(e)}")
        return redirect('result:view_results')
import asyncio
from playwright.async_api import async_playwright

@login_required
@user_passes_test(is_admin)
def generate_class_results_pdf_async(request, exam_id, class_id):
    """Async version for better performance with large classes"""
    
    examination = get_object_or_404(Examination, id=exam_id)
    classroom = get_object_or_404(Class, id=class_id)
    
    students = Student.objects.filter(
        classroom=classroom,
        is_active=True,
        overall_results__examination=examination
    ).order_by('roll_number')
    
    if not students:
        messages.error(request, "No students with results found for this class and exam.")
        return redirect('result:view_results')
    
    async def generate_bulk_pdfs():
        zip_buffer = BytesIO()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                
                # Process multiple students concurrently
                tasks = []
                
                for student in students:
                    task = generate_student_pdf(browser, student, examination, zip_file)
                    tasks.append(task)
                
                # Process up to 5 PDFs concurrently (adjust based on server capacity)
                semaphore = asyncio.Semaphore(5)
                
                async def bounded_task(task):
                    async with semaphore:
                        return await task
                
                await asyncio.gather(*[bounded_task(task) for task in tasks])
            
            await browser.close()
        
        return zip_buffer
    
    async def generate_student_pdf(browser, student, examination, zip_file):
        try:
            overall_result = StudentOverallResult.objects.filter(
                student=student, examination=examination
            ).first()
            
            if overall_result:
                subject_results = StudentResult.objects.filter(
                    student=student, examination=examination
                ).select_related('subject', 'exam_config').order_by('subject__name')
                
                context = {
                    'student': student,
                    'exam': examination,
                    'overall_result': overall_result,
                    'subject_results': subject_results,
                    'school_info': {
                        'name': 'Siddhartha Academy',
                        'address': 'Sallaghari,Srijana Nagar-Bhaktapur',
                        'phone': '01- 6615178'
                    },
                    'attendance_days': 59,
                    'total_days': 67,
                    'current_date': examination.date,
                }
                
                template = get_template('ResultManagement/result_card_pdf.html')
                html_content = template.render(context)
                
                page = await browser.new_page()
                await page.set_content(html_content, wait_until='networkidle')
                
                pdf_bytes = await page.pdf(
                    format='A4',
                    print_background=True,
                    margin={
                        'top': '10mm',
                        'bottom': '10mm', 
                        'left': '8mm',
                        'right': '8mm'
                    }
                )
                
                await page.close()
                
                pdf_filename = f"{student.first_name}_{student.last_name}_{student.roll_number}.pdf"
                zip_file.writestr(pdf_filename, pdf_bytes)
                
        except Exception as e:
            print(f"Error generating PDF for {student}: {str(e)}")
    
    try:
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        zip_buffer = loop.run_until_complete(generate_bulk_pdfs())
        loop.close()
        
        zip_buffer.seek(0)
        zip_filename = f"{examination.name}_{classroom.name}_results.zip"
        
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        return response
        
    except Exception as e:
        messages.error(request, f"Bulk PDF generation failed: {str(e)}")
        return redirect('result:view_results')


# Progress tracking version (optional - for large classes)
from django.http import JsonResponse
from django.core.cache import cache

@login_required
@user_passes_test(is_admin)
def generate_class_results_pdf_with_progress(request, exam_id, class_id):
    """Generate PDFs with progress tracking for large classes"""
    
    examination = get_object_or_404(Examination, id=exam_id)
    classroom = get_object_or_404(Class, id=class_id)
    
    students = Student.objects.filter(
        classroom=classroom,
        is_active=True,
        overall_results__examination=examination
    ).order_by('roll_number')
    
    if not students:
        messages.error(request, "No students with results found for this class and exam.")
        return redirect('result:view_results')
    
    total_students = students.count()
    progress_key = f"bulk_pdf_progress_{exam_id}_{class_id}_{request.user.id}"
    
    # Initialize progress
    cache.set(progress_key, {'completed': 0, 'total': total_students, 'status': 'processing'}, 300)
    
    try:
        zip_buffer = BytesIO()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                
                for index, student in enumerate(students, 1):
                    try:
                        # Generate PDF (same code as above)
                        overall_result = StudentOverallResult.objects.filter(
                            student=student, examination=examination
                        ).first()
                        
                        if overall_result:
                            # ... (PDF generation code same as above)
                            subject_results = StudentResult.objects.filter(
                                student=student, examination=examination
                            ).select_related('subject', 'exam_config').order_by('subject__name')
                            
                            context = {
                                'student': student,
                                'exam': examination,
                                'overall_result': overall_result,
                                'subject_results': subject_results,
                                'school_info': {
                                    'name': 'Siddhartha Academy',
                                    'address': 'Sallaghari,Srijana Nagar-Bhaktapur',
                                    'phone': '01- 6615178'
                                },
                                'attendance_days': 59,
                                'total_days': 67,
                                'current_date': examination.date,
                            }
                            
                            template = get_template('ResultManagement/result_card_pdf.html')
                            html_content = template.render(context)
                            
                            page = browser.new_page()
                            page.set_content(html_content, wait_until='networkidle')
                            
                            pdf_bytes = page.pdf(
                                format='A4',
                                print_background=True,
                                margin={
                                    'top': '10mm',
                                    'bottom': '10mm',
                                    'left': '8mm', 
                                    'right': '8mm'
                                }
                            )
                            
                            page.close()
                            
                            pdf_filename = f"{student.first_name}_{student.last_name}_{student.roll_number}.pdf"
                            zip_file.writestr(pdf_filename, pdf_bytes)
                        
                        # Update progress
                        cache.set(progress_key, {
                            'completed': index, 
                            'total': total_students, 
                            'status': 'processing',
                            'current_student': f"{student.first_name} {student.last_name}"
                        }, 300)
                        
                    except Exception as e:
                        print(f"Error generating PDF for {student}: {str(e)}")
                        continue
            
            browser.close()
        
        # Mark as completed
        cache.set(progress_key, {'completed': total_students, 'total': total_students, 'status': 'completed'}, 300)
        
        zip_buffer.seek(0)
        zip_filename = f"{examination.name}_{classroom.name}_results.zip"
        
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        return response
        
    except Exception as e:
        cache.set(progress_key, {'completed': 0, 'total': total_students, 'status': 'error', 'error': str(e)}, 300)
        messages.error(request, f"Bulk PDF generation failed: {str(e)}")
        return redirect('result:view_results')

@login_required
def bulk_pdf_progress(request, exam_id, class_id):
    """API endpoint to check bulk PDF generation progress"""
    progress_key = f"bulk_pdf_progress_{exam_id}_{class_id}_{request.user.id}"
    progress = cache.get(progress_key, {'completed': 0, 'total': 0, 'status': 'not_started'})
    return JsonResponse(progress)