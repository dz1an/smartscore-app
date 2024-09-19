from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from .models import Class, Student, Exam, Question, Answer, ExamSet, StudentQuestion
from .forms import ClassForm, StudentForm, ExamForm, ClassNameForm, EditStudentForm, UserCreationWithEmailForm, AddStudentToExamForm, TestSetForm, TestSet
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
import random
import logging
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from io import BytesIO
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from .forms import StudentBulkUploadForm
import csv

User = get_user_model()
logger = logging.getLogger(__name__)


def generate_student_code(exam_id):
    set_identifier = random.randint(0, 99)
    id_part = exam_id % 10000
    return f"{set_identifier:02d}-{id_part:04d}"

def index(request):
    return render(request, 'index.html')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
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
        form = UserCreationWithEmailForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, 'User registered successfully!')
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserCreationWithEmailForm()
    
    return render(request, 'register.html', {'form': form})

def registered_users_view(request):
    users = User.objects.all()
    return render(request, 'registered_users.html', {'users': users})

@login_required
def classes_view(request):
    user_instance = request.user
    
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            new_class = form.save(commit=False)
            new_class.user = user_instance
            new_class.save()
            return redirect('classes')
    else:
        form = ClassForm()
    
    classes = Class.objects.filter(user=user_instance)
    
    context = {
        'classes': classes,
        'form': form,
        'student_form': StudentForm()  # Add this line
    }
    return render(request, 'classes.html', context)

@login_required
def delete_class_view(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)
    if class_instance.user == request.user:
        class_instance.delete()
        messages.success(request, 'Class deleted successfully!')
    else:
        messages.error(request, 'You are not authorized to delete this class.')
    return redirect('classes')

@login_required
def class_detail_view(request, class_id):
    user_instance = request.user
    class_instance = get_object_or_404(Class, id=class_id)

    if class_instance.user != user_instance:
        raise PermissionDenied("You are not authorized to view this class.")

    students = Student.objects.filter(assigned_class=class_instance)

    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.assigned_class = class_instance
            try:
                student.save()
                messages.success(request, 'Student added successfully!')
                return redirect('class_detail', class_id=class_id)
            except Exception as e:
                messages.error(request, f"Error saving student: {e}")
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentForm()

    context = {
        'class': class_instance,
        'students': students,
        'form': form,
    }
    return render(request, 'class_detail.html', context)

@login_required
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
            exam = form.save(commit=False)
            exam.save()
            for i in range(3):  # Creating 3 sets for each exam
                ExamSet.objects.create(exam=exam, set_number=i + 1)
            messages.success(request, 'Exam and sets added successfully!')
            return redirect('exams')
        else:
            messages.error(request, 'There was an error adding the exam. Please check the form for errors.')
    else:
        form = ExamForm(user=user_instance)

    exams = Exam.objects.filter(class_assigned__user=user_instance)
    classes = Class.objects.filter(user=user_instance)

    context = {
        'exams': exams,
        'form': form,
        'classes': classes,
    }
    return render(request, 'exams.html', context)

@login_required
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if exam.class_assigned.user == request.user:
        exam.delete()
        messages.success(request, 'Exam deleted successfully.')
    else:
        messages.error(request, 'You are not authorized to delete this exam.')
    return redirect('exams')

@login_required
def add_question_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    available_exams = Exam.objects.exclude(id=exam_id)  # List of other exams
    
    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        option_a = request.POST.get('option_a')
        option_b = request.POST.get('option_b')
        option_c = request.POST.get('option_c')
        option_d = request.POST.get('option_d')
        option_e = request.POST.get('option_e')
        answer = request.POST.get('answer')
        
        selected_question_ids = request.POST.getlist('selected_questions')  # Fetch selected questions

        # Add manually entered question
        if question_text and option_a and option_b and answer:
            question = Question.objects.create(
                question_text=question_text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                option_e=option_e,
                answer=answer
            )
            exam.questions.add(question)  # Add the newly created question to the current exam
            messages.success(request, 'New question added successfully!')

        # Add selected questions from other exams
        if selected_question_ids:
            selected_questions = Question.objects.filter(id__in=selected_question_ids)
            exam.questions.add(*selected_questions)  # Add selected questions from other exams
            messages.success(request, 'Selected questions added successfully!')

        return redirect('exam_detail', exam_id=exam.id)

    return render(request, 'add_question.html', {
        'exam': exam,
        'available_exams': available_exams,
        'questions': []  # Initially no questions shown from other exams
    })


@login_required
def create_exam_set(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if request.method == 'POST':
        form = TestSetForm(request.POST)
        if form.is_valid():
            test_set = form.save(commit=False)
            test_set.exam = exam
            test_set.save()
            messages.success(request, f'Exam Set {test_set.set_no} created for {test_set.student}.')
            return redirect('exam_detail', exam_id=exam.id)
    else:
        form = TestSetForm()
    
    students = Student.objects.filter(assigned_class=exam.class_assigned)
    return render(request, 'create_exam_set.html', {'exam': exam, 'students': students, 'form': form})


@login_required
def edit_question_view(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        option_a = request.POST.get('option_a')
        option_b = request.POST.get('option_b')
        option_c = request.POST.get('option_c')
        option_d = request.POST.get('option_d')
        option_e = request.POST.get('option_e')
        correct_answer = request.POST.get('answer')

        if question_text and option_a and option_b and correct_answer:
            # Update question
            question.question_text = question_text
            question.option_a = option_a
            question.option_b = option_b
            question.option_c = option_c
            question.option_d = option_d
            question.option_e = option_e
            question.answer = correct_answer
            question.save()

            messages.success(request, 'Question and answer updated successfully!')
            return redirect('exam_detail', exam_id=question.exams.first().id)  # Get the first exam this question belongs to
        else:
            messages.error(request, 'Question text, Option A, Option B, and Correct Answer are required.')
    
    return render(request, 'edit_question.html', {'question': question})


@login_required
def delete_question_view(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    
    # Retrieve the first exam associated with the question (or modify this based on your logic)
    exam = question.exams.first()

    if not exam:
        messages.error(request, 'No exam is associated with this question.')
        return redirect('exams')  # Redirect to exams list if no exam is found

    exam_id = exam.id  # Get the associated exam's ID

    if request.method == 'POST':
        question.delete()  # Delete the question from the database
        messages.success(request, 'Question and answer deleted successfully!')
        return redirect('exam_detail', exam_id=exam_id)

    return redirect('exam_detail', exam_id=exam_id)


@login_required
def assign_questions_to_student(request, student_id, exam_id):
    student = get_object_or_404(Student, id=student_id)
    exam = get_object_or_404(Exam, id=exam_id)
    questions = exam.questions.all()

    for question in questions:
        StudentQuestion.objects.get_or_create(student=student, question=question, exam=exam)

    messages.success(request, f'Questions assigned to {student.name} for {exam.name}')
    return redirect('some_appropriate_url')

@login_required
def select_questions_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    current_class = exam.class_assigned
    selected_class_id = request.POST.get('class_source_id', current_class.id)
    selected_exam_id = request.POST.get('exam_source_id', None)

    # If a different class is selected, fetch exams from that class
    if selected_class_id:
        selected_class = get_object_or_404(Class, id=selected_class_id)
        available_exams = Exam.objects.filter(class_assigned=selected_class).exclude(id=exam_id)
    else:
        available_exams = None

    # If an exam is selected, fetch its questions
    if selected_exam_id:
        selected_exam = get_object_or_404(Exam, id=selected_exam_id)
        questions = selected_exam.questions.all()
    else:
        questions = []

    if request.method == 'POST' and 'questions' in request.POST:
        selected_question_ids = request.POST.getlist('questions')
        selected_questions = Question.objects.filter(id__in=selected_question_ids)
        exam.questions.add(*selected_questions)  # Add selected questions to the current exam
        messages.success(request, 'Questions added successfully!')
        return redirect('exam_detail', exam_id=exam_id)

    return render(request, 'select_questions.html', {
        'exam': exam,
        'current_class': current_class,
        'available_classes': Class.objects.exclude(id=current_class.id),  # Exclude current class
        'available_exams': available_exams,
        'questions': questions,
        'selected_class_id': int(selected_class_id),
        'selected_exam_id': int(selected_exam_id) if selected_exam_id else None,
    })




@login_required
def print_test_paper_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    selected_questions = list(exam.questions.all())
    random.shuffle(selected_questions)

    return render(request, 'print_test_paper.html', {'exam': exam, 'selected_questions': selected_questions})


@login_required
def save_test_paper_view(request, exam_id):
    if request.method == 'POST':
        exam = get_object_or_404(Exam, id=exam_id)
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, id=student_id)

        # Create a TestSet for the student and the exam
        test_set = TestSet.objects.create(exam=exam, student=student, set_no=random.randint(1, 100))

        # Optional: save questions and answers here if needed

        messages.success(request, f'Test paper for {exam.name} saved for student {student.first_name} {student.last_name}!')
        return redirect('exam_detail', exam_id=exam.id)
    else:
        messages.error(request, 'Invalid request method.')
        return redirect('exams')

@login_required
def generate_test_paper_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    selected_questions = list(exam.questions.all())
    random.shuffle(selected_questions)

    # Prepare a list of questions with options for rendering
    questions_with_options = [{'question_text': question.question_text,
                               'options': [question.option_a, question.option_b, question.option_c, question.option_d, question.option_e]}
                              for question in selected_questions]

    students = Student.objects.filter(assigned_class=exam.class_assigned)

    return render(request, 'generate_test_paper.html', {'exam': exam, 'questions_with_options': questions_with_options, 'students': students})


@login_required
def process_scanned_papers_view(request):
    if request.method == 'POST':
        exam_id = request.POST.get('exam_id')
        exam = get_object_or_404(Exam, id=exam_id)
        questions = list(exam.questions.all())
        total_questions = len(questions)
        
        marks = []
        for question in questions:
            answer_key = f'question{question.id}'
            marked_option = request.POST.get(answer_key)
            correct_option = question.answer

            if marked_option is not None:
                marks.append(1 if int(marked_option) == correct_option else 0)
            else:
                marks.append(0)

        score = sum(marks)
        total_marks = len(marks)

        messages.success(request, f"Exam submitted successfully. Score: {score}/{total_marks}")
        return redirect('exams')

    return redirect('exams')


def generate_answers_list(exam):
    selected_questions = exam.questions.all()
    answers = []
    for question in selected_questions:
        if question.answer == 'A':
            answers.append(question.option_a_value)
        elif question.answer == 'B':
            answers.append(question.option_b_value)
        elif question.answer == 'C':
            answers.append(question.option_c_value)
        elif question.answer == 'D':
            answers.append(question.option_d_value)
        elif question.answer == 'E':
            answers.append(question.option_e_value)
    return answers


@login_required
def generate_questionnaire_view(request, exam_id, student_id):
    exam = get_object_or_404(Exam, id=exam_id)
    student = get_object_or_404(Student, id=student_id)
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, f"Exam: {exam.name}")
    p.drawString(100, 780, f"Student: {student.first_name} {student.last_name}")
    p.drawString(100, 760, f"Set ID: {exam.set_id}")
    
    y = 740
    for question in exam.questions.all():
        p.drawString(100, y, f"{question.id}. {question.question_text}")
        y -= 20
        for option in [question.option_a, question.option_b, question.option_c, question.option_d, question.option_e]:
            p.drawString(120, y, option)
            y -= 20
        y -= 10
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')


@login_required
def list_classes_view(request):
    classes = Class.objects.filter(user=request.user)
    return render(request, 'list_classes.html', {'classes': classes})

@login_required
def class_exams_view(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)
    exams = class_instance.exams.all()
    return render(request, 'class_exams.html', {'class_instance': class_instance, 'exams': exams})

@login_required
def add_exam_view(request):
    if request.method == 'POST':
        form = ExamForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Exam added successfully!')
                return redirect('exams')
            except IntegrityError as e:
                form.add_error('exam_id', 'Exam ID must be unique.')
                messages.error(request, 'There was an error adding the exam. Please check the form for errors.')
        else:
            messages.error(request, 'There was an error adding the exam. Please check the form for errors.')
    else:
        form = ExamForm(user=request.user)

    user_classes = Class.objects.filter(user=request.user)
    # Debug print
    print(f"Classes: {user_classes}")
    context = {'form': form, 'classes': user_classes}
    return render(request, 'exams.html', context)

@login_required
def exam_detail_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    available_exams = Exam.objects.exclude(id=exam_id)  # Other exams to copy questions from
    questions = exam.questions.all()  # Questions already added to the current exam

    if request.method == 'POST':
        # Get the selected exam ID to copy questions from
        selected_exam_id = request.POST.get('exam_source_id')
        if selected_exam_id:
            source_exam = get_object_or_404(Exam, id=selected_exam_id)
            selected_question_ids = request.POST.getlist('questions')  # Get the selected questions

            if selected_question_ids:
                selected_questions = Question.objects.filter(id__in=selected_question_ids)
                exam.questions.add(*selected_questions)  # Add selected questions to the current exam
                messages.success(request, 'Selected questions copied successfully!')
            else:
                messages.error(request, 'No questions selected to copy!')

        # If manually adding a new question
        else:
            question_text = request.POST.get('question_text')
            option_a = request.POST.get('option_a')
            option_b = request.POST.get('option_b')
            option_c = request.POST.get('option_c')
            option_d = request.POST.get('option_d')
            option_e = request.POST.get('option_e')
            answer = request.POST.get('answer')

            if question_text and option_a and option_b and answer:
                question = Question.objects.create(
                    question_text=question_text,
                    option_a=option_a,
                    option_b=option_b,
                    option_c=option_c,
                    option_d=option_d,
                    option_e=option_e,
                    answer=answer
                )
                exam.questions.add(question)  # Add the newly created question to the exam
                messages.success(request, 'New question added successfully!')
            else:
                messages.error(request, 'Question text, Option A, Option B, and Correct Answer are required!')

    # Refetch the questions after copying/adding
    questions = exam.questions.all()

    return render(request, 'exam_detail.html', {
        'exam': exam,
        'questions': questions,
        'available_exams': available_exams
    })


@login_required
def grade_exam_view(request, exam_id, student_id):
    try:
        exam = Exam.objects.get(id=exam_id)
        student = Student.objects.get(id=student_id)
        student_questions = StudentQuestion.objects.filter(exam=exam, student=student)

        if request.method == 'POST':
            for student_question in student_questions:
                marks_field = f'marks_{student_question.id}'
                marks = request.POST.get(marks_field, 0)
                # Auto-grading logic
                if student_question.student_answer == student_question.question.answer:
                    student_question.marks = 1  # Assign 1 mark for correct answers, you can adjust the value
                else:
                    student_question.marks = 0  # Assign 0 mark for incorrect answers, you can adjust the value
                # Allow manual adjustment
                if marks:
                    student_question.marks = int(marks)
                student_question.save()

            messages.success(request, "Grades saved successfully!")
            return redirect('grade_exam', exam_id=exam.id, student_id=student.id)

        return render(request, 'exams/grade_exam.html', {
            'exam': exam,
            'student': student,
            'student_questions': student_questions
        })
    except Exam.DoesNotExist:
        messages.error(request, "Exam not found.")
        return redirect('exams')
    except Student.DoesNotExist:
        messages.error(request, "Student not found.")
        return redirect('exams')
    except Exception as e:
        messages.error(request, f"Error: {e}")
        return redirect('exams')

def students_view(request):
    students = Student.objects.all()
    return render(request, 'students.html', {'students': students})

@login_required
def add_student_view(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)

    if request.method == 'POST':
        form = StudentForm(request.POST, assigned_class=class_instance)
        if form.is_valid():
            student = form.save(commit=False)  # Don't save to the database yet
            student.assigned_class = class_instance  # Assign the class
            try:
                student.save()  # Now save the student with the assigned class
                messages.success(request, f'Student added successfully! Student ID: {student.student_id}')
                return redirect('class_detail', class_id=class_id)
            except Exception as e:
                messages.error(request, f"Error saving student: {e}")
        else:
            messages.error(request, 'Please correct the errors below.')
    
    form = StudentForm(assigned_class=class_instance)
    return render(request, 'add_student.html', {'form': form, 'class': class_instance})

@login_required
def bulk_upload_students_view(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)

    if request.method == 'POST':
        form = StudentBulkUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # Read the uploaded CSV file
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            for row in reader:
                student_id = row.get('student_id')
                first_name = row.get('first_name')
                last_name = row.get('last_name')
                middle_initial = row.get('middle_initial', '')
                
                # Check if the student ID already exists
                if Student.objects.filter(student_id=student_id).exists():
                    # You can choose to update existing students instead of skipping them
                    messages.warning(request, f"Student with ID {student_id} already exists. Skipping.")
                    continue  # Skip this student and move to the next one
                
                # Create the new student record
                try:
                    Student.objects.create(
                        student_id=student_id,
                        first_name=first_name,
                        last_name=last_name,
                        middle_initial=middle_initial,
                        assigned_class=class_instance
                    )
                except IntegrityError:
                    messages.error(request, f"Error creating student with ID {student_id}. Skipping.")
            
            messages.success(request, 'Student bulk upload completed successfully!')
            return redirect('class_detail', class_id=class_id)
    
    else:
        form = StudentBulkUploadForm()

    return render(request, 'bulk_upload_students.html', {
        'form': form,
        'class_instance': class_instance,
    })

@login_required
@require_POST
def edit_student(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    form = EditStudentForm(request.POST, instance=student)
    if form.is_valid():
        form.save()
        messages.success(request, 'Student updated successfully!')
    else:
        messages.error(request, 'There was an error updating the student.')
    return redirect('class_detail', class_id=student.assigned_class.id)



@login_required
@require_POST
def delete_student(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    assigned_class_id = student.assigned_class.id
    student.delete()
    messages.success(request, 'Student deleted successfully.')
    return redirect('class_detail', class_id=assigned_class_id)


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
def student_test_papers_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    test_sets = TestSet.objects.filter(student=student)  # Correct the query here

    return render(request, 'student_test_papers.html', {'student': student, 'test_sets': test_sets})


@login_required
def view_test_set_view(request, test_set_id):
    test_set = get_object_or_404(TestSet, id=test_set_id)
    return render(request, 'view_test_set.html', {'test_set': test_set})


@login_required
def add_class_view(request):
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            new_class = form.save(commit=False)
            new_class.user = request.user
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
    students = Student.objects.filter(assigned_class_id=class_id).values('id', 'first_name', 'last_name', 'student_id', 'short_id')
    data = list(students)
    return JsonResponse(data, safe=False)
