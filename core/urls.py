from django.urls import path
from . import views

urlpatterns = [
    path("", views.Home, name="Home"),
    path("about/", views.About, name="About"),
    path("story/", views.ourstory, name="ourstory"),
    path("gallery/", views.Gallery, name="Gallery"),  
    path("admission/", views.AdmissionForm, name="AdmissionForm"),
    path("news/", views.News, name="News"),
    path("team/", views.Team, name="Team"),
    path("classroutine/", views.classRoutine, name="classRoutine"),
    path("mission/", views.Mission, name="mission"), 
    path("studentvoices/", views.StudentVoices, name="studentvoices"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
