from django.shortcuts import render, redirect, get_object_or_404
import os
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from .models import ExamRoutine, ExamRoutineItem
from management.models import Subject
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
from reportlab.lib.units import inch
from reportlab.platypus import Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from django.utils.html import format_html
from django.contrib.auth.decorators import login_required
from management.models import ClassSubject, StudentExamMark
from management.models import Teacher
from management.models import Student
from management.models import Examination
import json


def create_routine(request):
    subjects = Subject.objects.all().order_by('name')

    if request.method == 'POST':
        exam_name = request.POST.get('examination_name', '').strip()
        exam_time = request.POST.get('exam_time', '').strip()
        note_above = request.POST.get('note_above', '').strip()
        note_below = request.POST.get('note_below', '').strip()

        class_names = request.POST.getlist('class_names[]')
        exam_dates = request.POST.getlist('exam_date[]')

        if not exam_name:
            messages.error(request, "Please enter Examination name.")
        elif not exam_dates:
            messages.error(request, "Please add at least one exam date (row).")
        elif not class_names:
            messages.error(request, "Please add at least one class column.")
        else:
            routine = ExamRoutine.objects.create(
                examination_name=exam_name,
                exam_time=exam_time or None,
                note_above=note_above or None,
                note_below=note_below or None
            )

            for r_index, date_str in enumerate(exam_dates):
                if not date_str:
                    continue
                try:
                    exam_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except Exception:
                    continue

                for c_index, class_name in enumerate(class_names):
                    field_name = f"subject_{r_index}_{c_index}"
                    subject_id = request.POST.get(field_name)
                    if subject_id:
                        try:
                            subj = Subject.objects.get(id=subject_id)
                            ExamRoutineItem.objects.create(
                                routine=routine,
                                exam_date=exam_date,
                                class_name=class_name,
                                subject=subj
                            )
                        except Subject.DoesNotExist:
                            continue

            messages.success(request, "Exam routine created.")
            return redirect('exam:routine_detail', pk=routine.pk)

    return render(request, 'Examination/create_routine.html', {
        'subjects': subjects
    })

def routine_detail(request, pk):
    routine = get_object_or_404(ExamRoutine, pk=pk)
    items = routine.items.all()
    class_names = sorted(list({it.class_name for it in items}))
    dates = sorted(list({it.exam_date for it in items}))

    grid = {}
    for it in items:
        grid.setdefault(it.exam_date, {})[it.class_name] = it.subject.name

    return render(request, 'Examination/routine_detail.html', {
        'routine': routine,
        'class_names': class_names,
        'dates': dates,
        'grid': grid
    })


def routine_preview(request, pk):
    routine = get_object_or_404(ExamRoutine, pk=pk)

    items = ExamRoutineItem.objects.filter(routine=routine).order_by('exam_date')

    class_names = sorted(set(item.class_name for item in items))
    dates = sorted(set(item.exam_date for item in items))

    grid = {}
    for date in dates:
        grid[date] = {}
        for cls in class_names:
            subject = next(
                (item.subject.name for item in items if item.exam_date == date and item.class_name == cls),
                None
            )
            grid[date][cls] = subject

    context = {
        'routine': routine,
        'class_names': class_names,
        'dates': dates,
        'grid': grid,
    }
    return render(request, 'Examination/routine_preview.html', context)

def routine_pdf(request, pk):
    routine = get_object_or_404(ExamRoutine, pk=pk)
    items = routine.items.all()
    class_names = sorted(list({it.class_name for it in items})) or []
    dates = sorted(list({it.exam_date for it in items})) or []

    header = ["Date"] + class_names
    table_data = [header]
    for d in dates:
        row = [d.strftime('%Y-%m-%d')]
        for cls in class_names:
            subj = items.filter(exam_date=d, class_name=cls).first()
            row.append(subj.subject.name if subj else "")
        table_data.append(row)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=36, rightMargin=36, topMargin=72, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    # Custom styles
    school_name_style = ParagraphStyle('schoolName', parent=styles['Title'], alignment=1, fontSize=16, spaceAfter=2)
    school_info_style = ParagraphStyle('schoolInfo', parent=styles['Normal'], alignment=1, fontSize=10, textColor=colors.grey)
    exam_time_style = ParagraphStyle(
        'examTime',
        parent=styles['Normal'],
        alignment=TA_LEFT,      # left alignment
        fontName='Helvetica-Bold',  # bold font
        fontSize=10,
        spaceAfter=12
    )

    # Logo & school info
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'src', 'logo.png')
    logo_width = 0.8 * inch
    logo_height = 0.8 * inch

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=logo_width, height=logo_height)
    else:
        logo = Paragraph("No Logo Found", styles['Normal'])

    school_info = [
        Paragraph("Siddhartha Academy", school_name_style),
        Paragraph("Srijananagar-5, Bhaktapur", school_info_style),
        Paragraph("Phone: 01-6615178 | Email: siddharthabkt@gmail.com", school_info_style),
    ]

    # Table for logo and school info side-by-side with minimal spacing
    header_data = [[logo, school_info]]

    # Set logo width and small gap after logo: 2-3px = ~2 points
    small_gap = 2  # points, roughly 2px

    header_table = Table(header_data, colWidths=[logo_width, 400])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),   # no left padding logo
        ('RIGHTPADDING', (0, 0), (0, 0), small_gap),  # very small right padding logo cell
        ('LEFTPADDING', (1, 0), (1, 0), 0),   # no left padding text cell
        ('RIGHTPADDING', (1, 0), (1, 0), 0),  # no right padding text cell
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)

    # Exam time centered under header table if exists
    if routine.exam_time:
        elements.append(Paragraph(f"Time: {routine.exam_time}", exam_time_style))

    elements.append(Spacer(1, 12))

    # Examination Name centered below header
    title_style = styles['Title']
    title_style.alignment = 1  # center
    elements.append(Paragraph(routine.examination_name, title_style))
    elements.append(Spacer(1, 12))

    # Note above if exists
    if routine.note_above:
        elements.append(Paragraph(routine.note_above, styles['Normal']))
        elements.append(Spacer(1, 12))

    # Calculate table column widths dynamically
    page_width = landscape(A4)[0] - doc.leftMargin - doc.rightMargin
    num_classes = len(class_names)
    if num_classes == 0:
        col_widths = [page_width]
    elif num_classes == 1:
        col_widths = [page_width * 0.3, page_width * 0.7]
    else:
        date_col_width = page_width * 0.15
        other_col_width = (page_width - date_col_width) / num_classes
        col_widths = [date_col_width] + [other_col_width] * num_classes

    # Create routine table
    table = Table(table_data, repeatRows=1, colWidths=col_widths)
    tbl_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f2937')),  # dark header
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
    ])
    table.setStyle(tbl_style)
    elements.append(table)
    elements.append(Spacer(1, 12))

    # Note below if exists
    if routine.note_below:
        elements.append(Paragraph(routine.note_below, styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="exam_routine_{routine.pk}.pdf"'
    return response



















def edit_routine(request, pk):
    routine = get_object_or_404(ExamRoutine, pk=pk)
    subjects = Subject.objects.all()

    if request.method == "POST":
        # Extract form data
        routine.examination_name = request.POST.get("examination_name", "").strip()
        routine.exam_time = request.POST.get("exam_time", "").strip()
        routine.note_above = request.POST.get("note_above", "").strip()
        routine.note_below = request.POST.get("note_below", "").strip()
        routine.save()

        # Classes (columns) sent as list
        class_names = request.POST.getlist("class_names[]")
        # Dates sent as list
        exam_dates = request.POST.getlist("exam_date[]")

        # Remove existing items
        routine.items.all().delete()

        # Loop through rows and classes to create ExamRoutineItems
        for r_idx, exam_date_str in enumerate(exam_dates):
            for c_idx, cls_name in enumerate(class_names):
                subj_id = request.POST.get(f"subject_{r_idx}_{c_idx}", "")
                if subj_id:
                    try:
                        subj = Subject.objects.get(id=int(subj_id))
                    except Subject.DoesNotExist:
                        subj = None
                    if subj:
                        ExamRoutineItem.objects.create(
                            routine=routine,
                            exam_date=exam_date_str,
                            class_name=cls_name,
                            subject=subj
                        )
        messages.success(request, "Exam routine updated successfully!")
        return redirect('exam:routine_detail', pk=routine.pk)

    # Prepare data for Alpine.js reactive form
    class_names = sorted(list(set(it.class_name for it in routine.items.all())))
    rows = []
    for d in sorted(set(it.exam_date for it in routine.items.all())):
        subjects_map = {}
        for cls in class_names:
            item = routine.items.filter(exam_date=d, class_name=cls).first()
            subjects_map[cls] = item.subject.id if item else ""
        rows.append({"date": d.strftime("%Y-%m-%d"), "subjects": subjects_map})

    context = {
        "routine": routine,
        "subjects": subjects,
        "class_names": json.dumps(class_names),
        "rows": json.dumps(rows),
        "m": messages.get_messages(request),  # for message display
    }
    return render(request, "Examination/edit_routine.html", context)





















@login_required
def enter_subject_marks(request, class_subject_id, exam_id):
    teacher = get_object_or_404(Teacher, user=request.user)
    class_subject = get_object_or_404(ClassSubject, id=class_subject_id, teacher=teacher)
    examination = get_object_or_404(Examination, id=exam_id)
    classroom = class_subject.classroom

    # Students in this class
    students = Student.objects.filter(classroom=classroom, is_active=True).order_by('roll_number')

    # Get max and pass marks from subject model or fixed (example)
    max_theory = 100  # Or you can add this field in Subject model
    max_practical = 50
    pass_theory = 40
    pass_practical = 20

    if request.method == 'POST':
        for student in students:
            theory_mark = request.POST.get(f'theory_{student.id}', '0')
            practical_mark = request.POST.get(f'practical_{student.id}', '0')
            try:
                theory_mark = float(theory_mark)
            except:
                theory_mark = 0
            try:
                practical_mark = float(practical_mark)
            except:
                practical_mark = 0

            StudentExamMark.objects.update_or_create(
                examination=examination,
                student=student,
                defaults={
                    'theory_marks': theory_mark,
                    'practical_marks': practical_mark,
                }
            )
        return redirect('enter_subject_marks', class_subject_id=class_subject.id, exam_id=examination.id)

    # Existing marks
    marks = StudentExamMark.objects.filter(examination=examination, student__in=students)
    marks_dict = {m.student_id: m for m in marks}

    context = {
        'class_subject': class_subject,
        'examination': examination,
        'students': students,
        'marks_dict': marks_dict,
        'max_theory': max_theory,
        'max_practical': max_practical,
        'pass_theory': pass_theory,
        'pass_practical': pass_practical,
    }
    return render(request, 'results/enter_subject_marks.html', context)