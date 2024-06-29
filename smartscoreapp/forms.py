from django import forms
from .models import Class, Student, Exam

class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name', 'description']

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'year']  
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': 'true'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'required': 'true'})
        }

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['name', 'class_assigned', 'date']

class ClassNameForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name']

class EditStudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'year'] 