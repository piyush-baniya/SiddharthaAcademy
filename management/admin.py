from django.contrib import admin
from .models import Contact, Student, ClassSubject, Teacher, Subject, Class, Examination, ExtraCurricularGrade, StudentExamMark, OurTeam, StudentVoice, NewsNotice, Gallery, GalleryImage, ClassRoutine, Syllabus, AdmissionForm, CarouselImage

# Register your models here.
admin.site.register(Contact),
admin.site.register(Student),
admin.site.register(ClassSubject),
admin.site.register(Teacher),
admin.site.register(Subject),
admin.site.register(Class),
admin.site.register(Examination),
admin.site.register(ExtraCurricularGrade),
admin.site.register(StudentExamMark)


# New models
admin.site.register(OurTeam)
admin.site.register(StudentVoice)
admin.site.register(NewsNotice)
admin.site.register(Gallery)
admin.site.register(GalleryImage)
admin.site.register(ClassRoutine)
admin.site.register(Syllabus)
admin.site.register(AdmissionForm)
admin.site.register(CarouselImage)




class CarouselImageInline(admin.TabularInline):
    model = CarouselImage
    extra = 3  # number of extra image forms to show












# look what i want is
# 1. exam routine model ( relation from examination model to get examination name and date, relation from subject model to select subject from a dropdown, class name ( no relation from class model as routine can be same for different classes and can be written as class 1-5 ), date of examination of that subject, Note so that i can write some notice in the bottom)

# 2. view and template should be like I want to create a exam routine i head over to the exam routine creation page -> I click create exam routine -> Examination name and date can be selected from a dropdown(relation with examination model), fields should be like exam_Date for that specific subject, subject name can be selected from the dropdown (Relation with subject model) -> i click add subject to add more subjects one by one with same project -> I click add note if i have to write some notice in the bottom of the routine -> i hit the create button and then the routine is create and i can download the pdf of the routine and print it and distribute it. 

# so that's the game plan now give me the models.py, views.py and templates files for this feature with clear file name