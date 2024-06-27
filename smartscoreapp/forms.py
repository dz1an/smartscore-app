from django import forms
from .models import Class, Student, Exam

class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name']

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'class_assigned']
        # Ensure class_assigned is required
        widgets = {
            'class_assigned': forms.Select(attrs={'class': 'form-control', 'required': 'true'})
        }

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['name', 'class_assigned', 'date']

class ClassNameForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name']
