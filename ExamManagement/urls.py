from django.urls import path
from . import views

app_name = 'exam'  # change or remove if you don't use app namespaces

urlpatterns = [
    path('routine/create/', views.create_routine, name='create_routine'),
    path('routine/<int:pk>/', views.routine_detail, name='routine_detail'),
    path('routine/<int:pk>/preview/', views.routine_preview, name='routine_preview'),  # HTML preview
    path('routine/<int:pk>/pdf/', views.routine_pdf, name='routine_pdf'),  # download PDF
    path('routine/<int:pk>/edit/', views.edit_routine, name='edit_routine'),
    path('results/enter/subject/<int:class_subject_id>/<int:exam_id>/', views.enter_subject_marks, name='enter_subject_marks'), 
]