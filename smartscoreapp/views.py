from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Class, Student, Exam, Question
from .forms import ClassForm, StudentForm, ExamForm, ClassNameForm, EditStudentForm 
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from .forms import UserCreationWithEmailForm 
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest

User = get_user_model() 

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
            messages.success(request, 'User registered successfully!')
            return redirect('login')  # Redirect to the login page
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserCreationForm()
    
    return render(request, 'register.html', {'form': form})

def registered_users_view(request):
    users = User.objects.all()
    return render(request, 'registered_users.html', {'users': users})

@login_required
def classes_view(request):
    user_instance = request.user  # Get the logged-in User instance
    
    if request.method == 'POST':
        # Handle form submission to add a new class
        form = ClassNameForm(request.POST)
        if form.is_valid():
            new_class = form.save(commit=False)
            new_class.user = user_instance  # Associate the logged-in user with the class
            new_class.save()
            return redirect('classes')  # Redirect to the classes page after successful creation
    else:
        # Fetch classes associated with the logged-in user
        if user_instance.is_superuser:
            # For superuser, fetch all classes
            classes = Class.objects.all()
        else:
            # For regular users, fetch classes they manage (assuming user is the admin)
            classes = Class.objects.filter(user=user_instance)
    
    # Render your template with classes data and form
    context = {
        'classes': classes,
        'form': ClassNameForm()  # Assuming ClassNameForm is your form for adding a new class
    }
    return render(request, 'classes.html', context)



def delete_class_view(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)
    class_instance.delete()
    messages.success(request, 'Class deleted successfully!')
    return redirect('classes')

@login_required
def class_detail_view(request, class_id):
    user_instance = request.user  # Get the logged-in User instance

    # Fetch the class instance for the given class_id
    class_instance = get_object_or_404(Class, id=class_id)

    # Check if the logged-in user is authorized to view this class
    if class_instance.user != user_instance:
        # You may want to handle unauthorized access here, like redirecting or showing an error message
        raise PermissionDenied("You are not authorized to view this class.")

    # Fetch students enrolled in this class
    students = Student.objects.filter(assigned_class=class_instance)

    # Render your template with class details and enrolled students
    context = {
        'class': class_instance,
        'students': students,
    }
    return render(request, 'class_detail.html', context)


def update_class_name_view(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)

    if request.method == 'POST':
        form = ClassNameForm(request.POST, instance=class_instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Class name updated successfully!')
            return redirect('class_detail', class_id=class_instance.id)
        else:
            messages.error(request, 'Error updating class name. Please check the form.')
    else:
        form = ClassNameForm(instance=class_instance)

    context = {
        'class': class_instance,
        'form': form,
    }
    return render(request, 'class_detail.html', context)


@login_required
def exams_view(request):
    user_instance = request.user
    
    if request.method == 'POST':
        form = ExamForm(request.POST, user=user_instance)
        if form.is_valid():
            new_exam = form.save(commit=False)
            new_exam.save()
            messages.success(request, 'Exam added successfully.')
            return redirect('exams')
        else:
            messages.error(request, 'Failed to add exam. Please check the form for errors.')
    else:
        form = ExamForm(user=user_instance)

    classes = Class.objects.filter(user=user_instance)
    exams = Exam.objects.filter(class_assigned__user=user_instance)

    context = {
        'exams': exams,
        'classes': classes,
        'form': form,
    }
    return render(request, 'exams.html', context)

def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    exam.delete()
    messages.success(request, 'Exam deleted successfully.')
    return redirect('exams')

@login_required
def add_question_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        option_a = request.POST.get('option_a')
        option_b = request.POST.get('option_b')
        option_c = request.POST.get('option_c')
        option_d = request.POST.get('option_d')
        correct_answer = request.POST.get('correct_answer')

        if question_text and option_a and option_b and option_c and option_d and correct_answer:
            Question.objects.create(
                exam=exam,
                question_text=question_text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                correct_answer=correct_answer
            )
            messages.success(request, 'Question added successfully!')
        else:
            messages.error(request, 'All fields are required.')

        return redirect('exam_detail', exam_id=exam.id)
    
    return render(request, 'add_question.html', {'exam': exam})

@login_required
def edit_question_view(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        option_a = request.POST.get('option_a')
        option_b = request.POST.get('option_b')
        option_c = request.POST.get('option_c')
        option_d = request.POST.get('option_d')
        correct_answer = request.POST.get('correct_answer')

        if question_text and option_a and option_b and option_c and option_d and correct_answer:
            question.question_text = question_text
            question.option_a = option_a
            question.option_b = option_b
            question.option_c = option_c
            question.option_d = option_d
            question.correct_answer = correct_answer
            question.save()
            messages.success(request, 'Question updated successfully!')
        else:
            messages.error(request, 'All fields are required.')

        return redirect('exam_detail', exam_id=question.exam.id)

    return render(request, 'edit_question.html', {'question': question})


@login_required
def delete_question_view(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    exam_id = question.exam.id

    if request.method == 'POST':
        question.delete()
        messages.success(request, 'Question deleted successfully!')
        return redirect('exam_detail', exam_id=exam_id)

    return redirect('exam_detail', exam_id=exam_id)

@login_required
def add_exam_view(request):
    if request.method == 'POST':
        form = ExamForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('exams')
    else:
        form = ExamForm(user=request.user)
    user_classes = Class.objects.filter(user=request.user)
    return render(request, 'exams.html', {'form': form, 'classes': user_classes})

@login_required
def exam_detail_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    if request.method == "POST":
        question_text = request.POST.get('question_text')
        option_a = request.POST.get('option_a')
        option_b = request.POST.get('option_b')
        option_c = request.POST.get('option_c')
        option_d = request.POST.get('option_d')
        correct_answer = request.POST.get('correct_answer')

        if question_text:
            Question.objects.create(
                exam=exam,
                question_text=question_text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                correct_answer=correct_answer
            )
            messages.success(request, "Question added successfully!")
        else:
            messages.error(request, "Question text is required!")

    # Retrieve questions related to the exam
    questions = exam.question_set.all()

    return render(request, 'exam_detail.html', {'exam': exam, 'questions': questions})


def students_view(request):
    students = Student.objects.all()
    return render(request, 'students.html', {'students': students})

@login_required
def add_student_view(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)
    
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.assigned_class = class_instance
            student.save()
            messages.success(request, 'Student added successfully!')
            return redirect('class_detail', class_id=class_id)
        else:
            messages.error(request, 'Error adding student. Please check the form.')
    else:
        form = StudentForm()
    
    return render(request, 'add_student.html', {'form': form, 'class_instance': class_instance})


@login_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    
    if request.method == 'POST':
        student.name = request.POST.get('name')
        student.save()
        # Optionally add success message
        messages.success(request, 'Student updated successfully.')
        return redirect('class_detail', class_id=student.assigned_class.id)  # Redirect to appropriate page
    
    # Handle other HTTP methods or render form for GET request
    return render(request, 'edit_student.html', {'student': student})

def delete_student(request, student_id):
    student = get_object_or_404(Student, pk=student_id)

    if request.method == 'POST':
        assigned_class_id = student.assigned_class.id
        student.delete()
        messages.success(request, 'Student deleted successfully.')
        return redirect('class_detail', class_id=assigned_class_id)

    # Handle other HTTP methods if necessary

    return redirect('class_detail', class_id=student.assigned_class.id)

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
    
    # Return to the exam detail page if not a POST request or if form is not valid
    return redirect('exam_detail', exam_id=exam.id)

@login_required
def add_class_view(request):
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            new_class = form.save(commit=False)
            new_class.user = request.user  # Directly assign request.user
            new_class.save()
            messages.success(request, 'Class added successfully!')
            return redirect('classes')
        else:
            messages.error(request, 'Error adding class. Please check the form.')
    else:
        form = ClassForm()
    
    return render(request, 'classes.html', {'form': form})

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

@login_required
@require_http_methods(['POST'])
def ajax_get_students(request):
    class_id = request.POST.get('class_id')
    students = Student.objects.filter(assigned_class_id=class_id).values('id', 'name')
    data = list(students)
    return JsonResponse(data, safe=False)
