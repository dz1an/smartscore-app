from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Class, Student, Exam, TestSet
from django.contrib.auth.models import User

class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name', 'description']

class StudentBulkUploadForm(forms.Form):
    csv_file = forms.FileField(label="Upload CSV")

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['first_name', 'last_name', 'middle_initial', 'student_id']

    def __init__(self, *args, **kwargs):
        class_instance = kwargs.pop('assigned_class', None)
        super(StudentForm, self).__init__(*args, **kwargs)
        if class_instance:
            self.instance.assigned_class = class_instance

    def clean_student_id(self):
        student_id = self.cleaned_data['student_id']
        assigned_class = self.instance.assigned_class
        if Student.objects.filter(student_id=student_id, assigned_class=assigned_class).exists():
            raise forms.ValidationError("Student ID must be unique within the assigned class.")
        return student_id

    
class ExamForm(forms.ModelForm):
    class_assigned = forms.ModelChoiceField(queryset=Class.objects.all(), required=False)

    class Meta:
        model = Exam
        fields = ['name', 'class_assigned']  # Removed 'exam_id'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ExamForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['class_assigned'].queryset = Class.objects.filter(user=user)


class ClassNameForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name']

class EditStudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['first_name', 'last_name', 'middle_initial']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'mt-1 block w-full shadow-sm sm:text-sm border-gray-300 dark:border-gray-700 rounded-md dark:bg-gray-900 dark:text-white'})

class TestSetForm(forms.ModelForm):
    class Meta:
        model = TestSet
        fields = ['exam', 'student', 'set_no']

class UserCreationWithEmailForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('email', 'username', 'password1', 'password2')

class AddStudentToExamForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['first_name', 'last_name', 'middle_initial', 'student_id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500'})
