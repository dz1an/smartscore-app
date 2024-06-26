from django import forms
from .models import Class, Student, Exam, TestSet

GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
)

class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name', 'description']

class StudentForm(forms.ModelForm):
    year = forms.IntegerField(
        label='Year', 
        widget=forms.NumberInput(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500'
        })
    )

    gender = forms.ChoiceField(
        choices=Student.GENDER_CHOICES,
        label='Gender',
        widget=forms.Select(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500'
        })
    )

    class Meta:
        model = Student
        fields = ['name', 'year', 'gender']

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['name', 'class_assigned', 'date', 'exam_id']

class ClassNameForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name']

class EditStudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'year', 'assigned_class']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'mt-1 block w-full shadow-sm sm:text-sm border-gray-300 dark:border-gray-700 rounded-md dark:bg-gray-900 dark:text-white'})

class TestSetForm(forms.ModelForm):
    class Meta:
        model = TestSet
        fields = ['exam', 'student', 'name']
