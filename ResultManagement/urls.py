# ResultManagement/urls.py
from django.urls import path
from . import views

app_name = 'result'

urlpatterns = [
    # Exam Configuration URLs
    path('config/', views.exam_configuration_list, name='exam_configuration_list'),
    path('config/setup/', views.exam_configuration_setup, name='exam_configuration_setup'),
    path('config/create/<int:exam_id>/<int:class_id>/', views.exam_configuration_create, name='exam_configuration_create'),
    
    # Marks Entry URLs
    path('marks/', views.marks_entry_dashboard, name='marks_entry_dashboard'),
    path('marks/enter/<int:config_id>/', views.enter_marks, name='enter_marks'),
    
    # Extracurricular Grades URLs
    path('extracurricular/', views.extracurricular_grades_dashboard, name='extracurricular_grades_dashboard'),
    path('extracurricular/enter/<int:exam_id>/<int:class_id>/', views.enter_extracurricular_grades, name='enter_extracurricular_grades'),
    
    # Results View URLs
    path('view/', views.view_results, name='view_results'),
    
    # AJAX URLs
    path('ajax/check-marks/', views.check_marks_status, name='check_marks_status'),

    # Result PDF generation
    path('pdf/<int:student_id>/<int:exam_id>/', views.generate_result_pdf, name='generate_result_pdf'),
    path('html/<int:student_id>/<int:exam_id>/', views.view_result_html, name='view_result_html'),


    # Add to urls.py
    path('bulk-pdf-playwright/<int:exam_id>/<int:class_id>/', views.generate_class_results_pdf, name='generate_class_results_pdf_playwright'),

    # Optional: Progress tracking
    path('bulk-pdf-progress/<int:exam_id>/<int:class_id>/',  views.bulk_pdf_progress,  name='bulk_pdf_progress'),
]