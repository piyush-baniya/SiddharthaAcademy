# forms.py
from django import forms
from .models import ExamRoutine

class ExamRoutineForm(forms.ModelForm):
    class Meta:
        model = ExamRoutine
        fields = ['examination', 'note']
        widgets = {
            'examination': forms.Select(attrs={'class': 'w-full border border-gray-300 rounded-lg p-3'}),
            'note': forms.Textarea(attrs={'class': 'w-full border border-gray-300 rounded-lg p-3 h-24 resize-none'}),
        }
        help_texts = {
            'examination': 'Select the examination for which you are creating the routine.',
            'note': 'Optional notes regarding the exam routine.',
        }
