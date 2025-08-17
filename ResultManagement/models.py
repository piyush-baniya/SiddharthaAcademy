# ResultManagement/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from management.models import Class, Subject, Student, Teacher, Examination
from decimal import Decimal, ROUND_HALF_UP

class ExamConfiguration(models.Model):
    """
    Configuration for each exam including full marks and pass marks
    """
    examination = models.ForeignKey(Examination, on_delete=models.CASCADE, related_name='configurations')
    classroom = models.ForeignKey(Class, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    
    # Theory configuration
    full_theory_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    pass_theory_marks = models.DecimalField(max_digits=5, decimal_places=2, default=40)
    
    # Practical configuration
    full_practical_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    pass_practical_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    
    # Overall configuration
    has_practical = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('examination', 'classroom', 'subject')
        
    def __str__(self):
        return f"{self.examination.name} - {self.classroom.name} - {self.subject.name}"

class StudentResult(models.Model):
    """
    Individual student result for a specific exam and subject
    """
    examination = models.ForeignKey(Examination, on_delete=models.CASCADE, related_name='student_results')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    exam_config = models.ForeignKey(ExamConfiguration, on_delete=models.CASCADE)
    
    # Marks obtained
    theory_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    practical_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Calculated fields
    total_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=5, blank=True)
    grade_point = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    
    # Status fields
    is_passed = models.BooleanField(default=False)
    is_theory_passed = models.BooleanField(default=False)
    is_practical_passed = models.BooleanField(default=True)  # Default true for subjects without practicals
    
    # Meta information
    entered_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='entered_results')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('examination', 'student', 'subject')
        
    def save(self, *args, **kwargs):
        self.calculate_result()
        super().save(*args, **kwargs)
    
    def calculate_result(self):
        """Calculate total marks, percentage, grade, and pass status"""
        if not self.exam_config:
            return
            
        # Calculate total marks
        theory = self.theory_marks or 0
        practical = self.practical_marks or 0
        self.total_marks = theory + practical
        
        # Calculate percentage
        full_marks = self.exam_config.full_theory_marks + (self.exam_config.full_practical_marks or 0)
        if full_marks > 0:
            self.percentage = (self.total_marks / full_marks) * 100
        else:
            self.percentage = 0
            
        # Check pass status
        self.is_theory_passed = theory >= self.exam_config.pass_theory_marks
        if self.exam_config.has_practical:
            self.is_practical_passed = practical >= self.exam_config.pass_practical_marks
        else:
            self.is_practical_passed = True
            
        self.is_passed = self.is_theory_passed and self.is_practical_passed
        
        # Calculate grade and grade point (4.0 scale)
        self.grade, self.grade_point = self.calculate_grade_and_gpa()
    
    def calculate_grade_and_gpa(self):
        """Calculate grade and GPA based on percentage"""
        percentage = float(self.percentage or 0)
        
        if not self.is_passed:
            return 'F', Decimal('0.00')
        elif percentage >= 90:
            return 'A+', Decimal('4.00')
        elif percentage >= 80:
            return 'A', Decimal('3.70')
        elif percentage >= 70:
            return 'B+', Decimal('3.30')
        elif percentage >= 60:
            return 'B', Decimal('3.00')
        elif percentage >= 50:
            return 'C+', Decimal('2.70')
        elif percentage >= 40:
            return 'C', Decimal('2.30')
        else:
            return 'D', Decimal('2.00')
    
    def __str__(self):
        return f"{self.student} - {self.subject.name} - {self.examination.name}"

class StudentOverallResult(models.Model):
    """
    Overall result summary for a student in a particular exam
    """
    examination = models.ForeignKey(Examination, on_delete=models.CASCADE, related_name='overall_results')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='overall_results')
    
    # Overall statistics
    total_subjects = models.IntegerField(default=0)
    subjects_passed = models.IntegerField(default=0)
    subjects_failed = models.IntegerField(default=0)
    
    # GPA calculation
    total_grade_points = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    cgpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    overall_grade = models.CharField(max_length=5, blank=True)
    
    # Overall percentage
    total_marks_obtained = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_full_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    overall_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Status
    is_promoted = models.BooleanField(default=False)
    
    # Extra-curricular grades
    extracurricular_grade = models.CharField(max_length=10, blank=True)
    extracurricular_remarks = models.TextField(blank=True)
    extracurricular_entered_by = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='entered_extracurricular'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('examination', 'student')
    
    def calculate_overall_result(self):
        """Calculate overall result based on individual subject results"""
        subject_results = StudentResult.objects.filter(
            examination=self.examination,
            student=self.student
        )
        
        self.total_subjects = subject_results.count()
        self.subjects_passed = subject_results.filter(is_passed=True).count()
        self.subjects_failed = self.total_subjects - self.subjects_passed
        
        # Calculate totals
        self.total_marks_obtained = sum(result.total_marks or 0 for result in subject_results)
        self.total_full_marks = sum(
            (result.exam_config.full_theory_marks or 0) + (result.exam_config.full_practical_marks or 0)
            for result in subject_results
        )
        
        # Calculate overall percentage
        if self.total_full_marks > 0:
            self.overall_percentage = (self.total_marks_obtained / self.total_full_marks) * 100
        else:
            self.overall_percentage = 0
            
        # Calculate CGPA
        valid_results = subject_results.filter(grade_point__isnull=False)
        if valid_results.exists():
            self.total_grade_points = sum(result.grade_point or 0 for result in valid_results)
            self.cgpa = self.total_grade_points / valid_results.count()
            self.cgpa = self.cgpa.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            self.cgpa = Decimal('0.00')
            
        # Determine overall grade
        self.overall_grade = self.get_overall_grade()
        
        # Determine promotion status (passed if no failed subjects)
        self.is_promoted = self.subjects_failed == 0
        
        self.save()
    
    def get_overall_grade(self):
        """Get overall grade based on CGPA"""
        cgpa = float(self.cgpa or 0)
        if cgpa >= 3.8:
            return 'A+'
        elif cgpa >= 3.5:
            return 'A'
        elif cgpa >= 3.0:
            return 'B+'
        elif cgpa >= 2.7:
            return 'B'
        elif cgpa >= 2.3:
            return 'C+'
        elif cgpa >= 2.0:
            return 'C'
        else:
            return 'F'
    
    def __str__(self):
        return f"{self.student} - {self.examination.name} - CGPA: {self.cgpa}"