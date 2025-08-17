from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Contact, Student, Teacher, Class, ClassSubject, Subject, Examination, ExtraCurricularGrade, StudentExamMark
from django.db.models import Prefetch
from django.contrib.auth.models import User


# ---------- STUDENTS ----------

def student_list(request):
    students = Student.objects.all().order_by('roll_number')
    return render(request, 'Management/student_list.html', {'students': students})

def add_student(request):
    if request.method == 'POST':
        student = Student(
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            roll_number=request.POST.get('roll_number'),
            date_of_birth=request.POST.get('date_of_birth'),
            section=request.POST.get('section'),
            father_name=request.POST.get('father_name'),
            mother_name=request.POST.get('mother_name'),
            permanent_address=request.POST.get('permanent_address'),
            temporary_address=request.POST.get('temporary_address'),
            student_contact=request.POST.get('student_contact'),
            guardian_contact=request.POST.get('guardian_contact'),
            is_active=request.POST.get('is_active') == 'on',
            classroom_id=request.POST.get('classroom')  # assign classroom if passed
        )

        # Handle file uploads
        for file_field in ['birth_certificate', 'transfer_certificate', 'photo']:
            if file_field in request.FILES:
                setattr(student, file_field, request.FILES[file_field])

        student.save()
        messages.success(request, "Student added successfully.")
        return redirect('list')

    classes = Class.objects.all()
    return render(request, 'Management/add_student.html', {'classes': classes})

def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    if request.method == 'POST':
        for field in ['first_name', 'last_name', 'roll_number', 'date_of_birth', 'section', 'father_name', 'mother_name', 'permanent_address', 'temporary_address', 'student_contact', 'guardian_contact']:
            setattr(student, field, request.POST.get(field))

        student.is_active = request.POST.get('is_active') == 'on'
        student.classroom_id = request.POST.get('classroom')

        # Handle file uploads
        for file_field in ['birth_certificate', 'transfer_certificate', 'photo']:
            if file_field in request.FILES:
                setattr(student, file_field, request.FILES[file_field])

        student.save()
        messages.success(request, "Student updated successfully.")
        return redirect('list')

    classes = Class.objects.all()
    return render(request, 'Management/edit_student.html', {'student': student, 'classes': classes})

def delete_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        student.delete()
        messages.success(request, "Student deleted successfully.")
        return redirect('list')
    return render(request, 'Management/student_list.html', {'student': student})

# ---------- TEACHERS ----------

def teacher_list(request):
        # Prefetch ClassSubjects per teacher with related class and subject
    teachers = Teacher.objects.prefetch_related(
        Prefetch(
            'class_subjects',
            queryset=ClassSubject.objects.select_related('classroom', 'subject')
        )
    ).all()
    return render(request, 'management/teacher_list.html', {'teachers': teachers})
    

def add_teacher(request):
    class_subjects = ClassSubject.objects.all().select_related('classroom', 'subject')

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        
        # Create User account if email provided
        user = None
        if email:
            username = email.split('@')[0]  # Use email prefix as username
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='temporary123'  # Set temporary password
                )
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email') or None
        phone = request.POST.get('phone') or None
        address = request.POST.get('address') or None
        linkedin_profile = request.POST.get('linkedin_profile') or None
        date_joined = request.POST.get('date_joined') or None
        date_left = request.POST.get('date_left') or None

        # Files
        photo = request.FILES.get('photo')
        related_document = request.FILES.get('related_document')
        cv = request.FILES.get('cv')
        pan_card = request.FILES.get('pan_card')
        citizenship_front = request.FILES.get('citizenship_front')
        citizenship_back = request.FILES.get('citizenship_back')

        # Create teacher object
        teacher = Teacher.objects.create(
            user=user,
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            linkedin_profile=linkedin_profile,
            date_joined=date_joined,
            date_left=date_left,
            photo=photo,
            related_document=related_document,
            cv=cv,
            pan_card=pan_card,
            citizenship_front=citizenship_front,
            citizenship_back=citizenship_back
        )

        # Handle multiple class_subject selections
        selected_cs_ids = request.POST.getlist('class_subjects')  # note plural
        # For each selected ClassSubject, assign teacher
        ClassSubject.objects.filter(id__in=selected_cs_ids).update(teacher=teacher)

        messages.success(request, "Teacher added successfully!")
        return redirect('teachers_list')

    return render(request, 'management/add_teacher.html', {
        'class_subjects': class_subjects,
    })

def edit_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    class_subjects = ClassSubject.objects.all().select_related('classroom', 'subject')

    if request.method == 'POST':
        teacher.full_name = request.POST.get('full_name')
        teacher.email = request.POST.get('email') or None
        teacher.phone = request.POST.get('phone') or None
        teacher.address = request.POST.get('address') or None
        teacher.linkedin_profile = request.POST.get('linkedin_profile') or None
        teacher.date_joined = request.POST.get('date_joined') or None
        teacher.date_left = request.POST.get('date_left') or None

        # File uploads (only update if new file provided)
        for field in ['photo', 'related_document', 'cv', 'pan_card', 'citizenship_front', 'citizenship_back']:
            uploaded_file = request.FILES.get(field)
            if uploaded_file:
                setattr(teacher, field, uploaded_file)

        teacher.save()

        selected_cs_ids = request.POST.getlist('class_subjects')  # list of selected ClassSubject IDs

        # Unassign this teacher from all ClassSubject entries currently assigned to them
        ClassSubject.objects.filter(teacher=teacher).exclude(id__in=selected_cs_ids).update(teacher=None)

        # Assign this teacher to the selected ClassSubject entries
        ClassSubject.objects.filter(id__in=selected_cs_ids).update(teacher=teacher)

        messages.success(request, "Teacher updated successfully!")
        return redirect('teachers_list')

    # Pre-select class_subjects assigned to this teacher
    assigned_cs_ids = teacher.class_subjects.values_list('id', flat=True)

    return render(request, 'management/edit_teacher.html', {
        'teacher': teacher,
        'class_subjects': class_subjects,
        'assigned_cs_ids': list(assigned_cs_ids),
    })


def delete_teacher(request, teacher_id):
    if request.method == "POST":
        teacher = get_object_or_404(Teacher, id=teacher_id)
        teacher.delete()
        messages.success(request, f'Teacher "{teacher.full_name}" has been deleted.')
    return redirect('teachers_list')

# ---------- CLASSES ----------

def class_list(request):
    classes = Class.objects.all()
    return render(request, 'Class/class_list.html', {'classes': classes})

def add_class(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        class_teacher_id = request.POST.get('class_teacher')
        class_teacher = Teacher.objects.filter(id=class_teacher_id).first() if class_teacher_id else None
        
        new_class = Class.objects.create(name=name, class_teacher=class_teacher)
        
        # Also save selected subjects
        selected_subject_ids = request.POST.getlist('subjects')
        if selected_subject_ids:
            new_class.subjects.set(selected_subject_ids)
        
        return redirect('class_list')

    teachers = Teacher.objects.all()
    subjects = Subject.objects.all()  # Add this line
    return render(request, 'Class/class_add.html', {'teachers': teachers, 'subjects': subjects})


def edit_class(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)
    teachers = Teacher.objects.all()
    subjects = Subject.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name')
        class_teacher_id = request.POST.get('class_teacher')
        selected_subject_ids = request.POST.getlist('subjects')

        class_teacher = Teacher.objects.filter(id=class_teacher_id).first() if class_teacher_id else None

        class_instance.name = name
        class_instance.class_teacher = class_teacher
        class_instance.save()

        class_instance.subjects.set(selected_subject_ids)
        return redirect('class_list')

    return render(request, 'Class/class_edit.html', {
        'class_instance': class_instance,
        'teachers': teachers,
        'subjects': subjects,
    })

def delete_class(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
    class_obj.delete()
    return redirect('class_list')

# ---------- SUBJECTS ----------

def subject_list(request):
    subjects = Subject.objects.all().order_by('name')
    return render(request, 'Class/subject_list.html', {'subjects': subjects})

def subject_add(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Subject name cannot be empty.')
        else:
            Subject.objects.create(name=name)
            messages.success(request, f'Subject "{name}" added successfully.')
            return redirect('subject_list')
    return render(request, 'Class/subject_add.html')

def subject_edit(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Subject name cannot be empty.')
        else:
            subject.name = name
            subject.save()
            messages.success(request, f'Subject "{name}" updated successfully.')
            return redirect('subject_list')
    return render(request, 'Class/subject_edit.html', {'subject': subject})

def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        subject.delete()
        messages.success(request, f'Subject "{subject.name}" deleted successfully.')
        return redirect('subject_list')
    return redirect('subject_list')

# ---------- EXAMINATIONS ----------

@login_required
def examination_add(request):
    classes = Class.objects.all()
    subjects = Subject.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        date = request.POST.get('date')
        classroom_ids = request.POST.getlist('classrooms')  # multiple classrooms
        subject_ids = request.POST.getlist('subjects')      # multiple subjects now

        # Basic form validation
        if not all([name, date, classroom_ids, subject_ids]):
            messages.error(request, "All fields are required.")
            return render(request, 'Examination/Examination_add.html', {
                'classes': classes,
                'subjects': subjects
            })

        # Get the selected subjects from DB
        valid_subjects = Subject.objects.filter(id__in=subject_ids)
        if not valid_subjects.exists():
            messages.error(request, "Invalid subjects selected.")
            return render(request, 'Examination/Examination_add.html', {
                'classes': classes,
                'subjects': subjects
            })

        created_count = 0

        # Loop through each classroom & subject combination
        for class_id in classroom_ids:
            for subject in valid_subjects:
                # Only create exam if subject belongs to this class
                if ClassSubject.objects.filter(classroom_id=class_id, subject=subject).exists():
                    exam, created = Examination.objects.get_or_create(
                        name=name,
                        subject=subject,
                        defaults={'date': date}
                    )

                    # Add the classroom to this exam (whether new or existing)
                    exam.classrooms.add(class_id)
                    created_count += 1 if created else 0

        if created_count > 0:
            messages.success(request, f"{created_count} examinations added successfully.")
        else:
            messages.warning(request, "No examinations created — none of the selected subjects are assigned to the selected classes.")

        return redirect('examination_list')

    return render(request, 'Examination/Examination_add.html', {
        'classes': classes,
        'subjects': subjects
    })


@login_required
def examination_edit(request, exam_id):
    exam = get_object_or_404(Examination, id=exam_id)
    classes = Class.objects.all()
    subjects = Subject.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name').strip()
        date = request.POST.get('date')
        classroom_ids = request.POST.getlist('classrooms')  # multiple selection, list of ids
        subject_id = request.POST.get('subject')

        if not all([name, date, classroom_ids, subject_id]):
            messages.error(request, "All fields are required.")
        else:
            subject = Subject.objects.filter(id=subject_id).first()
            if not subject:
                messages.error(request, "Invalid Subject selected.")
            else:
                exam.name = name
                exam.date = date
                exam.subject = subject
                exam.save()

                # Update classrooms many-to-many
                exam.classrooms.set(classroom_ids)
                exam.save()

                messages.success(request, "Examination updated successfully.")
                return redirect('examination_list')

    return render(request, 'Examination/Examination_edit.html', {
        'exam': exam, 'classes': classes, 'subjects': subjects
    })


@login_required
def examination_delete(request, exam_id):
    exam = get_object_or_404(Examination, id=exam_id)
    if request.method == 'POST':
        exam.delete()
        messages.success(request, "Examination deleted successfully.")
        return redirect('examination_list')

# ---------- ENTER MARKS ----------
@login_required
def examination_list(request):
    exams = Examination.objects.prefetch_related('classrooms', 'subject').order_by('-date')

    # Create a flat list of (exam, classroom) pairs
    exam_class_pairs = []
    for exam in exams:
        for classroom in exam.classrooms.all():
            exam_class_pairs.append({
                'exam': exam,
                'classroom': classroom,
                # Get teacher for classroom+subject from ClassSubject
                'teacher': ClassSubject.objects.filter(classroom=classroom, subject=exam.subject).first()
            })

    return render(request, 'Examination/Examination_list.html', {'exam_class_pairs': exam_class_pairs})



# Marks entry view for a particular exam
@login_required
def enter_marks(request, exam_id, classroom_id):
    exam = get_object_or_404(Examination.objects.prefetch_related('classrooms', 'subject'), id=exam_id)
    classroom = get_object_or_404(exam.classrooms, id=classroom_id)  # make sure classroom belongs to exam

    students = Student.objects.filter(
        classroom=classroom,
        is_active=True
    ).order_by('roll_number')

    marks = StudentExamMark.objects.filter(examination=exam, student__in=students)
    marks_dict = {m.student.id: m for m in marks}

    full_marks = {'theory': 100, 'practical': 100}

    if request.method == 'POST':
        for student in students:
            theory_mark = request.POST.get(f'marks_{student.id}_theory')
            practical_mark = request.POST.get(f'marks_{student.id}_practical')

            try:
                theory_mark = float(theory_mark)
            except (ValueError, TypeError):
                theory_mark = None

            try:
                practical_mark = float(practical_mark)
            except (ValueError, TypeError):
                practical_mark = None

            StudentExamMark.objects.update_or_create(
                examination=exam,
                student=student,
                defaults={'theory_marks': theory_mark, 'practical_marks': practical_mark}
            )
        messages.success(request, "Marks saved successfully.")
        return redirect('examination_list')

    context = {
        'exam': exam,
        'classroom': classroom,
        'students': students,
        'marks_dict': marks_dict,
        'full_marks': full_marks,
    }
    return render(request, 'Examination/enter_marks.html', context)


# ---------- EXTRA-CURRICULAR GRADES ----------

@login_required
def enter_extracurricular_grades(request, classroom_id):
    classroom = get_object_or_404(Class, id=classroom_id)
    teacher = Teacher.objects.filter(email=request.user.email).first()

    if classroom.class_teacher != teacher:
        messages.error(request, "You don't have permission to enter extracurricular grades for this class.")
        return redirect('examination_list')

    students = classroom.students.filter(is_active=True).order_by('roll_number')

    if request.method == 'POST':
        for student in students:
            grade = request.POST.get(f'grade_{student.id}')
            remarks = request.POST.get(f'remarks_{student.id}')

            obj, _ = ExtraCurricularGrade.objects.get_or_create(
                student=student,
                classroom=classroom,
                defaults={'grade': '', 'remarks': ''}
            )
            obj.grade = grade or ''
            obj.remarks = remarks or ''
            obj.save()

        messages.success(request, "Extra-curricular grades saved successfully.")
        return redirect('examination_list')

    grades_dict = {}
    for student in students:
        grade_obj = ExtraCurricularGrade.objects.filter(student=student, classroom=classroom).first()
        grades_dict[student.id] = {
            'grade': grade_obj.grade if grade_obj else '',
            'remarks': grade_obj.remarks if grade_obj else '',
        }

    return render(request, 'Examination/Enter_extracurricular_grades.html', {
        'classroom': classroom,
        'students': students,
        'grades_dict': grades_dict,
    })

# ---------- CONTACTS ----------

def ContactUs(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')

        if name and email and message_text and subject:
            Contact.objects.create(name=name, email=email, message=message_text, subject=subject)
            messages.success(request, "Thank you for contacting us!")
        else:
            messages.error(request, "Please fill all fields.")

    return render(request, "Management/contactus.html")

def contact_list(request):
    contacts = Contact.objects.order_by('-created_at')
    return render(request, 'Management/contact_list.html', {'contacts': contacts})

def contact_delete(request, id):
    if request.method == "POST":
        contact = get_object_or_404(Contact, id=id)
        contact.delete()
        messages.success(request, "Contact message deleted successfully.")
    return redirect('contact_list')

@require_http_methods(["POST"])
def contact_reply(request):
    contact_id = request.POST.get('id')
    reply_message = request.POST.get('reply', '').strip()
    status = request.POST.get('status', 'Unresolved')

    contact = get_object_or_404(Contact, id=contact_id)
    if reply_message:
        contact.reply = reply_message
        contact.status = status
        contact.save()

    return redirect('contact_list')

# ---------- MISC ----------

def attendance(request):
    return render(request, 'Management/attendance.html')

def results_management(request):
    return render(request, 'Management/results.html')

def settings(request):
    return render(request, 'Management/settings.html')
