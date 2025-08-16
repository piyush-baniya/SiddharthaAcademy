from django.urls import path
from . import views

urlpatterns = [
    # Contacts
    path("contact/", views.ContactUs, name="Contact"),
    path("contact/list/", views.contact_list, name="contact_list"),
    path('manage/contacts/<int:id>/delete/', views.contact_delete, name='contact_delete'),
    path('manage/contacts/update/', views.contact_reply, name='contact_reply'),

    # Students
    path('students/', views.student_list, name='list'),
    path('students/add/', views.add_student, name='add_student'),
    path('edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('delete/<int:student_id>/', views.delete_student, name='delete_student'),

    # Teachers
    path('teachers/', views.teacher_list, name='teachers_list'),
    path('teachers/add/', views.add_teacher, name='add_teacher'),
    path("teachers/edit/<int:teacher_id>/", views.edit_teacher, name="edit_teacher"),
    path('teachers/delete/<int:teacher_id>/', views.delete_teacher, name='delete_teacher'),

    # Classes
    path('classes/', views.class_list, name='class_list'),
    path('classes/add/', views.add_class, name='class_add'),
    path('classes/edit/<int:class_id>/', views.edit_class, name='class_edit'),
    path('classes/delete/<int:class_id>/', views.delete_class, name='class_delete'),

    # Attendance
    path('attendance/', views.attendance, name='attendance'),

    # Subjects
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/add/', views.subject_add, name='subject_add'),
    path('subjects/edit/<int:pk>/', views.subject_edit, name='subject_edit'),
    path('subjects/delete/<int:pk>/', views.subject_delete, name='subject_delete'),

    # Examinations
    path('exams/', views.examination_list, name='examination_list'),
    path('examinations/add/', views.examination_add, name='examination_add'),
    path('examinations/<int:exam_id>/edit/', views.examination_edit, name='examination_edit'),
    path('examinations/<int:exam_id>/delete/', views.examination_delete, name='examination_delete'),

    # Enter marks for specific exam
    # e.g., for classroom ID
     path('exams/<int:exam_id>/classroom/<int:classroom_id>/enter-marks/', views.enter_marks, name='enter_marks'),



    # Extra-curricular grades
    path('classes/<int:classroom_id>/enter-extracurricular-grades/', views.enter_extracurricular_grades, name='enter_extracurricular_grades'),

    # Results management
    path('results/', views.results_management, name='results_management'),

    # Settings
    path('settings/', views.settings, name='settings'),
]
