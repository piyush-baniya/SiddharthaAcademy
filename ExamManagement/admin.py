from django.contrib import admin
from .models import ExamRoutine, ExamRoutineItem, StudentExamRemark

class ExamRoutineItemInline(admin.TabularInline):
    model = ExamRoutineItem
    extra = 1

@admin.register(ExamRoutine)
class ExamRoutineAdmin(admin.ModelAdmin):
    list_display = ('examination_name', 'exam_time', 'created_at')
    search_fields = ('examination_name',)
    inlines = [ExamRoutineItemInline]

@admin.register(StudentExamRemark)
class StudentExamRemarkAdmin(admin.ModelAdmin):
    list_display = ('student', 'examination', 'classroom', 'entered_by', 'updated_at')
    search_fields = ('student__first_name', 'student__last_name', 'examination__name')