from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Class, Student, Exam, Question, Answer, ExamSet
from .forms import ClassForm, StudentForm, ExamForm, ClassNameForm, EditStudentForm 
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from .forms import UserCreationWithEmailForm 
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from random import shuffle
import random
from .forms import StudentForm, AddStudentToExamForm, TestSetForm
from django.utils.crypto import get_random_string
from django.db import models
from .models import Student


User = get_user_model() 

def index(request):
    return render(request, 'index.html')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            # Try to authenticate using the custom backend
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Login successful!")
                # Print the backend used
                print(f"Backend used: {user.backend}")
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
        option_e = request.POST.get('option_e')
        correct_answer = request.POST.get('correct_answer')

        if question_text and option_a and option_b and correct_answer:
            # Create the Question object
            question = Question.objects.create(
                exam=exam,
                question_text=question_text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                option_e=option_e
            )
            
            # Create the associated Answer object
            Answer.objects.create(
                question=question,
                correct_answer=correct_answer
            )
            
            messages.success(request, 'Question and answer added successfully!')
        else:
            messages.error(request, 'Question text, Option A, Option B, and Correct Answer are required.')

        return redirect('exam_detail', exam_id=exam.id)
    
    return render(request, 'add_question.html', {'exam': exam})

@login_required
def create_exam_set(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if request.method == 'POST':
        set_number = request.POST.get('set_number')
        student_ids = request.POST.getlist('students')
        
        exam_set = ExamSet.objects.create(exam=exam, set_number=set_number)
        students = Student.objects.filter(student_id__in=student_ids)
        exam_set.students.add(*students)
        
        messages.success(request, f'Exam Set {set_number} created and assigned to students.')
        return redirect('exam_detail', exam_id=exam.id)
    
    students = Student.objects.filter(assigned_class=exam.class_assigned)
    return render(request, 'create_exam_set.html', {'exam': exam, 'students': students})


@login_required
def edit_question_view(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    answer = question.answer  # Get the associated answer

    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        option_a = request.POST.get('option_a')
        option_b = request.POST.get('option_b')
        option_c = request.POST.get('option_c')
        option_d = request.POST.get('option_d')
        option_e = request.POST.get('option_e')
        correct_answer = request.POST.get('correct_answer')

        if question_text and option_a and option_b and correct_answer:
            # Update question
            question.question_text = question_text
            question.option_a = option_a
            question.option_b = option_b
            question.option_c = option_c
            question.option_d = option_d
            question.option_e = option_e
            question.save()

            # Update answer
            answer.correct_answer = correct_answer
            answer.save()

            messages.success(request, 'Question and answer updated successfully!')
            return redirect('exam_detail', exam_id=question.exam.id)
        else:
            messages.error(request, 'Question text, Option A, Option B, and Correct Answer are required.')
    
    return render(request, 'edit_question.html', {'question': question, 'answer': answer})

@login_required
def delete_question_view(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    exam_id = question.exam.id

    if request.method == 'POST':
        # The associated answer will be automatically deleted due to the OneToOneField with on_delete=models.CASCADE
        question.delete()
        messages.success(request, 'Question and answer deleted successfully!')
        return redirect('exam_detail', exam_id=exam_id)

    return redirect('exam_detail', exam_id=exam_id)

@login_required
def select_questions_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    questions = Question.objects.all()

    if request.method == 'POST':
        selected_question_ids = request.POST.getlist('questions')
        selected_questions = Question.objects.filter(id__in=selected_question_ids)
        
        # Clear existing questions and add selected questions
        exam.questions.clear()
        exam.questions.add(*selected_questions)

        messages.success(request, 'Questions selected successfully!')
        return redirect('generate_test_paper', exam_id=exam_id)

    return render(request, 'select_questions.html', {'exam': exam, 'questions': questions})

@login_required
def print_test_paper_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    selected_questions = list(exam.questions.all())
    random.shuffle(selected_questions)  # Randomize questions for each student

    return render(request, 'print_test_paper.html', {'exam': exam, 'selected_questions': selected_questions})

@login_required
def generate_test_paper_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    selected_questions = list(exam.questions.all())
    random.shuffle(selected_questions)  # Randomize questions for each student

    # Prepare a list of questions with options for rendering
    questions_with_options = [{'question_text': question.question_text,
                               'options': [question.option_a, question.option_b, question.option_c, question.option_d, question.option_e]}
                              for question in selected_questions]

    return render(request, 'generate_test_paper.html', {'exam': exam, 'questions_with_options': questions_with_options})

@login_required
def process_scanned_papers_view(request):
    if request.method == 'POST':
        exam_id = request.POST.get('exam_id')
        exam = get_object_or_404(Exam, id=exam_id)
        questions = list(exam.questions.all())
        total_questions = len(questions)
        
        # Process scanned answers
        marks = []
        for question in questions:
            answer_key = f'question{question.id}'  # Adjust as per your form structure
            marked_option = request.POST.get(answer_key)
            correct_option = question.correct_answer  # Adjust based on your model design

            if marked_option is not None:
                marks.append(1 if int(marked_option) == correct_option else 0)
            else:
                marks.append(0)  # Handle case where no option is marked (if needed)

        # Calculate score and other relevant metrics
        score = sum(marks)
        total_marks = len(marks)

        # Optionally, save the scanned papers or marks for further processing
        # Ensure your file paths and processing align with your requirements

        messages.success(request, f"Exam submitted successfully. Score: {score}/{total_marks}")
        return redirect('exams')  # Redirect to exams page after processing

    return redirect('exams')  # Redirect to exams page if not a POST request or processing fails


def generate_answers_list(exam):
    selected_questions = exam.questions.all()
    answers = []
    for question in selected_questions:
        if question.correct_answer == 'A':
            answers.append(question.option_a_value)
        elif question.correct_answer == 'B':
            answers.append(question.option_b_value)
        elif question.correct_answer == 'C':
            answers.append(question.option_c_value)
        elif question.correct_answer == 'D':
            answers.append(question.option_d_value)
        elif question.correct_answer == 'E':
            answers.append(question.option_e_value)
    return answers


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
        option_e = request.POST.get('option_e')
        correct_answer = request.POST.get('correct_answer')

        if question_text:
            Question.objects.create(
                exam=exam,
                question_text=question_text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                option_e=option_e,
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
    
    return render(request, 'add_student.html', {'form': form})


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


@login_required
def add_student_to_exam_view(request, exam_id):
    exam_instance = get_object_or_404(Exam, id=exam_id)
    
    if request.method == 'POST':
        student_form = AddStudentToExamForm(request.POST)
        test_set_form = TestSetForm(request.POST)
        
        if student_form.is_valid() and test_set_form.is_valid():
            student = student_form.save()
            test_set = test_set_form.save(commit=False)
            test_set.exam = exam_instance
            test_set.student = student
            test_set.save()
            messages.success(request, 'Student and exam set added successfully!')
            return redirect('exam_detail', exam_id=exam_id)
        else:
            messages.error(request, 'Error adding student and exam set. Please check the form.')
    else:
        student_form = AddStudentToExamForm()
        test_set_form = TestSetForm()
    
    return render(request, 'add_student_to_exam.html', {'student_form': student_form, 'test_set_form': test_set_form})

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

@login_required
def settings_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('settings')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field.capitalize()}: {error}')
            return redirect('settings')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'settings.html', {'form': form})

@login_required
@require_http_methods(['POST'])
def ajax_get_students(request):
    class_id = request.POST.get('class_id')
    students = Student.objects.filter(assigned_class_id=class_id).values('id', 'name')
    data = list(students)
    return JsonResponse(data, safe=False)
