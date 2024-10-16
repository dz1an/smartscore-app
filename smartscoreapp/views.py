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
from django.contrib.auth.forms import PasswordChangeForm, UserChangeForm
import random
import logging
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from io import BytesIO
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from .forms import StudentBulkUploadForm
import csv
from django.core.files.storage import FileSystemStorage
from datetime import datetime
import os
import string
from django.conf import settings
from django.http import HttpResponseForbidden
from django.db.models import Count

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
            form.save()  # Save the user without logging them in
            messages.success(request, 'User registered successfully! Please log in.')
            return redirect('login')  # Redirect to the login page
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
    
    # Handle form submission for adding a new class
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            new_class = form.save(commit=False)
            new_class.user = user_instance
            new_class.save()
            return redirect('classes')
    else:
        form = ClassForm()

    # Get sorting criteria from request, default is by name
    sort_by = request.GET.get('sort', 'name')

    # Fetch classes and annotate them with the number of students
    classes = Class.objects.filter(user=user_instance).annotate(num_students=Count('students'))

    # Sort classes based on the sorting criteria
    if sort_by == 'name':
        classes = classes.order_by('name')
    elif sort_by == 'description':
        classes = classes.order_by('description')
    elif sort_by == 'num_students':
        classes = classes.order_by('-num_students')

    context = {
        'classes': classes,
        'form': form,
        'student_form': StudentForm(),  # Add this line
        'sort_by': sort_by  # Pass sorting criteria to the template
    }
    return render(request, 'classes.html', context)


@login_required
def delete_class_view(request, class_id):
    try:
        # Fetch the class to be deleted and ensure it belongs to the current user
        class_instance = get_object_or_404(Class, id=class_id, user=request.user)

        # Fetch exams associated with the class
        exams = Exam.objects.filter(class_assigned=class_instance)

        # Optionally delete all associated exams before deleting the class
        exams.delete()  # Remove this line if you want to keep exams

        # Now delete the class
        class_instance.delete()

        # Success message after deletion
        messages.success(request, 'Class deleted successfully, and associated exams have been removed.')
        return redirect('classes')
    
    except IntegrityError as e:
        # Handle errors that could occur during deletion, such as related objects
        messages.error(request, f'Error occurred while deleting the class: {str(e)}')
        return redirect('classes')

    except Class.DoesNotExist:
        # Handle the case where the class does not exist
        messages.error(request, 'Class not found.')
        return redirect('classes')


@login_required
def class_detail_view(request, class_id):
    user_instance = request.user
    class_instance = get_object_or_404(Class, id=class_id)

    # Check if the logged-in user owns the class
    if class_instance.user != user_instance:
        raise PermissionDenied("You are not authorized to view this class.")

    # Order students by last name, first name, and middle initial
    students = Student.objects.filter(assigned_class=class_instance).order_by('last_name', 'first_name', 'middle_initial')

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
    
    # Handle POST request (when adding a new exam)
    if request.method == 'POST':
        form = ExamForm(request.POST, user=user_instance)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.save()

            # Creating 3 sets for each exam
            for i in range(3):
                ExamSet.objects.create(exam=exam, set_number=i + 1)
                
            messages.success(request, 'Exam and sets added successfully!')
            return redirect('exams')
        else:
            messages.error(request, 'There was an error adding the exam. Please check the form for errors.')
    else:
        form = ExamForm(user=user_instance)

    # Fetch exams and annotate with the number of questions
    exams = Exam.objects.filter(class_assigned__user=user_instance).annotate(num_questions=Count('questions'))
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
    students = Student.objects.filter(assigned_class=exam.class_assigned)

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
    
    # Fetch classes assigned to the logged-in user
    user_classes = Class.objects.filter(user=request.user)

    # Get selected class and exam from POST data
    selected_class_id = request.POST.get('class_source_id', current_class.id)
    selected_exam_id = request.POST.get('exam_source_id', None)

    # If a different class is selected, fetch exams from that class
    if selected_class_id:
        selected_class = get_object_or_404(Class, id=selected_class_id, user=request.user)
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
        count_added = selected_questions.count()  # Get the number of selected questions
        exam.questions.add(*selected_questions)  # Add selected questions to the current exam

        # Update the success message to include the count of added questions
        messages.success(request, f'Questions added successfully! {count_added} question(s) added to the exam.')
        return redirect('exam_detail', exam_id=exam_id)

    return render(request, 'select_questions.html', {
        'exam': exam,
        'current_class': current_class,
        'available_classes': user_classes,  # Only user-specific classes
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
def scan_page(request, class_id, exam_id):
    current_class = get_object_or_404(Class, id=class_id)
    current_exam = get_object_or_404(Exam, id=exam_id)
    
    # Fetch exams related to the current class
    exams = current_class.exams.all()  # Get all exams associated with this class
    
    if request.method == 'POST':
        # Handle the uploaded images
        uploaded_images = request.FILES.getlist('image_upload')
        
        # Add a message indicating how many images were uploaded
        if uploaded_images:
            messages.success(request, f"{len(uploaded_images)} image(s) uploaded successfully.")
        else:
            messages.warning(request, "No images were uploaded.")
    
    context = {
        'current_class': current_class,
        'current_exam': current_exam,
        'exams': exams
    }
    
    return render(request, 'scan_page.html', context)



def scan_exam_view(request):
    folder_path = None
    csv_file = None
    images = []
    
    if request.method == "POST":
        class_name = request.POST.get('class_name', 'Unknown_Class')
        
        # Create folder in base directory with class name and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{class_name}_{timestamp}"
        folder_path = os.path.join(settings.MEDIA_ROOT, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # Save CSV file into folder
        csv_file = request.FILES.get('exam_csv')
        if csv_file:
            fs = FileSystemStorage(location=folder_path)
            csv_filename = fs.save(csv_file.name, csv_file)
        
        # Save images into the folder
        images = request.FILES.getlist('images')
        for img in images:
            fs.save(img.name, img)

        # Handle scan and return results
        result_csv = process_scanned_images(folder_path, images)
        
        # Save the result CSV in the same folder
        with open(os.path.join(folder_path, 'scan_results.csv'), 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerows(result_csv)

        return redirect('scan_exam_view')
    
    return render(request, 'scan_exam.html', {
        'folder_path': folder_path,
        'csv_file': csv_file,
        'images': images,
    })

def process_scanned_images(folder_path, images):
    # Example function for processing images (replace with your actual logic)
    # Dummy processing returning a result in CSV format
    results = [['Student ID', 'Score']]
    for img in images:
        results.append([img.name, 80])  # Mock result
    return results


@login_required
def generate_exam_sets(request, class_id, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    current_class = get_object_or_404(Class, id=class_id)

    if request.method == "POST":
        students = current_class.students.all()
        exam_questions = exam.questions.all()

        if not exam_questions.exists():
            return JsonResponse({
                'success': False,
                'message': "No questions available for this exam."
            })

        # Initialize CSV writer for download
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="exam_sets_class_{current_class.id}_exam_{exam.id}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Lastname', 'Firstname', 'MiddleInitial', 'ID', 'Exam ID', 'Answer Key'])

        new_sets_generated = False
        generated_sets = []  # Create a local variable to store generated sets

        for student in students:
            if not TestSet.objects.filter(exam=exam, student=student).exists():
                set_no = random.randint(1, 100)
                while TestSet.objects.filter(exam=exam, set_no=set_no).exists():
                    set_no = random.randint(1, 100)

                test_set = TestSet.objects.create(exam=exam, student=student, set_no=set_no)
                randomized_questions = list(exam_questions)
                random.shuffle(randomized_questions)

                number_of_questions_to_select = min(len(randomized_questions), 10)  # Adjust as needed
                selected_questions = randomized_questions[:number_of_questions_to_select]
                answer_key = ''.join(str(['A', 'B', 'C', 'D', 'E'].index(question.answer)) for question in selected_questions)

                formatted_id = student.student_id[4:] if len(student.student_id) > 4 else student.student_id
                exam_unique_id = str(random.randint(10000, 99999))  # Ensure it’s a 5-digit ID
                middle_initial = student.middle_initial if student.middle_initial else ''

                writer.writerow([
                    student.last_name,
                    student.first_name,
                    middle_initial,
                    formatted_id,
                    exam_unique_id,
                    answer_key
                ])

                generated_sets.append({
                    'student_name': f"{student.first_name} {student.last_name}",
                    'set_no': set_no,
                    'set_id': test_set.id
                })  # Append to the local list
                new_sets_generated = True

        if not new_sets_generated:
            return JsonResponse({
                'success': False,
                'message': "No new sets were generated, as all students already have sets."
            })

        # Return the generated sets as JSON
        return JsonResponse({
            'success': True,
            'generated_sets': generated_sets
        })

    # Handle GET request and initial loading of generated sets
    generated_sets = TestSet.objects.filter(exam=exam, student__in=current_class.students.all())
    context = {
        'exam': exam,
        'current_class': current_class,
        'generated_sets': generated_sets,
    }

    return render(request, 'exams/generate_sets.html', context)


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
    current_class = exam.class_assigned

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
        'current_class': current_class,
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
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        middle_initial = request.POST.get('middle_initial', '')
        student_id = request.POST.get('student_id')

        # Allow adding the same student ID to different classes
        # Check if the student ID already exists in the same class
        if Student.objects.filter(student_id=student_id, assigned_class=class_instance).exists():
            messages.warning(request, f"Student with ID {student_id} already exists in this class.")
            return redirect('class_detail', class_id=class_id)

        try:
            # Create the new student record with assigned_class
            Student.objects.create(
                student_id=student_id,
                first_name=first_name,
                last_name=last_name,
                middle_initial=middle_initial,
                assigned_class=class_instance  # Ensure the class is assigned here
            )
            messages.success(request, f"Student {first_name} {last_name} added successfully!")
            return redirect('class_detail', class_id=class_id)
        except IntegrityError as e:
            messages.error(request, f"Error creating student with ID {student_id}. Error: {str(e)}")
            return redirect('class_detail', class_id=class_id)

    return render(request, 'add_student.html', {
        'class_instance': class_instance,
    })


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

            # Initialize a counter for successfully added students
            successful_additions = 0
            existing_student_ids = []  # To keep track of existing student IDs
            
            for row in reader:
                student_id = row.get('ID')  # Ensure this matches your CSV header
                first_name = row.get('First Name')
                last_name = row.get('Last Name')
                middle_initial = row.get('Middle Initial', '')

                # Check if the student already exists in the same class
                if Student.objects.filter(student_id=student_id, assigned_class=class_instance).exists():
                    existing_student_ids.append(student_id)
                    messages.warning(request, f"Student with ID {student_id} already exists in this class. Skipping.")
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
                    successful_additions += 1  # Increment the counter
                except IntegrityError as e:
                    messages.error(request, f"Error creating student with ID {student_id}. Error: {str(e)}")
                    continue  # Skip to next row on error
            
            # Success message for total added students
            if successful_additions > 0:
                messages.success(request, f'Student bulk upload completed successfully! {successful_additions} students added.')
            else:
                messages.info(request, 'No new students were added during the bulk upload.')
            
            # Info alert with the list of skipped students (if any)
            if existing_student_ids:
                skipped_ids = ', '.join(existing_student_ids)
                messages.info(request, f'Skipped {len(existing_student_ids)} existing student IDs: {skipped_ids}')
                
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
def delete_student_view(request, class_id, student_id):
    # Retrieve the class instance
    class_instance = get_object_or_404(Class, id=class_id)

    # Retrieve the student instance
    student = get_object_or_404(Student, student_id=student_id, assigned_class=class_instance)

    if request.method == 'POST':
        # Attempt to delete the student
        student.delete()
        messages.success(request, f"Student {student.first_name} {student.last_name} has been deleted successfully.")
        return redirect('class_detail', class_id=class_id)

    return render(request, 'delete_student.html', {
        'student': student,
        'class_instance': class_instance,
    })


def delete_student(request, student_id, class_id):
    # Fetch the class and ensure the student belongs to that class
    class_instance = get_object_or_404(Class, id=class_id, user=request.user)
    student_instance = get_object_or_404(Student, student_id=student_id, assigned_class=class_instance)

    if request.method == 'POST':
        # Delete the student
        student_instance.delete()
        messages.success(request, f'Student {student_instance.first_name} {student_instance.last_name} deleted successfully.')
        return redirect('class_detail', class_id=class_id)
    
    # If not POST, show a confirmation page (optional)
    return render(request, 'delete_student_confirm.html', {'student': student_instance, 'class': class_instance})





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
        password_form = PasswordChangeForm(request.user, request.POST)
        user_form = UserChangeForm(request.POST, instance=request.user)

        if password_form.is_valid() and user_form.is_valid():
            # Update user information
            user_form.save()

            # Update password
            user = password_form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your settings were successfully updated!')
            return redirect('settings')
        else:
            # Capture and display error messages
            if not password_form.is_valid():
                for field, errors in password_form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field.capitalize()}: {error}')
            if not user_form.is_valid():
                for field, errors in user_form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field.capitalize()}: {error}')
    else:
        password_form = PasswordChangeForm(request.user)
        user_form = UserChangeForm(instance=request.user)

    context = {
        'password_form': password_form,
        'user_form': user_form,
    }
    return render(request, 'settings.html', context)


@login_required
@require_http_methods(['POST'])
def ajax_get_students(request):
    class_id = request.POST.get('class_id')
    students = Student.objects.filter(assigned_class_id=class_id).values('id', 'first_name', 'last_name', 'student_id', 'short_id')
    data = list(students)
    return JsonResponse(data, safe=False)


@login_required
def delete_account_view(request):
    if request.method == 'POST':
        user = request.user
        user.delete()
        messages.success(request, "Your account has been deleted.")
        return redirect('index')