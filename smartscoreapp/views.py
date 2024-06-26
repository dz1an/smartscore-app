from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Class, Student, Exam, Question
from .forms import ClassForm, StudentForm, ExamForm
from django.contrib.auth.decorators import login_required



def index(request):
    return render(request, 'index.html')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Login successful!")
                return redirect('index')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('index')

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, 'User registered successfully')
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def registered_users_view(request):
    users = User.objects.all()
    return render(request, 'registered_users.html', {'users': users})

def classes_view(request):
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Class added successfully!')
            return redirect('classes')
        else:
            messages.error(request, 'Error adding class. Please check the form.')
    else:
        form = ClassForm()
    
    classes = Class.objects.all()
    return render(request, 'classes.html', {'classes': classes, 'form': form})

def class_detail_view(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)

    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.class_assigned = class_instance
            student.save()
            messages.success(request, 'Student added successfully!')
            return redirect('class_detail', class_id=class_id)
        else:
            messages.error(request, 'Error adding student. Please check the form.')
    else:
        form = StudentForm()

    students = class_instance.students.all()
    return render(request, 'class_detail.html', {'class': class_instance, 'students': students, 'form': form})


def exams_view(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exam added successfully!')
            return redirect('exams')
        else:
            messages.error(request, 'Error adding exam. Please check the form.')
    else:
        form = ExamForm()
    
    classes = Class.objects.all()
    exams = Exam.objects.all()
    return render(request, 'exams.html', {'classes': classes, 'exams': exams, 'form': form})

def exam_detail_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        correct_answer = request.POST.get('correct_answer')
        if question_text and correct_answer:
            Question.objects.create(exam=exam, question_text=question_text, correct_answer=correct_answer)
            messages.success(request, 'Question added successfully!')
            return redirect('exam_detail', exam_id=exam_id)
        else:
            messages.error(request, 'Error adding question. Please check the form.')
    else:
        form = QuestionForm()
    
    questions = exam.questions.all()
    return render(request, 'exam_detail.html', {'exam': exam, 'questions': questions, 'form': form})

def students_view(request):
    students = Student.objects.all()
    return render(request, 'students.html', {'students': students})

def add_student_view(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)
    
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            # Save the student and associate with the class
            student = form.save(commit=False)
            student.class_assigned = class_instance
            student.save()
            messages.success(request, 'Student added successfully!')
            return redirect('class_detail', class_id=class_instance.id)
        else:
            messages.error(request, 'Error adding student. Please check the form.')
    else:
        form = StudentForm()  # Create a new form instance for GET requests
    
    # If form submission fails or it's a GET request, redirect to class detail
    return redirect('class_detail', class_id=class_instance.id)

def add_exam_view(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exam added successfully!')
            return redirect('exams')
        else:
            messages.error(request, 'Error adding exam. Please check the form.')
    else:
        form = ExamForm()
    
    return render(request, 'add_exam.html', {'form': form})

def add_student_to_exam_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.exam = exam
            student.save()
            messages.success(request, 'Student added to exam successfully!')
            return redirect('exam_detail', exam_id=exam.id)
        else:
            messages.error(request, 'Error adding student to exam. Please check the form.')
    else:
        form = StudentForm()
    
    return render(request, 'add_student.html', {'form': form})

def add_class_view(request):
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('classes')  # Redirect to classes page after adding a class
    else:
        form = ClassForm()

    return render(request, 'add_class.html', {'form': form})

def settings_view(request):
    if request.method == 'POST':
        # Handle form submission and save settings
        # ...
        pass

    return render(request, 'settings.html')

@login_required
def settings_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')  # Use 'email' instead of 'username' for clarity
        password = request.POST.get('password')
        user = request.user

        if email:
            user.email = email
            user.username = email  # Ensure the username is also updated to the email
            if password:
                user.set_password(password)
            user.save()
            messages.success(request, 'Settings updated successfully!')
            return redirect('settings')
        else:
            messages.error(request, 'Email is required.')

    return render(request, 'settings.html')