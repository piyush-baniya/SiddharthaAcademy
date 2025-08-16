from django.db import models
from management.models import Subject, Class, Examination, Student, Teacher

class ExamRoutine(models.Model):
    examination_name = models.CharField(max_length=255)
    exam_time = models.CharField(max_length=100, blank=True, null=True)
    note_above = models.TextField(blank=True, null=True)
    note_below = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.examination_name

class ExamRoutineItem(models.Model):
    routine = models.ForeignKey(ExamRoutine, on_delete=models.CASCADE, related_name='items')
    exam_date = models.DateField()
    class_name = models.CharField(max_length=80)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    class Meta:
        ordering = ['exam_date', 'class_name']
        unique_together = ()


    def __str__(self):
        return f"{self.class_name} — {self.subject.name} on {self.exam_date}"














class StudentExamRemark(models.Model):
    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='exam_remarks')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_remarks')
    examination = models.ForeignKey(Examination, on_delete=models.CASCADE, related_name='exam_remarks')
    remarks = models.TextField(blank=True, null=True)
    entered_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, related_name='entered_remarks')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('classroom', 'student', 'examination')

    def __str__(self):
        return f"Remark for {self.student} in {self.examination}"
