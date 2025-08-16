from django.shortcuts import render

# Create your views here.
def Home(request):
    return render(request, "core/index.html")

def Gallery(request):
    return render(request, "Academics/gallery.html")

def AdmissionForm(request):
    return render(request, "Academics/admissionform.html")   

def dashboard(request):
    return render(request, "Management/dashboard.html")    

def News(request):
    return render(request, "Academics/news.html")

def Team(request):
    return render(request, "About/team.html")

def classRoutine(request):
    return render(request, "Class/classroutine.html")

def Mission(request):
    return render(request, "About/mission.html")

def StudentVoices(request):
    return render(request, "Academics/studentvoice.html")

def About(request):
    return render(request, "About/about.html")

def ourstory(request):
    return render(request, "About/ourstory.html")