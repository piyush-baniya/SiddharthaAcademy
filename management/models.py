from django.db import models
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth.models import User


class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField()
    reply = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ('unresolved', 'Unresolved'),
        ('resolved', 'Resolved'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unresolved')

    def __str__(self):
        return self.name


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='teacher_photos/', blank=True, null=True)
    cv = models.FileField(upload_to='teacher_cvs/', blank=True, null=True)
    pan_card = models.FileField(upload_to='teacher_pan_cards/', blank=True, null=True)
    citizenship_front = models.FileField(upload_to='teacher_citizenship_front/', blank=True, null=True)
    citizenship_back = models.FileField(upload_to='teacher_citizenship_back/', blank=True, null=True)
    linkedin_profile = models.URLField(blank=True, null=True)
    date_joined = models.DateField()
    date_left = models.DateField(blank=True, null=True)
    related_document = models.FileField(upload_to='teacher_documents/', blank=True, null=True)

    def __str__(self):
        return self.full_name


class Subject(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Class(models.Model):
    name = models.CharField(max_length=100)  # e.g. "Grade 5", "10A"
    section = models.CharField(max_length=10, blank=True, null=True)  # New section field
    class_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='classes_as_class_teacher'
    )
    subjects = models.ManyToManyField(
        Subject,
        through='ClassSubject',
        related_name='classes'
    )
    def active_student_count(self):
        """Return count of active students in this class"""
        return self.students.filter(is_active=True).count()
    
    def __str__(self):
        if self.section:
            return f"{self.name} - {self.section}"
        return self.name


class ClassSubject(models.Model):
    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='class_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='class_subjects')
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, blank=True, null=True, related_name='class_subjects')

    class Meta:
        # Allow same subject in same class with different teachers
        unique_together = ('classroom', 'subject', 'teacher')

    def __str__(self):
        teacher_name = self.teacher.full_name if self.teacher else "No teacher assigned"
        return f"{self.subject.name} in {self.classroom} taught by {teacher_name}"


class Student(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=5)
    date_of_birth = models.DateField()
    section = models.CharField(max_length=10, blank=True, null=True)  # Optional if student has own section
    father_name = models.CharField(max_length=100)
    mother_name = models.CharField(max_length=100)
    permanent_address = models.TextField()
    temporary_address = models.TextField(blank=True, null=True)
    student_contact = models.CharField(max_length=15)
    guardian_contact = models.CharField(max_length=15, blank=True, null=True)
    birth_certificate = models.FileField(upload_to='documents/', blank=True, null=True)
    transfer_certificate = models.FileField(upload_to='documents/', blank=True, null=True)
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    classroom = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='students'
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.roll_number})"


class Examination(models.Model):
    """
    An examination can be for multiple classes (classrooms) and one subject.
    Each exam has a name and date.
    """
    name = models.CharField(max_length=100)  # e.g. "Midterm 2025"
    classrooms = models.ManyToManyField(
        'Class',
        related_name='examinations'
    )
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.CASCADE,
        related_name='examinations'
    )
    date = models.DateField()

    class Meta:
        unique_together = ('name', 'subject')  # name+subject unique

    def __str__(self):
        class_names = ", ".join(str(cls) for cls in self.classrooms.all())
        return f"{self.name} - {class_names} - {self.subject.name}"


class StudentExamMark(models.Model):
    """
    Stores marks for a student for a specific examination.
    Marks can be theory and practical.
    """
    examination = models.ForeignKey(
        Examination,
        on_delete=models.CASCADE,
        related_name='student_marks'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='exam_marks'
    )
    theory_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    practical_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('examination', 'student')

    def __str__(self):
        return f"Marks of {self.student} in {self.examination}"


class ExtraCurricularGrade(models.Model):
    """
    Extra-curricular grades given by class teacher for a student in a class and exam.
    """
    classroom = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='extracurricular_grades'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='extracurricular_grades'
    )
    examination = models.ForeignKey(
        Examination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extracurricular_grades'
    )
    grade = models.CharField(max_length=10)  # e.g. "A+", "Good", "Excellent"
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('classroom', 'student', 'examination')

    def __str__(self):
        return f"Extra Curricular grade for {self.student} in {self.classroom}"


# Signal to automatically relate new Class to existing Examinations of its subjects, and vice versa

@receiver(post_save, sender=Class)
def add_class_to_exams(sender, instance, created, **kwargs):
    if created:
        # When a new Class is created,
        # automatically link it to Examinations of subjects that the class has
        subjects = instance.subjects.all()
        exams = Examination.objects.filter(subject__in=subjects)
        for exam in exams:
            exam.classrooms.add(instance)
            exam.save()


@receiver(m2m_changed, sender=Examination.classrooms.through)
def classrooms_changed(sender, instance, action, pk_set, **kwargs):
    # When classrooms are added to an exam,
    # you can add additional logic here if needed
    pass



































class CarouselImage(models.Model):
    image = models.ImageField(upload_to='carousel_images/')
    order = models.PositiveIntegerField(default=0)  # to control image order

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image {self.id} - Order {self.order}"
    

# 1. OurTeam
class OurTeam(models.Model):
    profile_pic = models.ImageField(upload_to='ourteam/')
    name = models.CharField(max_length=100)
    post = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

# 2. StudentVoice
class StudentVoice(models.Model):
    profile_pic = models.ImageField(upload_to='student_voices/')
    name = models.CharField(max_length=100)
    classroom = models.ForeignKey('Class', on_delete=models.SET_NULL, null=True, blank=True, related_name='student_voices')
    message = models.TextField()

    def __str__(self):
        return f"{self.name} - {self.classroom}"

# 3. News and Notices
class NewsNotice(models.Model):
    TAG_CHOICES = [
        ('news', 'News'),
        ('notice', 'Notice'),
    ]
    date = models.DateField()
    title = models.CharField(max_length=200)
    description = models.TextField()  # Can contain HTML, text, images (via editor later)
    attached_files = models.FileField(upload_to='news_notices_files/', blank=True, null=True)
    tag = models.CharField(max_length=10, choices=TAG_CHOICES)

    def __str__(self):
        return f"{self.title} ({self.tag})"

# 4. Gallery
class Gallery(models.Model):
    title = models.CharField(max_length=200)
    thumbnail = models.ImageField(upload_to='gallery/thumbnails/')
    description = models.TextField(blank=True)
    date = models.DateField()

    def __str__(self):
        return self.title

class GalleryImage(models.Model):
    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='gallery/images/')

    def __str__(self):
        return f"Image for {self.gallery.title}"

# 5. ClassRoutine
class ClassRoutine(models.Model):
    classroom = models.ForeignKey('Class', on_delete=models.CASCADE, related_name='class_routines')
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE, related_name='class_routines')
    day_of_week = models.CharField(max_length=10, choices=[
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ])
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.classroom} - {self.subject} on {self.day_of_week} ({self.start_time} - {self.end_time})"

# 6. Syllabus
class Syllabus(models.Model):
    class_subject = models.ForeignKey('ClassSubject', on_delete=models.CASCADE, related_name='syllabi')
    description = models.TextField()

    def __str__(self):
        return f"Syllabus for {self.class_subject}"

# 7. AdmissionForm
class AdmissionForm(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    full_name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    address = models.TextField()
    contact = models.CharField(max_length=15)
    parents_name = models.CharField(max_length=150)
    email = models.EmailField()
    applying_for_grade = models.ForeignKey('Class', on_delete=models.SET_NULL, null=True, blank=True, related_name='admission_forms')
    message = models.TextField(blank=True, null=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Admission form - {self.full_name} for {self.applying_for_grade}"
