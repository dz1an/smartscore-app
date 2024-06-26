from django import forms
from .models import Class, Student, Exam

class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name']

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'email']

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['name', 'class_assigned']
