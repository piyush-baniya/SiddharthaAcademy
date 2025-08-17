# ResultManagement/admin.py
from django.contrib import admin
from .models import ExamConfiguration, StudentResult, StudentOverallResult

@admin.register(ExamConfiguration)
class ExamConfigurationAdmin(admin.ModelAdmin):
    list_display = ('examination', 'classroom', 'subject', 'full_theory_marks', 'pass_theory_marks', 'has_practical')
    list_filter = ('examination', 'classroom', 'has_practical', 'created_at')
    search_fields = ('examination__name', 'classroom__name', 'subject__name')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('examination', 'classroom', 'subject')
        }),
        ('Theory Configuration', {
            'fields': ('full_theory_marks', 'pass_theory_marks')
        }),
        ('Practical Configuration', {
            'fields': ('has_practical', 'full_practical_marks', 'pass_practical_marks')
        }),
    )

@admin.register(StudentResult)
class StudentResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'examination', 'subject', 'theory_marks', 'practical_marks', 'total_marks', 'grade', 'is_passed')
    list_filter = ('examination', 'subject', 'grade', 'is_passed', 'created_at')
    search_fields = ('student__first_name', 'student__last_name', 'student__roll_number')
    ordering = ('-created_at', 'student__roll_number')
    readonly_fields = ('total_marks', 'percentage', 'grade', 'grade_point', 'is_passed', 'is_theory_passed', 'is_practical_passed')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('examination', 'student', 'subject', 'exam_config')
        }),
        ('Marks', {
            'fields': ('theory_marks', 'practical_marks')
        }),
        ('Calculated Results', {
            'fields': ('total_marks', 'percentage', 'grade', 'grade_point'),
            'classes': ('collapse',)
        }),
        ('Pass Status', {
            'fields': ('is_passed', 'is_theory_passed', 'is_practical_passed'),
            'classes': ('collapse',)
        }),
        ('Meta Information', {
            'fields': ('entered_by',),
            'classes': ('collapse',)
        }),
    )

@admin.register(StudentOverallResult)
class StudentOverallResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'examination', 'total_subjects', 'subjects_passed', 'subjects_failed', 'cgpa', 'overall_grade', 'is_promoted')
    list_filter = ('examination', 'overall_grade', 'is_promoted', 'created_at')
    search_fields = ('student__first_name', 'student__last_name', 'student__roll_number')
    ordering = ('-created_at', 'student__roll_number')
    readonly_fields = ('total_subjects', 'subjects_passed', 'subjects_failed', 'total_grade_points', 'cgpa', 'overall_grade', 'total_marks_obtained', 'total_full_marks', 'overall_percentage', 'is_promoted')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('examination', 'student')
        }),
        ('Subject Statistics', {
            'fields': ('total_subjects', 'subjects_passed', 'subjects_failed')
        }),
        ('Overall Performance', {
            'fields': ('total_marks_obtained', 'total_full_marks', 'overall_percentage', 'total_grade_points', 'cgpa', 'overall_grade', 'is_promoted')
        }),
        ('Extra-curricular', {
            'fields': ('extracurricular_grade', 'extracurricular_remarks', 'extracurricular_entered_by'),
            'classes': ('collapse',)
        }),
    )