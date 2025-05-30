# Django core imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import IntegrityError
from django.db.models import Count
from django.http import (
    HttpResponse, 
    JsonResponse, 
    HttpResponseForbidden, 
    HttpResponseNotAllowed,
    FileResponse,
    
)
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

# Django authentication
from django.contrib.auth import (
    authenticate, 
    login, 
    logout, 
    get_user_model,
    update_session_auth_hash
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (
    UserCreationForm, 
    AuthenticationForm,
    PasswordChangeForm, 
    UserChangeForm,
    
)

# Local imports
from .models import (
    Class, 
    Student, 
    Exam, 
    Question, 
    Answer, 
    ExamSet, 
    StudentQuestion
)
from .forms import (
    ClassForm,
    StudentForm,
    ExamForm,
    ClassNameForm,
    EditStudentForm,
    UserCreationWithEmailForm,
    AddStudentToExamForm,
    TestSetForm,
    TestSet,
    StudentBulkUploadForm
)

# PDF generation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import legal
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak
)
from reportlab.lib.units import inch

# Standard library imports
import csv
import json
import logging
import os
import random
import re
import shutil
import string
import textwrap
from datetime import datetime
from io import BytesIO

# Third party imports
from background_task import background
import xlsxwriter
from omr2 import omr


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
            # Validate username format
            username = form.cleaned_data.get('username')
            if not all(c.isalnum() or c == '.' for c in username):
                messages.error(request, "Username can only contain letters, numbers, and periods.")
                return render(request, 'register.html', {'form': form})
                
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

        # Fetch or create the 'Unassigned Class' for the current user
        unassigned_class, created = Class.objects.get_or_create(
            name='Unassigned Class', 
            user=request.user,  # Ensure it's tied to the same user
            defaults={'description': 'This class is used to store reassigned exams.'}  # Optional description
        )

        # Reassign all exams from the class being deleted to the 'Unassigned Class'
        Exam.objects.filter(class_assigned=class_instance).update(class_assigned=unassigned_class)

        # Now delete the class
        class_instance.delete()

        # Success message after deletion
        messages.success(request, 'Class deleted successfully, and exams have been moved to the "Unassigned Class".')
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

    # Get the sort parameter from the request
    sort_by = request.GET.get('sort_by', 'last_name')

    # Order students based on the sort parameter and filter out those without an assigned class
    students = Student.objects.filter(assigned_class=class_instance).exclude(assigned_class=None)

    if sort_by == 'first_name':
        students = students.order_by('first_name', 'last_name')
    elif sort_by == 'most_recent':
        students = students.order_by('-id')
    else:
        students = students.order_by('last_name', 'first_name')

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
        'sort_by': sort_by,
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

    # Fetch exams, annotate with number of questions, and order by name
    exams = Exam.objects.filter(class_assigned__user=user_instance)\
        .annotate(num_questions=Count('questions'))\
        .order_by('name')  # Add this line to sort alphabetically
    
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
    available_exams = Exam.objects.exclude(id=exam_id)

    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        option_a = request.POST.get('option_a')
        option_b = request.POST.get('option_b')
        option_c = request.POST.get('option_c')
        option_d = request.POST.get('option_d')
        option_e = request.POST.get('option_e', '')
        correct_answer = request.POST.get('correct_answer')
        difficulty = request.POST.get('difficulty')  # Ensure difficulty is captured
        selected_question_ids = request.POST.getlist('selected_questions')

        if question_text and option_a and option_b and correct_answer and difficulty:
            # Create new question
            question = Question.objects.create(
                question_text=question_text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                option_e=option_e,
                answer=correct_answer,
                difficulty=difficulty  # Save difficulty level
            )
            exam.questions.add(question)
            messages.success(request, 'New question added successfully!')

        # Add selected questions from other exams
        if selected_question_ids:
            selected_questions = Question.objects.filter(id__in=selected_question_ids)
            exam.questions.add(*selected_questions)
            messages.success(request, 'Selected questions added successfully!')

        return redirect('exam_detail', exam_id=exam.id)

    return render(request, 'add_question.html', {
        'exam': exam,
        'available_exams': available_exams,
        'questions': [],
    })

    exam = get_object_or_404(Exam, id=exam_id)
    available_exams = Exam.objects.exclude(id=exam_id)

    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        option_a = request.POST.get('option_a')
        option_b = request.POST.get('option_b')
        option_c = request.POST.get('option_c')
        option_d = request.POST.get('option_d')
        option_e = request.POST.get('option_e', '')
        correct_answer = request.POST.get('correct_answer')
        difficulty = request.POST.get('difficulty')  # Ensure difficulty is captured
        selected_question_ids = request.POST.getlist('selected_questions')

        if question_text and option_a and option_b and correct_answer and difficulty:
            # Create new question
            question = Question.objects.create(
                question_text=question_text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                option_e=option_e,
                answer=correct_answer,
                difficulty=difficulty  # Save difficulty level
            )
            exam.questions.add(question)
            messages.success(request, 'New question added successfully!')

        # Add selected questions from other exams
        if selected_question_ids:
            selected_questions = Question.objects.filter(id__in=selected_question_ids)
            exam.questions.add(*selected_questions)
            messages.success(request, 'Selected questions added successfully!')

        return redirect('exam_detail', exam_id=exam.id)

    return render(request, 'add_question.html', {
        'exam': exam,
        'available_exams': available_exams,
        'questions': [],
    })


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
        selected_answer = request.POST.get('correct_answer')  # This should match with what is expected in the question model
        difficulty = request.POST.get('difficulty')  # Fetch the selected difficulty

        if question_text and option_a and option_b and selected_answer:
            # Update question attributes
            question.question_text = question_text
            question.option_a = option_a
            question.option_b = option_b
            question.option_c = option_c
            question.option_d = option_d
            question.option_e = option_e
            question.difficulty = difficulty  # Update difficulty level
            question.answer = selected_answer  # Update the correct answer
            question.save()

            messages.success(request, 'Question updated successfully!')
            return redirect('exam_detail', exam_id=question.exams.first().id)  # Redirect to the related exam detail
        
        else:
            messages.error(request, 'All fields are required.')
    
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
    
    # Fetch classes assigned to the logged-in user, EXCLUDING the current class
    user_classes = Class.objects.filter(user=request.user).exclude(id=current_class.id)

    # Initialize variables
    selected_class_id = current_class.id
    selected_exam_id = None
    questions = []

    # Get selected class and exam from POST data
    if request.method == 'POST':
        selected_class_id = request.POST.get('class_source_id', current_class.id)
        selected_exam_id = request.POST.get('exam_source_id', None)

        # If an exam is selected, fetch its questions
        if selected_exam_id:
            selected_exam = get_object_or_404(Exam, id=selected_exam_id)
            questions = selected_exam.questions.all()
        
        # Handle adding questions to the current exam
        if 'questions' in request.POST:
            selected_question_ids = request.POST.getlist('questions')
            selected_questions = Question.objects.filter(id__in=selected_question_ids)
            count_added = selected_questions.count()
            
            if count_added > 0:
                exam.questions.add(*selected_questions)
                messages.success(request, f'Questions added successfully! {count_added} question(s) added to the exam.')
            else:
                messages.warning(request, 'No questions selected to add.')
            return redirect('exam_detail', exam_id=exam_id)
    
    # Always fetch available exams for the selected class
    selected_class = get_object_or_404(Class, id=selected_class_id, user=request.user)
    available_exams = Exam.objects.filter(class_assigned=selected_class).exclude(id=exam_id)
    
    return render(request, 'select_questions.html', {
        'exam': exam,
        'current_class': current_class,
        'available_classes': user_classes,  # Now this excludes the current class
        'available_exams': available_exams,
        'questions': questions,
        'selected_class_id': int(selected_class_id),
        'selected_exam_id': int(selected_exam_id) if selected_exam_id else None,
    })

@login_required
def remove_image(request, class_id, exam_id, image_name):
    # Ensure the request is a POST (to avoid issues with unintended GET requests)
    if request.method == 'POST':
        current_class = get_object_or_404(Class, id=class_id)
        current_exam = get_object_or_404(Exam, id=exam_id)

        # Get the image file path
        folder_path = os.path.join(settings.MEDIA_ROOT, 'uploads', f'class_{current_class.id}', f'exam_{current_exam.id}')
        file_path = os.path.join(folder_path, image_name)

        try:
            # Check if the file exists, if so, delete it
            if os.path.exists(file_path):
                os.remove(file_path)
                # Also remove the image from the session
                uploaded_images = request.session.get('uploaded_images', [])
                uploaded_images = [img for img in uploaded_images if img['name'] != image_name]
                request.session['uploaded_images'] = uploaded_images
                messages.success(request, "Image deleted successfully.")
            else:
                messages.error(request, "File not found.")
        except Exception as e:
            messages.error(request, f"Error deleting file: {str(e)}")

        return redirect('scan_page', class_id=class_id, exam_id=exam_id)

    # If not POST, redirect to scan page with an error message
    messages.error(request, "Invalid request method.")
    return redirect('scan_page', class_id=class_id, exam_id=exam_id)


@login_required
def scan_page(request, class_id, exam_id):
    """
    Main view for the scan page handling image uploads, scanning, and result management.
    Allows for rescanning of exam papers.
    
    Args:
        request (HttpRequest): The current request object
        class_id (int): ID of the current class
        exam_id (int): ID of the current exam
    
    Returns:
        HttpResponse: Rendered scan page
    """
    current_class = get_object_or_404(Class, id=class_id)
    current_exam = get_object_or_404(Exam, id=exam_id)
    exams = current_class.exams.all()

    # Get upload paths
    base_upload_path, absolute_upload_path, base_csv_path = get_upload_paths(current_class, current_exam)
    
    # Initialize result paths
    result_csv = ''
    csv_file = ''
    results_folder = os.path.join(absolute_upload_path)

    if request.method == 'POST':
        if 'image_upload' in request.FILES:
            if handle_image_upload(request, absolute_upload_path, request.user):
                return redirect('scan_page', class_id=class_id, exam_id=exam_id)

        elif 'scan_images' in request.POST:
            # Validate exam and CSV for scanning
            csv_exam_id = request.POST.get('csv_indicator', current_exam.id)
            selected_exam = get_object_or_404(Exam, id=csv_exam_id)

            if selected_exam.id != current_exam.id:
                messages.error(request, "Selected exam does not match the current exam.")
                return redirect('scan_page', class_id=class_id, exam_id=exam_id)

            uploaded_images = get_uploaded_images(absolute_upload_path, base_upload_path, request.user)
            if not uploaded_images:
                messages.error(request, "No images available for scanning.")
                return redirect('scan_page', class_id=class_id, exam_id=exam_id)

            # Construct CSV path consistently
            csv_file = os.path.join(settings.MEDIA_ROOT, 'csv', 
                                  f'class_{current_class.id}', 
                                  f'exam_{selected_exam.id}_sets.csv')

            # Validate exam and CSV
            is_valid, error_message = validate_exam_for_scanning(
                request, current_class, current_exam, csv_file
            )
            if not is_valid:
                messages.error(request, error_message)
                return redirect('scan_page', class_id=class_id, exam_id=exam_id)

            try:
                # Verify upload folder exists and contains files
                if not os.path.exists(absolute_upload_path):
                    messages.error(request, "Upload folder not found.")
                    return redirect('scan_page', class_id=class_id, exam_id=exam_id)

                # Generate unique timestamp for this scan
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Call OMR with absolute paths
                result_csv = omr(csv_file, absolute_upload_path)
                
                if result_csv and os.path.exists(result_csv):
                    # Rename the result file to include timestamp
                    new_result_csv = os.path.join(os.path.dirname(result_csv), 
                                                f'Results_exam_{exam_id}_{timestamp}.csv')
                    os.rename(result_csv, new_result_csv)
                    result_csv = new_result_csv
                    messages.success(request, "Scanning completed. Results saved successfully.")
                else:
                    messages.warning(request, "Scanning completed but no results were generated.")
                    
            except Exception as e:
                messages.error(request, f"Scanning failed: {str(e)}")
                return redirect('scan_page', class_id=class_id, exam_id=exam_id)

        elif 'delete_results' in request.POST:
            # Delete all user-specific images in the directory
            if os.path.exists(absolute_upload_path):
                for filename in os.listdir(absolute_upload_path):
                    file_path = os.path.join(absolute_upload_path, filename)
                    # Only delete files with the current user's identifier
                    if os.path.isfile(file_path) and f"user_{request.user.id}_" in filename:
                        os.remove(file_path)
                messages.success(request, "Your uploaded images deleted successfully.")

            return redirect('scan_page', class_id=class_id, exam_id=exam_id)

    # Get existing results if any
    existing_results = []
    if os.path.exists(results_folder):
        existing_results = [f for f in os.listdir(results_folder) 
                          if f.startswith('Results_exam_') and f.endswith('.csv')]

    context = {
        'current_class': current_class,
        'current_exam': current_exam,
        'exams': exams,
        'upload_path': absolute_upload_path,
        'uploaded_images': get_uploaded_images(absolute_upload_path, base_upload_path, request.user),
        'result_csv': result_csv,
        'csv_file': csv_file,
        'existing_results': existing_results,
        'can_scan': True  # Always allow scanning
    }

    return render(request, 'scan_page.html', context)



def get_uploaded_images(absolute_upload_path, base_upload_path, current_user):
    """
    Retrieve uploaded images from a specific directory for the current user.
    
    Args:
        absolute_upload_path (str): Absolute path to the upload directory
        base_upload_path (str): Base path for generating file URLs
        current_user (User): Current user object
    
    Returns:
        list: List of dictionaries containing image details
    """
    if not os.path.exists(absolute_upload_path):
        return []
    
    uploaded_images = []
    for filename in os.listdir(absolute_upload_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            # Check if the filename contains the user's identifier
            if f"user_{current_user.id}_" in filename:
                file_url = os.path.join(settings.MEDIA_URL, base_upload_path, filename)
                uploaded_images.append({
                    'name': filename,
                    'url': file_url,
                    'absolute_path': os.path.join(absolute_upload_path, filename)
                })
    return uploaded_images

def handle_image_upload(request, absolute_upload_path, current_user):
    """
    Handle image file uploads to a specified directory.
    
    Args:
        request (HttpRequest): The current request object
        absolute_upload_path (str): The absolute filesystem path to upload images
        current_user (User): The current user object
    
    Returns:
        bool: True if upload was successful, False otherwise
    """
    uploaded_files = request.FILES.getlist('image_upload')
    if not uploaded_files:
        return False
    
    # Ensure upload directory exists
    os.makedirs(absolute_upload_path, exist_ok=True)
    
    for image in uploaded_files:
        # Modify filename to include user identifier
        modified_filename = f"user_{current_user.id}_{image.name}"
        
        # Create storage with absolute path
        fs = FileSystemStorage(location=absolute_upload_path)
        fs.save(modified_filename, image)
    
    messages.success(request, f"{len(uploaded_files)} image(s) uploaded successfully.")
    return True

def get_upload_paths(current_class, current_exam):
    """
    Generate consistent upload and CSV paths for a given class and exam.
    
    Args:
        current_class (Class): The current class object
        current_exam (Exam): The current exam object
    
    Returns:
        tuple: Containing base and absolute upload paths, and base CSV path
    """
    base_upload_path = os.path.join('uploads', f'class_{current_class.id}', f'exam_{current_exam.id}')
    absolute_upload_path = os.path.join(settings.MEDIA_ROOT, base_upload_path)
    base_csv_path = os.path.join('csv', f'class_{current_class.id}')
    
    return base_upload_path, absolute_upload_path, base_csv_path

def validate_exam_for_scanning(request, current_class, current_exam, csv_file):
    """
    Validate the exam and CSV file before scanning.
    
    Args:
        request (HttpRequest): The current request object
        current_class (Class): The current class object
        current_exam (Exam): The current exam object
        csv_file (str): Path to the CSV file
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Validate CSV file existence
    if not os.path.exists(csv_file):
        return False, "Required CSV file not found. Please generate exam sets first."
    
    return True, ""

def scan_exam_view(request):
    folder_path = None
    csv_file = None
    images = []
    
    if request.method == "POST":
        class_name = request.POST.get('class_name', 'Unknown_Class')
        
        # Create folder in the media directory with class name and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{class_name}_{timestamp}"
        folder_path = os.path.join(settings.MEDIA_ROOT, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Handle CSV file upload
        csv_file = request.FILES.get('exam_csv')
        if csv_file:
            fs = FileSystemStorage(location=folder_path)
            csv_filename = fs.save(csv_file.name, csv_file)  # This saves the CSV file in the new folder

        # Handle image uploads
        images = request.FILES.getlist('images')
        for img in images:
            fs.save(img.name, img)  # Save each image

        # Process images and create result CSV
        result_csv = process_scanned_images(folder_path, images)
        
        # Save the result CSV in the same folder
        result_csv_path = os.path.join(folder_path, 'scan_results.csv')
        with open(result_csv_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerows(result_csv)

        return redirect('scan_exam_view')  # Redirect to the same view or another page
    
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

    # Filter questions based on difficulty
    easy_questions = list(exam.questions.filter(difficulty='Easy'))
    medium_questions = list(exam.questions.filter(difficulty='Medium'))
    hard_questions = list(exam.questions.filter(difficulty='Hard'))

    easy_count = len(easy_questions)
    medium_count = len(medium_questions)
    hard_count = len(hard_questions)

    if request.method == "POST":
        num_sets = int(request.POST.get('num_sets', 1))
        easy_q_requested = int(request.POST.get('easy_questions', 0))
        medium_q_requested = int(request.POST.get('medium_questions', 0))
        hard_q_requested = int(request.POST.get('hard_questions', 0))

        students = list(current_class.students.all())
        total_students = len(students)

        # Validate number of sets
        if num_sets > total_students:
            num_sets = total_students

        # Check if there are enough questions
        if easy_q_requested > easy_count or medium_q_requested > medium_count or hard_q_requested > hard_count:
            messages.error(request, "Not enough questions available for the selected difficulty.")
            return redirect('generate_exam_sets', class_id=class_id, exam_id=exam_id)

        # Clear existing test sets for re-generation
        TestSet.objects.filter(exam=exam, student__in=students).delete()

        generated_sets = []
        csv_rows = []

        # Generate the actual unique sets first
        unique_sets = []
        exam_id_part = str(exam.exam_id).zfill(3)[-3:]  # Get last 3 digits of exam_id
        
        # Generate set IDs first - one for each unique set
        set_ids = []
        used_set_ids = set()
        
        for set_no in range(num_sets):
            while True:
                random_part = f"{random.randint(0, 99):02d}"
                set_id = f"{exam_id_part}{random_part}"
                
                if set_id not in used_set_ids and not TestSet.objects.filter(set_id=set_id).exists():
                    used_set_ids.add(set_id)
                    set_ids.append(set_id)
                    break

            # Shuffle and select questions for each set
            random.shuffle(easy_questions)
            random.shuffle(medium_questions)
            random.shuffle(hard_questions)

            selected_easy = easy_questions[:easy_q_requested]
            selected_medium = medium_questions[:medium_q_requested]
            selected_hard = hard_questions[:hard_q_requested]

            selected_questions = selected_easy + selected_medium + selected_hard
            random.shuffle(selected_questions)

            answer_key = ''.join(str(ord(question.answer) - ord('A')) for question in selected_questions)
            difficulty_points = ''.join(
                '1' if question.difficulty == 'Easy' 
                else '2' if question.difficulty == 'Medium' 
                else '3'
                for question in selected_questions
            )

            unique_sets.append({
                'set_id': set_ids[set_no],
                'questions': selected_questions,
                'answer_key': answer_key,
                'difficulty_points': difficulty_points,
                'set_no': set_no + 1
            })

        # Distribute sets among students
        for idx, student in enumerate(students):
            # Use modulo to cycle through the sets
            set_data = unique_sets[idx % num_sets]
            
            # Create and save the test set
            test_set = TestSet(
                exam=exam,
                student=student,
                set_no=set_data['set_no'],
                answer_key=set_data['answer_key'],
                set_id=set_data['set_id']  # Use the same set_id for students with same questions
            )
            test_set.save()
            test_set.questions.add(*set_data['questions'])

            # Add to generated sets list
            generated_sets.append({
                'student_id': student.student_id,
                'student_name': f"{student.first_name} {student.last_name}",
                'set_id': set_data['set_id'],
                'answer_key': set_data['answer_key'],
                'difficulty_points': set_data['difficulty_points']
            })

            # Add row to CSV - use full student ID instead of slicing
            csv_rows.append([
                student.last_name,
                student.first_name,
                student.middle_initial,
                student.student_id,  # Changed from student.student_id[4:] to use full 7-digit ID
                set_data['set_id'],
                set_data['answer_key'],
                set_data['difficulty_points']
            ])

        # Save to CSV file
        if csv_rows:
            csv_file_path = os.path.join(settings.MEDIA_ROOT, 'csv', f'class_{current_class.id}', f'exam_{exam.id}_sets.csv')
            os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
            
            with open(csv_file_path, mode='w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(['Last Name', 'First Name', 'Middle Initial', 'ID', 'Set ID', 'Answer Key', 'Difficulty Points'])
                writer.writerows(csv_rows)

            messages.success(request, f"Successfully generated {len(generated_sets)} exam sets across {num_sets} unique test versions.")
        else:
            messages.warning(request, "No sets were generated.")

        return redirect('exam_detail', exam_id=exam_id)

    context = {
        'exam': exam,
        'current_class': current_class,
        'generated_sets': TestSet.objects.filter(exam=exam, student__in=current_class.students.all()).order_by('student__last_name', 'student__first_name'),
        'easy_count': easy_count,
        'medium_count': medium_count,
        'hard_count': hard_count,
    }
    return render(request, 'exams/generate_sets.html', context)

# @login_required
# def generate_exam_sets(request, class_id, exam_id):
#     exam = get_object_or_404(Exam, id=exam_id)
#     current_class = get_object_or_404(Class, id=class_id)

#     # Filter questions based on difficulty
#     easy_questions = list(exam.questions.filter(difficulty='Easy'))
#     medium_questions = list(exam.questions.filter(difficulty='Medium'))
#     hard_questions = list(exam.questions.filter(difficulty='Hard'))

#     easy_count = len(easy_questions)
#     medium_count = len(medium_questions)
#     hard_count = len(hard_questions)

#     if request.method == "POST":
#         num_sets = int(request.POST.get('num_sets', 1))
#         easy_q_requested = int(request.POST.get('easy_questions', 0))
#         medium_q_requested = int(request.POST.get('medium_questions', 0))
#         hard_q_requested = int(request.POST.get('hard_questions', 0))

#         students = list(current_class.students.all())
#         total_students = len(students)

#         # Validate number of sets
#         if num_sets > total_students:
#             num_sets = total_students

#         # Check if there are enough questions
#         if easy_q_requested > easy_count or medium_q_requested > medium_count or hard_q_requested > hard_count:
#             messages.error(request, "Not enough questions available for the selected difficulty.")
#             return redirect('generate_exam_sets', class_id=class_id, exam_id=exam_id)

#         # Clear existing test sets for re-generation
#         TestSet.objects.filter(exam=exam, student__in=students).delete()

#         generated_sets = []
#         csv_rows = []

#         # Generate the actual unique sets first
#         unique_sets = []
#         exam_id_part = str(exam.exam_id).zfill(3)[-3:]  # Get last 3 digits of exam_id
        
#         # Generate set IDs first - one for each unique set
#         set_ids = []
#         used_set_ids = set()
        
#         for set_no in range(num_sets):
#             while True:
#                 random_part = f"{random.randint(0, 99):02d}"
#                 set_id = f"{exam_id_part}{random_part}"
                
#                 if set_id not in used_set_ids and not TestSet.objects.filter(set_id=set_id).exists():
#                     used_set_ids.add(set_id)
#                     set_ids.append(set_id)
#                     break

#             # Shuffle and select questions for each set
#             random.shuffle(easy_questions)
#             random.shuffle(medium_questions)
#             random.shuffle(hard_questions)

#             selected_easy = easy_questions[:easy_q_requested]
#             selected_medium = medium_questions[:medium_q_requested]
#             selected_hard = hard_questions[:hard_q_requested]

#             selected_questions = selected_easy + selected_medium + selected_hard
#             random.shuffle(selected_questions)

#             answer_key = ''.join(str(ord(question.answer) - ord('A')) for question in selected_questions)
#             difficulty_points = ''.join(
#                 '1' if question.difficulty == 'Easy' 
#                 else '2' if question.difficulty == 'Medium' 
#                 else '3'
#                 for question in selected_questions
#             )

#             unique_sets.append({
#                 'set_id': set_ids[set_no],
#                 'questions': selected_questions,
#                 'answer_key': answer_key,
#                 'difficulty_points': difficulty_points,
#                 'set_no': set_no + 1
#             })

#         # Distribute sets among students
#         for idx, student in enumerate(students):
#             # Use modulo to cycle through the sets
#             set_data = unique_sets[idx % num_sets]
            
#             # Create and save the test set
#             test_set = TestSet(
#                 exam=exam,
#                 student=student,
#                 set_no=set_data['set_no'],
#                 answer_key=set_data['answer_key'],
#                 set_id=set_data['set_id']  # Use the same set_id for students with same questions
#             )
#             test_set.save()
#             test_set.questions.add(*set_data['questions'])

#             # Add to generated sets list
#             generated_sets.append({
#                 'student_id': student.student_id,
#                 'student_name': f"{student.first_name} {student.last_name}",
#                 'set_id': set_data['set_id'],
#                 'answer_key': set_data['answer_key'],
#                 'difficulty_points': set_data['difficulty_points']
#             })

#             # Add row to CSV
#             csv_rows.append([
#                 student.last_name,
#                 student.first_name,
#                 student.middle_initial,
#                 student.student_id[4:],
#                 set_data['set_id'],
#                 set_data['answer_key'],
#                 set_data['difficulty_points']
#             ])

#         # Save to CSV file
#         if csv_rows:
#             csv_file_path = os.path.join(settings.MEDIA_ROOT, 'csv', f'class_{current_class.id}', f'exam_{exam.id}_sets.csv')
#             os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
            
#             with open(csv_file_path, mode='w', newline='') as csv_file:
#                 writer = csv.writer(csv_file)
#                 writer.writerow(['Last Name', 'First Name', 'Middle Initial', 'ID', 'Set ID', 'Answer Key', 'Difficulty Points'])
#                 writer.writerows(csv_rows)

#             messages.success(request, f"Successfully generated {len(generated_sets)} exam sets across {num_sets} unique test versions.")
#         else:
#             messages.warning(request, "No sets were generated.")

#         return redirect('exam_detail', exam_id=exam_id)  # Changed from 'exam_details' to 'exam_detail'

#     context = {
#         'exam': exam,
#         'current_class': current_class,
#         'generated_sets': TestSet.objects.filter(exam=exam, student__in=current_class.students.all()).order_by('student__last_name', 'student__first_name'),
#         'easy_count': easy_count,
#         'medium_count': medium_count,
#         'hard_count': hard_count,
#     }
#     return render(request, 'exams/generate_sets.html', context)



# def grade_exam(student_answers_by_difficulty, answer_key, difficulty_points):
#     """
#     Grade a student's exam based on the answer key and difficulty points
    
#     Parameters:
#     student_answers_by_difficulty (dict): Dictionary with lists of answers by difficulty (Easy, Medium, Hard)
#     answer_key (str): String of correct answers (0-based indices, e.g., "01230")
#     difficulty_points (str): String indicating difficulty for each question (e.g., "11223")
    
#     Returns:
#     tuple: (total_score, max_possible_score, breakdown_by_difficulty, incorrect_answers, failed_status)
#     """
#     total_score = 0
#     max_possible_score = 0
#     total_correct_answers = 0
#     total_questions = 0
    
#     # Initialize breakdown with points per difficulty
#     breakdown = {
#         'Easy': {'correct': 0, 'total': 0, 'points': 0, 'incorrect': [], 'point_value': 1},
#         'Medium': {'correct': 0, 'total': 0, 'points': 0, 'incorrect': [], 'point_value': 2},
#         'Hard': {'correct': 0, 'total': 0, 'points': 0, 'incorrect': [], 'point_value': 3}
#     }
    
#     incorrect_answers = []
    
#     # Convert answer key to list of integers
#     correct_answers = [int(ans) for ans in answer_key]
    
#     # Create difficulty map
#     difficulty_map = {
#         '1': 'Easy',
#         '2': 'Medium',
#         '3': 'Hard'
#     }
    
#     # Count expected answers by difficulty
#     expected_counts = {
#         'Easy': difficulty_points.count('1'),
#         'Medium': difficulty_points.count('2'),
#         'Hard': difficulty_points.count('3')
#     }
    
#     # Calculate maximum possible score
#     for difficulty in difficulty_points:
#         diff_type = difficulty_map[difficulty]
#         max_possible_score += breakdown[diff_type]['point_value']
    
#     # Validate answers count
#     for difficulty, expected in expected_counts.items():
#         student_ans = student_answers_by_difficulty.get(difficulty, [])
#         if len(student_ans) != expected:
#             return 0, max_possible_score, breakdown, [
#                 f"Invalid number of {difficulty} answers. Expected {expected}, got {len(student_ans)}"
#             ], True
    
#     # Grade each answer
#     current_index_by_difficulty = {'Easy': 0, 'Medium': 0, 'Hard': 0}
    
#     for i, (correct_ans, diff) in enumerate(zip(correct_answers, difficulty_points)):
#         difficulty = difficulty_map[diff]
#         point_value = breakdown[difficulty]['point_value']
#         total_questions += 1
        
#         # Get student's answer for this difficulty level
#         student_ans_index = current_index_by_difficulty[difficulty]
#         if student_ans_index >= len(student_answers_by_difficulty[difficulty]):
#             incorrect_answers.append(f"Missing {difficulty} answer at question {i+1}")
#             breakdown[difficulty]['incorrect'].append(i+1)
#             continue
        
#         student_ans = student_answers_by_difficulty[difficulty][student_ans_index]
#         current_index_by_difficulty[difficulty] += 1
        
#         # Update statistics
#         breakdown[difficulty]['total'] += 1
        
#         # Check if answer is correct
#         if student_ans == correct_ans:
#             breakdown[difficulty]['correct'] += 1
#             breakdown[difficulty]['points'] += point_value
#             total_score += point_value
#             total_correct_answers += 1
#         else:
#             incorrect_answers.append(
#                 f"Question {i+1} ({difficulty}): answered {student_ans}, correct was {correct_ans}"
#             )
#             breakdown[difficulty]['incorrect'].append(i+1)
    
#     # Calculate percentages
#     for difficulty in breakdown:
#         if breakdown[difficulty]['total'] > 0:
#             breakdown[difficulty]['percentage'] = (
#                 breakdown[difficulty]['correct'] / breakdown[difficulty]['total'] * 100
#             )
#         else:
#             breakdown[difficulty]['percentage'] = 0
    
#     # Determine failed status (zero correct answers)
#     failed_status = total_correct_answers == 0
    
#     return total_score, max_possible_score, breakdown, incorrect_answers, failed_status

# def format_grade_report(student_id, student_name, score, max_score, breakdown, errors, set_id=None, failed=False):
#     """
#     Format a readable grade report with improved difficulty breakdown and failure status
#     """
#     percentage = (score / max_score * 100) if max_score > 0 else 0
    
#     report = f"Grade Report for {student_name} (ID: {student_id})"
#     if set_id:
#         report += f" - Set {set_id}"
    
#     if failed:
#         report += "\nSTATUS: FAILED - No correct answers"
        
#     report += f"\nTotal Score: {score}/{max_score} ({percentage:.1f}%)\n\n"
    
#     report += "Breakdown by Difficulty:\n"
#     for difficulty, results in breakdown.items():
#         if results['total'] > 0:
#             report += (f"{difficulty}: {results['correct']}/{results['total']} correct "
#                       f"({results['percentage']:.1f}%) - {results['points']} points\n")
#             if results['incorrect']:
#                 report += f"    Incorrect questions: {', '.join(map(str, results['incorrect']))}\n"
    
#     if errors:
#         report += "\nErrors:\n"
#         for error in errors:
#             report += f"- {error}\n"
            
#     return report

# # Example usage:
# if __name__ == "__main__":
#     # Example data
#     answer_key = "01230"
#     difficulty_points = "11123"
    
#     # Test case 1: Some correct answers
#     student_answers = {
#         'Easy': [0, 1, 2],
#         'Medium': [3],
#         'Hard': [0]
#     }
    
#     score, max_score, breakdown, errors, failed = grade_exam(
#         student_answers,
#         answer_key,
#         difficulty_points
#     )
    
#     report = format_grade_report(
#         student_id="2001234",
#         student_name="John Doe",
#         score=score,
#         max_score=max_score,
#         breakdown=breakdown,
#         errors=errors,
#         set_id="001A",
#         failed=failed
#     )
#     print("Test Case 1 - Normal:")
#     print(report)
    
#     # Test case 2: All wrong answers
#     student_answers = {
#         'Easy': [1, 2, 3],
#         'Medium': [0],
#         'Hard': [1]
#     }
    
#     score, max_score, breakdown, errors, failed = grade_exam(
#         student_answers,
#         answer_key,
#         difficulty_points
#     )
    
#     report = format_grade_report(
#         student_id="2001235",
#         student_name="Jane Doe",
#         score=score,
#         max_score=max_score,
#         breakdown=breakdown,
#         errors=errors,
#         set_id="001B",
#         failed=failed
#     )
#     print("\nTest Case 2 - All Wrong:")
#     print(report)



@login_required
def delete_test_set(request, test_set_id):
    test_set = get_object_or_404(TestSet, id=test_set_id)
    exam = test_set.exam

    # Use 'class_assigned.user' instead of 'class_assigned.owner'
    if request.user == exam.class_assigned.user:  # Access the user field in the Class model
        test_set.delete()
        messages.success(request, "Test set deleted successfully.")
    else:
        return HttpResponseForbidden("You do not have permission to delete this test set.")

    return redirect('generate_exam_sets', class_id=exam.class_assigned.id, exam_id=exam.id)

@login_required 
def download_test_paper(request, class_id, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    current_class = get_object_or_404(Class, id=class_id)

    # Check if there are any test sets generated
    test_sets = TestSet.objects.filter(
        exam=exam,
        student__in=current_class.students.all()
    )

    if not test_sets.exists():
        messages.error(request, "No test sets have been generated yet. Please generate test sets first.")
        return redirect('generate_exam_sets', class_id=current_class.id, exam_id=exam_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="test_paper_class_{current_class.id}_exam_{exam.id}.pdf"'

    # Create PDF with 0.5 inch margins (36 points = 0.5 inches)
    p = SimpleDocTemplate(
        response, 
        pagesize=legal,
        topMargin=36, 
        bottomMargin=36, 
        leftMargin=36, 
        rightMargin=36
    )
    
    # Get styles and customize for compact layout
    styles = getSampleStyleSheet()
    
    # Modify styles for smaller font and tighter spacing
    styles['Normal'].fontSize = 8  # Reduced from 10 to 8
    styles['Normal'].leading = 10  # Reduced leading (font size + 2)
    styles['Title'].fontSize = 10  # Reduced from 12 to 10
    styles['Title'].leading = 12
    styles['Heading3'].fontSize = 9  # Reduced from 11 to 9
    styles['Heading3'].leading = 11
    styles['Heading4'].fontSize = 8  # Reduced from 10 to 8
    styles['Heading4'].leading = 10
    
    # Create document elements list
    elements = []
    
    # Process each test set
    test_sets = test_sets.prefetch_related('questions').order_by('student__last_name', 'student__first_name')

    for test_set in test_sets:
        student = test_set.student
        
        # Process questions and answers
        all_questions = list(test_set.questions.all())
        ordered_questions = []
        answers = []
        
        if test_set.answer_key:
            for idx, key in enumerate(test_set.answer_key):
                try:
                    answer_letter = chr(ord('A') + int(key))
                    answers.append(f"{idx + 1}. {answer_letter}")
                    
                    matching_question = next(
                        (q for q in all_questions if ord(q.answer) - ord('A') == int(key)),
                        None
                    )
                    if matching_question:
                        ordered_questions.append(matching_question)
                        all_questions.remove(matching_question)
                except (ValueError, IndexError):
                    # Skip invalid answer keys
                    continue
        
        ordered_questions.extend(all_questions)
        # Include all questions (up to 30) instead of limiting to 20
        
        # Add a page break
        elements.append(PageBreak())
        
        # Document header
        header_text = f"<b>{exam.name}</b>"
        elements.append(Paragraph(header_text, styles['Title']))
        elements.append(Spacer(1, 3))  # Minimal spacing between header and info
        
        # Student info (all on one line to save space)
        info_text = f"<b>Name:</b> {student.last_name}, {student.first_name} &nbsp;&nbsp; <b>ID:</b> {student.student_id} &nbsp;&nbsp; <b>Set:</b> {test_set.set_id}"
        elements.append(Paragraph(info_text, styles['Normal']))
        
        if exam.time_limit:
            time_text = f"<b>Time Limit:</b> {exam.time_limit} minutes"
            elements.append(Paragraph(time_text, styles['Normal']))
        
        elements.append(Spacer(1, 2))  # Extremely reduced spacing
        
        # Instructions (if available)
        if exam.instructions:
            elements.append(Paragraph("<b>Instructions:</b>", styles['Heading3']))
            elements.append(Paragraph(exam.instructions, styles['Normal']))
            elements.append(Spacer(1, 2))  # Very minimal spacing
        
        # Questions
        elements.append(Paragraph("<b>Questions:</b>", styles['Heading3']))
        elements.append(Spacer(1, 1))  # Extremely minimal spacing
        
        for i, question in enumerate(ordered_questions):
            question_text = f"{i+1}. {question.question_text}"
            elements.append(Paragraph(question_text, styles['Heading4']))
            
            # Options with compact spacing
            option_data = [
                ('A', question.option_a),
                ('B', question.option_b),
                ('C', question.option_c),
                ('D', question.option_d),
                ('E', question.option_e)
            ]
            
            for opt_letter, opt_text in option_data:
                if opt_text:
                    option_text = f"&nbsp;&nbsp;{opt_letter}. {opt_text}"  # Reduced indentation
                    # Create a paragraph with indentation
                    paragraph = Paragraph(option_text, styles['Normal'])
                    paragraph.leftIndent = 10  # Reduced indentation from 15 to 10
                    elements.append(paragraph)
            
            elements.append(Spacer(1, 1))  # Minimal space between questions
        
        # Add answer key page for staff/superusers
        if request.user.is_staff or request.user.is_superuser:
            elements.append(PageBreak())
            elements.append(Paragraph("<b>ANSWER KEY</b>", styles['Title']))
            elements.append(Paragraph(f"Student: {student.last_name}, {student.first_name}", styles['Normal']))
            elements.append(Paragraph(f"Set ID: {test_set.set_id}", styles['Normal']))
            elements.append(Spacer(1, 6))
            
            # Create a compact table for answers (5 answers per row)
            answer_rows = []
            row = []
            
            for idx, answer in enumerate(answers):
                row.append(answer)
                
                # Start a new row after every 5 items
                if (idx + 1) % 5 == 0:
                    answer_rows.append(row)
                    row = []
            
            # Add any remaining items
            if row:
                while len(row) < 5:  # Pad the row with empty cells
                    row.append('')
                answer_rows.append(row)
            
            if answer_rows:
                answer_table = Table(answer_rows, colWidths=[70] * 5)  # Reduced column widths
                answer_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),  # Reduced font size for answer key
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 2),  # Reduced padding
                    ('RIGHTPADDING', (0, 0), (-1, -1), 2),  # Reduced padding
                    ('TOPPADDING', (0, 0), (-1, -1), 1),  # Reduced padding
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),  # Reduced padding
                ]))
                elements.append(answer_table)
    
    # Build the PDF
    p.build(elements)
    
    return response

@login_required
def download_exam_sets_csv(request, class_id, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    current_class = get_object_or_404(Class, id=class_id)
    students = current_class.students.all()

    # Initialize CSV writer for download
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="exam_sets_class_{current_class.id}_exam_{exam.id}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Lastname', 'Firstname', 'MiddleInitial', 'ID', 'Exam ID', 'Answer Key'])

    for student in students:
        test_set = TestSet.objects.filter(exam=exam, student=student).first()
        if test_set:
            formatted_id = student.student_id[4:] if len(student.student_id) > 4 else student.student_id
            exam_unique_id = str(random.randint(10000, 99999))  # Random 5-digit ID
            middle_initial = student.middle_initial if student.middle_initial else ''

            writer.writerow([
                student.last_name,
                student.first_name,
                middle_initial,
                formatted_id,
                exam_unique_id,
                test_set.answer_key  # Assuming you have stored answer key in TestSet model
            ])

    return response


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
                exam_name = form.cleaned_data.get('name')
                # Check if exam name already exists for this user's classes
                if Exam.objects.filter(
                    class_assigned__user=request.user, 
                    name__iexact=exam_name
                ).exists():
                    form.add_error('name', 'An exam with this name already exists.')
                    messages.error(request, 'Exam name must be unique.')
                else:
                    # Save the exam instance
                    exam = form.save(commit=False)
                    exam.save()
                    messages.success(request, 'Exam added successfully!')
                    return redirect('exams')
            except IntegrityError:
                form.add_error('exam_id', 'Exam ID must be unique.')
                messages.error(request, 'There was an error adding the exam.')
        else:
            messages.error(request, 'Please check the form for errors.')
    else:
        form = ExamForm(user=request.user)

    user_classes = Class.objects.filter(user=request.user)
    context = {'form': form, 'classes': user_classes}
    return render(request, 'exams.html', context)


@login_required
def exam_detail_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    available_exams = Exam.objects.exclude(id=exam_id)  # Other exams to copy questions from
    current_class = exam.class_assigned

    # Determine sorting option
    sort_by = request.GET.get('sort_by', 'most_recent')
    questions = exam.questions.all()  # Questions already added to the current exam

    if sort_by == 'difficulty':
        questions = sorted(questions, key=lambda q: ('Easy', 'Medium', 'Hard').index(q.difficulty))
    elif sort_by == 'most_recent':
        questions = questions.order_by('-id')  # Assuming that ID corresponds to the creation time

    if request.method == 'POST':
        selected_exam_id = request.POST.get('exam_source_id')
        if selected_exam_id:
            # Logic for copying questions
            source_exam = get_object_or_404(Exam, id=selected_exam_id)
            selected_question_ids = request.POST.getlist('questions')
            if selected_question_ids:
                selected_questions = Question.objects.filter(id__in=selected_question_ids)
                exam.questions.add(*selected_questions)  # Add selected questions
                messages.success(request, 'Selected questions copied successfully!')
            else:
                messages.error(request, 'No questions selected to copy!')
        else:
            # Logic for adding a new question
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
                exam.questions.add(question)  # Add newly created question to the exam
                messages.success(request, 'New question added successfully!')
            else:
                messages.error(request, 'Question text, Option A, Option B, and Correct Answer are required!')

    return render(request, 'exam_detail.html', {
        'exam': exam,
        'current_class': current_class,
        'questions': questions,
        'available_exams': available_exams,
        'sort_by': sort_by  # Pass the sort option to the template
    })

@login_required
def download_answer_sheet(request, exam_id):
   exam = get_object_or_404(Exam, id=exam_id)
   
   pdf_path = os.path.join(settings.BASE_DIR, 'static', 'pdf', 'SmartScore_AnswerSheet_Template.pdf')
   
   if os.path.exists(pdf_path):
       response = FileResponse(open(pdf_path, 'rb'), as_attachment=True, filename=f'exam_{exam_id}_answer_sheet.pdf')
       return response
   else:
       from django.http import HttpResponseNotFound
       return HttpResponseNotFound(f'Answer sheet PDF not found at {pdf_path}')


@login_required
def grade_exam_view(request, exam_id, student_id):
    student = get_object_or_404(Student, id=student_id)
    exam = get_object_or_404(Exam, id=exam_id)
    student_questions = StudentQuestion.objects.filter(student=student, exam=exam)

    # Find the most recent OMR results file
    results_dir = os.path.join(
        settings.MEDIA_ROOT,
        'uploads',
        f'class_{student.assigned_class.id}',
        f'exam_{exam.id}'
    )
    
    omr_results = None
    if os.path.exists(results_dir):
        result_files = [f for f in os.listdir(results_dir) if f.startswith('Results_exam_') and f.endswith('.csv')]
        if result_files:
            # Get the most recent results file
            latest_result = max(result_files, key=lambda x: os.path.getctime(os.path.join(results_dir, x)))
            result_path = os.path.join(results_dir, latest_result)
            
            try:
                with open(result_path, 'r') as file:
                    csv_reader = csv.DictReader(file)
                    for row in csv_reader:
                        # Match student by their ID
                        if str(row.get('ID')) == str(student.student_id):
                            omr_results = row
                            break
            except Exception as e:
                messages.error(request, f"Error reading OMR results: {str(e)}")

    # If we found OMR results and grades haven't been set yet
    if omr_results and not any(q.marks for q in student_questions):
        try:
            # Parse incorrect answers
            incorrect_answers = eval(omr_results.get('Incorrect Answer', '[]'))
            invalid_answers = eval(omr_results.get('Invalid Answer', '[]'))
            
            # Update marks for each question
            for student_question in student_questions:
                question_num = student_question.question.number
                # Mark as correct (1) if not in incorrect or invalid answers
                is_correct = question_num not in incorrect_answers and question_num not in invalid_answers
                student_question.marks = 1 if is_correct else 0
                student_question.save()
            
            messages.success(request, 'OMR results loaded successfully!')
        except Exception as e:
            messages.error(request, f"Error processing OMR results: {str(e)}")

    # Handle form submission for manual grading
    if request.method == 'POST':
        if 'save_grades' in request.POST:
            for student_question in student_questions:
                try:
                    marks = int(request.POST.get(f"marks_{student_question.id}", 0))
                    if 0 <= marks <= 1:
                        student_question.marks = marks
                        student_question.save()
                    else:
                        messages.error(request, f"Invalid marks for question {student_question.question.number}. Must be 0 or 1.")
                        return redirect('grade_exam', exam_id=exam_id, student_id=student_id)
                except ValueError:
                    messages.error(request, f"Invalid marks for question {student_question.question.number}.")
                    return redirect('grade_exam', exam_id=exam_id, student_id=student_id)
            
            messages.success(request, 'Grades saved successfully!')
            return redirect('class_detail', class_id=student.assigned_class.id)
        
        elif 'reset_grades' in request.POST:
            student_questions.update(marks=None)
            messages.success(request, 'Grades reset successfully!')
            return redirect('grade_exam', exam_id=exam_id, student_id=student_id)

    # Get scanned images
    scanned_images = []
    if os.path.exists(results_dir):
        for file in os.listdir(results_dir):
            if file.endswith(('.jpg', '.png', '.jpeg', '.pdf')):
                image_url = os.path.join(
                    settings.MEDIA_URL,
                    'uploads',
                    f'class_{student.assigned_class.id}',
                    f'exam_{exam.id}',
                    file
                )
                scanned_images.append(image_url)

    # Calculate statistics
    total_questions = len(student_questions)
    graded_questions = sum(1 for q in student_questions if q.marks is not None)
    total_score = sum(q.marks or 0 for q in student_questions)
    score_percentage = (total_score / total_questions * 100) if total_questions > 0 else 0

    # Add OMR results to context if available
    omr_info = None
    if omr_results:
        omr_info = {
            'score': omr_results.get('Score', 'N/A'),
            'invalid_answers': eval(omr_results.get('Invalid Answer', '[]')),
            'incorrect_answers': eval(omr_results.get('Incorrect Answer', '[]')),
            'set_id': omr_results.get('Set ID', 'N/A')
        }

    context = {
        'student': student,
        'exam': exam,
        'student_questions': student_questions,
        'total_score': total_score,
        'total_questions': total_questions,
        'graded_questions': graded_questions,
        'score_percentage': score_percentage,
        'scanned_images': scanned_images,
        'omr_results': omr_info
    }

    return render(request, 'grade_exam.html', context)


@login_required
def students_view(request):
    """
    View to display all students and handle student-related operations.
    """
    # Get all students, ordered by name
    students = Student.objects.all().order_by('first_name', 'last_name')
    
    if request.method == 'POST':
        # Handle any POST operations here if needed
        pass
        
    context = {
        'students': students,
        'title': 'Students List'  # Add a title for the page
    }
    return render(request, 'students.html', context)



@login_required
def scan_results_view(request, class_id, exam_id):
    current_class = get_object_or_404(Class, id=class_id)
    current_exam = get_object_or_404(Exam, id=exam_id)
    
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 
                             f'class_{class_id}', 
                             f'exam_{exam_id}')
    
    # Load deleted records
    deleted_records_file = os.path.join(upload_dir, 'deleted_records.json')
    deleted_records = []
    if os.path.exists(deleted_records_file):
        try:
            with open(deleted_records_file, 'r') as f:
                deleted_records = json.load(f)
        except json.JSONDecodeError:
            deleted_records = []
    
    scan_results = []
    question_stats = {
        'Easy': {'correct': 0, 'total': 0},
        'Medium': {'correct': 0, 'total': 0},
        'Hard': {'correct': 0, 'total': 0}
    }
    
    def determine_status(score, student_id, set_id):
        if student_id == 'N/A' or set_id == 'N/A':
            return 'failed_processing'
        elif score <= 0:
            return 'failed_exam'
        else:
            return 'success'
    
    def calculate_grade(score, max_score):
        if not score or not max_score:
            return 'N/A'
        
        percentage = (float(score) / float(max_score)) * 100
        
        if percentage >= 95:
            return 'A+'
        elif percentage >= 90:
            return 'A'
        elif percentage >= 85:
            return 'B+'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 75:
            return 'C'
        elif percentage >= 70:
            return 'C-'
        elif percentage >= 65:
            return 'D+'
        elif percentage >= 60:
            return 'D'
        else:
            return 'F'
    
    def parse_list(list_str):
        # Handle empty list, bracket-enclosed list, or plain string
        if not list_str or list_str == '[]':
            return []
        
        # Remove brackets and split
        cleaned = list_str.strip('[]')
        if not cleaned:
            return []
        
        # Split and strip each item
        return [item.strip() for item in cleaned.split(',') if item.strip()]
    
    # Process all result files
    if os.path.exists(upload_dir):
        csv_files = [f for f in os.listdir(upload_dir) if f.startswith('Results_exam') and f.endswith('.csv')]
        
        # Process each CSV file
        for csv_file in sorted(csv_files):  # Process in chronological order
            csv_path = os.path.join(upload_dir, csv_file)
            
            try:
                with open(csv_path, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    
                    for row in reader:
                        # Get student ID
                        student_id = row.get('ID', 'N/A')
                        
                        # Check if this record is deleted
                        record_id = f"{csv_file}|{student_id}"
                        if record_id in deleted_records:
                            continue  # Skip deleted records
                        
                        # Parse the specific incorrect answer lists by difficulty
                        easy_incorrect_list = parse_list(row.get('Easy Inc list', ''))
                        medium_incorrect_list = parse_list(row.get('Medium Inc list', ''))
                        hard_incorrect_list = parse_list(row.get('Hard Inc list', ''))
                        
                        # Get the basic counts from the CSV
                        easy_count = int(row.get('Easy', 0))
                        medium_count = int(row.get('Medium', 0))
                        hard_count = int(row.get('Hard', 0))
                        total_items = int(row.get('Items', 0))
                        max_score = int(row.get('Max Score', 0))
                        score = int(row.get('Score', 0))
                        
                        # Calculate percentage
                        percentage = (float(score) / float(max_score)) * 100 if max_score > 0 else 0
                        
                        # Calculate correct counts based on specific incorrect lists
                        easy_correct = easy_count - len(easy_incorrect_list)
                        medium_correct = medium_count - len(medium_incorrect_list)
                        hard_correct = hard_count - len(hard_incorrect_list)
                        
                        # Prepare answer stats
                        answer_stats = {
                            'Easy': {
                                'total': easy_count,
                                'correct': easy_correct,
                                'incorrect': len(easy_incorrect_list),
                                'incorrect_answers': easy_incorrect_list
                            },
                            'Medium': {
                                'total': medium_count,
                                'correct': medium_correct,
                                'incorrect': len(medium_incorrect_list),
                                'incorrect_answers': medium_incorrect_list
                            },
                            'Hard': {
                                'total': hard_count,
                                'correct': hard_correct,
                                'incorrect': len(hard_incorrect_list),
                                'incorrect_answers': hard_incorrect_list
                            }
                        }
                        
                        # Update overall statistics
                        for difficulty in ['Easy', 'Medium', 'Hard']:
                            question_stats[difficulty]['total'] += answer_stats[difficulty]['total']
                            question_stats[difficulty]['correct'] += answer_stats[difficulty]['correct']
                        
                        # Parse overall incorrect answers list
                        incorrect_answers_list = parse_list(row.get('Incorrect Ans list', ''))
                        
                        set_id = row.get('Set ID', 'N/A')
                        
                        scan_results.append({
                            'student_id': student_id,
                            'last_name': row.get('Last Name', ''),
                            'first_name': row.get('First Name', ''),
                            'middle_initial': row.get('Middle Initial', ''),
                            'set_id': set_id,
                            'answer_stats': answer_stats,
                            'total_items': total_items,
                            'score': score,
                            'max_score': max_score,
                            'percentage': percentage,
                            'grade': calculate_grade(score, max_score),
                            'formatted_grade': f"{score}/{max_score} ({percentage:.1f}%) - {calculate_grade(score, max_score)}",
                            'status': determine_status(score, student_id, set_id),
                            'invalid_answer': row.get('Invalid Ans list', ''),
                            'incorrect_answer': ', '.join(incorrect_answers_list) if incorrect_answers_list else '',
                            'scan_timestamp': csv_file  # Add this to track which scan this came from
                        })
                        
            except Exception as e:
                messages.error(request, f"Error reading results file {csv_file}: {str(e)}")
                print(f"Error details: {str(e)}")
    
    # Sort results by last name, first name for consistent display
    scan_results.sort(key=lambda x: (x['last_name'], x['first_name']))
    
    # Calculate overall statistics
    success_count = len([r for r in scan_results if r['status'] == 'success'])
    failed_exam_count = len([r for r in scan_results if r['status'] == 'failed_exam'])
    failed_processing_count = len([r for r in scan_results if r['status'] == 'failed_processing'])
    passing_grades = ['A+', 'A', 'B+', 'B', 'C']
    passing_count = len([r for r in scan_results if r['grade'] in passing_grades])
    failing_count = len([r for r in scan_results if r['grade'] == 'C-' or r['grade'] == 'D+' or r['grade'] == 'D' or r['grade'] == 'F'])
    
    # Add total number of scans processed
    total_scans = len(set([f for f in os.listdir(upload_dir) if f.startswith('Results_exam') and f.endswith('.csv')])) if os.path.exists(upload_dir) else 0
    
    context = {
        'current_class': current_class,
        'current_exam': current_exam,
        'scan_results': scan_results,
        'question_stats': question_stats,
        'scanned_count': len(scan_results),
        'success_count': success_count,
        'failed_exam_count': failed_exam_count,
        'failed_processing_count': failed_processing_count,
        'passing_count': passing_count,
        'failing_count': failing_count,
        'total_scans': total_scans,  # New context variable for number of scans
        'deleted_records_count': len(deleted_records),  # Count of deleted records
    }
    
    return render(request, 'scan_results.html', context)



@login_required
def delete_scan_result(request, class_id, exam_id, result_file, student_id):
    """Delete a specific scan result record"""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    # Verify the class and exam exist and belong to the current user
    current_class = get_object_or_404(Class, id=class_id, user=request.user)
    current_exam = get_object_or_404(Exam, id=exam_id, class_assigned=current_class)
    
    # Get the path to the deleted records file
    deleted_records_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 
                                     f'class_{class_id}', 
                                     f'exam_{exam_id}')
    deleted_records_file = os.path.join(deleted_records_dir, 'deleted_records.json')
    
    # Create directory if it doesn't exist
    os.makedirs(deleted_records_dir, exist_ok=True)
    
    # Load existing deleted records or initialize empty list
    deleted_records = []
    if os.path.exists(deleted_records_file):
        try:
            with open(deleted_records_file, 'r') as f:
                deleted_records = json.load(f)
        except json.JSONDecodeError:
            # Handle corrupted file
            deleted_records = []
    
    # Add the current record to the deleted list
    record_id = f"{result_file}|{student_id}"
    if record_id not in deleted_records:
        deleted_records.append(record_id)
        
        # Save updated deleted records
        with open(deleted_records_file, 'w') as f:
            json.dump(deleted_records, f)
        
        messages.success(request, "Record deleted successfully.")
    else:
        messages.info(request, "This record was already deleted.")
    
    return redirect('scan_results', class_id=class_id, exam_id=exam_id)

def export_results(request, class_id, exam_id):
    """
    Export all scan results to Excel, including duplicate student IDs
    """
    from openpyxl import Workbook
    from django.http import HttpResponse
    
    current_class = get_object_or_404(Class, id=class_id)
    current_exam = get_object_or_404(Exam, id=exam_id)
    
    # Define possible result folders
    possible_folders = [
        # Standard structure: class_XX/exam_YY/
        os.path.join(settings.MEDIA_ROOT, 'uploads', f'class_{class_id}', f'exam_{exam_id}'),
        # Alternative structure: class_XX_exam_YY/
        os.path.join(settings.MEDIA_ROOT, 'uploads', f'class_{class_id}_exam_{exam_id}')
    ]
    
    combined_data = []
    # CHANGED: Removed the processed_student_ids set to allow duplicates
    
    # Check each possible location
    for folder in possible_folders:
        if os.path.exists(folder):
            result_files = [f for f in os.listdir(folder) 
                          if f.startswith(f'Results_exam_{exam_id}_') and f.endswith('.csv')]
            
            # Process all result files
            for result_file in sorted(result_files):
                csv_path = os.path.join(folder, result_file)
                try:
                    with open(csv_path, 'r', encoding='utf-8') as file:
                        reader = csv.DictReader(file)
                        for row in reader:
                            # Add scan timestamp to row for reference
                            row_with_file = row.copy()
                            row_with_file['Scan File'] = result_file
                            combined_data.append(row_with_file)
                except Exception as e:
                    continue
    
    if not combined_data:
        messages.error(request, "No results found to export.")
        return redirect('scan_results', class_id=class_id, exam_id=exam_id)
    
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "All Scan Results"
        
        # Define the headers to export - include scan file information
        headers_to_export = ['Last Name', 'First Name', 'Middle Initial', 'ID', 'Set ID', 'Items', 'Max Score', 'Score', 'Scan File']
        ws.append(headers_to_export)
        
        # Write combined data to Excel
        for row in combined_data:
            ws.append([row.get(header, '') for header in headers_to_export])
        
        # Add a summary sheet
        ws2 = wb.create_sheet("Summary")
        ws2.append(['Total Records', len(combined_data)])
        ws2.append(['Total Scan Files', len(set(row['Scan File'] for row in combined_data))])
        
        # Count valid vs invalid student IDs
        valid_ids = len([row for row in combined_data if row.get('ID', 'N/A') != 'N/A' and row.get('ID', '').strip() != ''])
        invalid_ids = len(combined_data) - valid_ids
        ws2.append(['Valid Student IDs', valid_ids])
        ws2.append(['Invalid Student IDs', invalid_ids])
        
        # Prepare response
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=exam_{exam_id}_all_results.xlsx'
        wb.save(response)
        return response
        
    except Exception as e:
        messages.error(request, f"Error exporting results: {str(e)}")
        return redirect('scan_results', class_id=class_id, exam_id=exam_id)   
@login_required
def student_test_papers_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    test_sets = TestSet.objects.filter(student=student).select_related('exam').prefetch_related('exam__questions')

    return render(request, 'student_test_papers.html', {'student': student, 'test_sets': test_sets})



def validate_student_id(student_id):
    """
    Validate student ID to ensure it contains only alphanumeric characters.
    
    Args:
        student_id (str): The student ID to validate
    
    Raises:
        ValidationError: If the student ID contains spaces or special characters
    """
    if not re.match(r'^[a-zA-Z0-9]+$', student_id):
        raise ValidationError("Student ID must contain only letters and numbers, with no spaces or special characters.")

@login_required
def add_student_view(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        middle_initial = request.POST.get('middle_initial', '')
        student_id = request.POST.get('student_id', '').strip()

        try:
            # Validate student ID format: exactly 7 digits
            if not re.match(r'^\d{7}$', student_id):
                raise ValidationError("Student ID must be exactly 7 digits")

            # Check if the student ID already exists in the same class
            if Student.objects.filter(student_id=student_id, assigned_class=class_instance).exists():
                messages.warning(request, f"Student with ID {student_id} already exists in this class.")
                return redirect('class_detail', class_id=class_id)

            # Create the new student record with assigned_class
            Student.objects.create(
                student_id=student_id,
                first_name=first_name,
                last_name=last_name,
                middle_initial=middle_initial,
                assigned_class=class_instance
            )
            messages.success(request, f"Student {first_name} {last_name} added successfully!")
            return redirect('class_detail', class_id=class_id)
        
        except ValidationError as ve:
            messages.error(request, str(ve))
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

            # Initialize counters and lists
            successful_additions = 0
            existing_student_ids = []
            invalid_student_ids = []
            
            for row in reader:
                student_id = row.get('ID', '').strip()  # Ensure no leading/trailing whitespace
                first_name = row.get('First Name')
                last_name = row.get('Last Name')
                middle_initial = row.get('Middle Initial', '')

                try:
                    # Validate student ID format: exactly 7 digits
                    if not student_id or not re.match(r'^\d{7}$', student_id):
                        invalid_student_ids.append(student_id)
                        continue

                    # Check if the student already exists in the same class
                    if Student.objects.filter(student_id=student_id, assigned_class=class_instance).exists():
                        existing_student_ids.append(student_id)
                        continue  # Skip this student
                    
                    # Create the new student record
                    Student.objects.create(
                        student_id=student_id,
                        first_name=first_name,
                        last_name=last_name,
                        middle_initial=middle_initial,
                        assigned_class=class_instance
                    )
                    successful_additions += 1

                except ValidationError:
                    invalid_student_ids.append(student_id)
                except IntegrityError as e:
                    messages.error(request, f"Error creating student with ID {student_id}. Error: {str(e)}")
            
            # Success and info messages
            if successful_additions > 0:
                messages.success(request, f'Student bulk upload completed successfully! {successful_additions} students added.')
            else:
                messages.info(request, 'No new students were added during the bulk upload.')
            
            # Alert for existing and invalid student IDs
            if existing_student_ids:
                messages.info(request, f'Skipped {len(existing_student_ids)} existing student IDs: {", ".join(existing_student_ids)}')
            
            if invalid_student_ids:
                messages.warning(request, f'Skipped {len(invalid_student_ids)} invalid student IDs: {", ".join(invalid_student_ids)}')
                
            return redirect('class_detail', class_id=class_id)
    
    else:
        form = StudentBulkUploadForm()

    return render(request, 'bulk_upload_students.html', {
        'form': form,
        'class_instance': class_instance,
    })


@login_required
@require_http_methods(["GET", "POST"])
def edit_student(request, student_id):
    class_instance = request.GET.get('class_id')

    try:
        student = get_object_or_404(Student, student_id=student_id, assigned_class__id=class_instance)

        if request.method == "POST":
            # Get the new student ID
            new_student_id = request.POST.get('student_id', student.student_id).strip()
            
            try:
                # Validate student ID format: exactly 7 digits
                if not re.match(r'^\d{7}$', new_student_id):
                    raise ValidationError("Student ID must be exactly 7 digits")
                
                # Check for uniqueness only if the ID is being changed
                if new_student_id != student.student_id:
                    # Check if another student in the same class already has this ID
                    if Student.objects.filter(student_id=new_student_id, assigned_class__id=class_instance).exists():
                        messages.error(request, f"Student ID {new_student_id} already exists in this class.")
                        return redirect('edit_student', student_id=student_id, class_id=class_instance)
                
                # Update student details
                student.student_id = new_student_id
                student.first_name = request.POST.get('first_name', student.first_name)
                student.last_name = request.POST.get('last_name', student.last_name)
                student.middle_initial = request.POST.get('middle_initial', student.middle_initial)
                student.save()

                messages.success(request, "Student information updated successfully!")
                return redirect('class_detail', class_id=class_instance)
            
            except ValidationError as ve:
                messages.error(request, str(ve))
                return redirect('edit_student', student_id=student_id, class_id=class_instance)

        return render(request, 'edit_student.html', {
            'student': student,
            'class_id': class_instance,
        })

    except Student.DoesNotExist:
        messages.error(request, "Student not found.")
        return redirect('class_detail', class_id=class_instance)
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('class_detail', class_id=class_instance)

# @login_required
# def add_student_view(request, class_id):
#     class_instance = get_object_or_404(Class, id=class_id)

#     if request.method == 'POST':
#         first_name = request.POST.get('first_name')
#         last_name = request.POST.get('last_name')
#         middle_initial = request.POST.get('middle_initial', '')
#         student_id = request.POST.get('student_id', '').strip().lower()  # Convert to lowercase and remove whitespace

#         try:
#             # Validate student ID format: 2 letters + 9 digits
#             if not re.match(r'^[a-zA-Z]{2}\d{9}$', student_id):
#                 raise ValidationError("Student ID must be in format: xx123456789 (2 letters followed by 9 digits)")

#             # Check if the student ID already exists in the same class
#             if Student.objects.filter(student_id=student_id, assigned_class=class_instance).exists():
#                 messages.warning(request, f"Student with ID {student_id} already exists in this class.")
#                 return redirect('class_detail', class_id=class_id)

#             # Create the new student record with assigned_class and formatted student ID
#             Student.objects.create(
#                 student_id=student_id,  # Will be lowercase
#                 first_name=first_name,
#                 last_name=last_name,
#                 middle_initial=middle_initial,
#                 assigned_class=class_instance
#             )
#             messages.success(request, f"Student {first_name} {last_name} added successfully!")
#             return redirect('class_detail', class_id=class_id)
        
#         except ValidationError as ve:
#             messages.error(request, str(ve))
#             return redirect('class_detail', class_id=class_id)
#         except IntegrityError as e:
#             messages.error(request, f"Error creating student with ID {student_id}. Error: {str(e)}")
#             return redirect('class_detail', class_id=class_id)

#     return render(request, 'add_student.html', {
#         'class_instance': class_instance,
#     })

# @login_required
# def bulk_upload_students_view(request, class_id):
#     class_instance = get_object_or_404(Class, id=class_id)

#     if request.method == 'POST':
#         form = StudentBulkUploadForm(request.POST, request.FILES)
        
#         if form.is_valid():
#             csv_file = request.FILES['csv_file']
            
#             # Read the uploaded CSV file
#             decoded_file = csv_file.read().decode('utf-8').splitlines()
#             reader = csv.DictReader(decoded_file)

#             # Initialize counters and lists
#             successful_additions = 0
#             existing_student_ids = []
#             invalid_student_ids = []
            
#             for row in reader:
#                 student_id = row.get('ID', '').strip()  # Ensure no leading/trailing whitespace
#                 first_name = row.get('First Name')
#                 last_name = row.get('Last Name')
#                 middle_initial = row.get('Middle Initial', '')

#                 try:
#                     # Validate student ID format: 2 letters followed by 9 digits
#                     if not student_id or not re.match(r'^[a-zA-Z]{2}\d{9}$', student_id):
#                         invalid_student_ids.append(student_id)
#                         continue

#                     # Check if the student already exists in the same class
#                     if Student.objects.filter(student_id=student_id.lower(), assigned_class=class_instance).exists():
#                         existing_student_ids.append(student_id)
#                         continue  # Skip this student
                    
#                     # Create the new student record
#                     Student.objects.create(
#                         student_id=student_id,
#                         first_name=first_name,
#                         last_name=last_name,
#                         middle_initial=middle_initial,
#                         assigned_class=class_instance
#                     )
#                     successful_additions += 1

#                 except ValidationError:
#                     invalid_student_ids.append(student_id)
#                 except IntegrityError as e:
#                     messages.error(request, f"Error creating student with ID {student_id}. Error: {str(e)}")
            
#             # Success and info messages
#             if successful_additions > 0:
#                 messages.success(request, f'Student bulk upload completed successfully! {successful_additions} students added.')
#             else:
#                 messages.info(request, 'No new students were added during the bulk upload.')
            
#             # Alert for existing and invalid student IDs
#             if existing_student_ids:
#                 messages.info(request, f'Skipped {len(existing_student_ids)} existing student IDs: {", ".join(existing_student_ids)}')
            
#             if invalid_student_ids:
#                 messages.warning(request, f'Skipped {len(invalid_student_ids)} invalid student IDs: {", ".join(invalid_student_ids)}')
                
#             return redirect('class_detail', class_id=class_id)
    
#     else:
#         form = StudentBulkUploadForm()

#     return render(request, 'bulk_upload_students.html', {
#         'form': form,
#         'class_instance': class_instance,
#     })


# @login_required
# @require_http_methods(["GET", "POST"])
# def edit_student(request, student_id):
#     class_instance = request.GET.get('class_id')

#     try:
#         student = get_object_or_404(Student, student_id=student_id, assigned_class__id=class_instance)

#         if request.method == "POST":
#             # Get and format the new student ID
#             new_student_id = request.POST.get('student_id', student.student_id).strip().lower()
            
#             try:
#                 # Validate student ID format: 2 letters followed by 9 digits (e.g. xt202001241)
#                 if not re.match(r'^[a-zA-Z]{2}\d{9}$', new_student_id):
#                     raise ValidationError("Student ID must be in format: xx123456789 (2 letters followed by 9 digits)")
                
#                 # Check for uniqueness only if the ID is being changed
#                 if new_student_id != student.student_id:
#                     # Check if another student in the same class already has this ID
#                     if Student.objects.filter(student_id__iexact=new_student_id, assigned_class__id=class_instance).exists():
#                         messages.error(request, f"Student ID {new_student_id} already exists in this class.")
#                         return redirect('edit_student', student_id=student_id, class_id=class_instance)
                
#                 # Update student details
#                 student.student_id = new_student_id  # Store as lowercase
#                 student.first_name = request.POST.get('first_name', student.first_name)
#                 student.last_name = request.POST.get('last_name', student.last_name)
#                 student.middle_initial = request.POST.get('middle_initial', student.middle_initial)
#                 student.save()

#                 messages.success(request, "Student information updated successfully!")
#                 return redirect('class_detail', class_id=class_instance)
            
#             except ValidationError as ve:
#                 messages.error(request, str(ve))
#                 return redirect('edit_student', student_id=student_id, class_id=class_instance)

#         return render(request, 'edit_student.html', {
#             'student': student,
#             'class_id': class_instance,
#         })

#     except Student.DoesNotExist:
#         messages.error(request, "Student not found.")
#         return redirect('class_detail', class_id=class_instance)
#     except Exception as e:
#         messages.error(request, f"An error occurred: {str(e)}")
#         return redirect('class_detail', class_id=class_instance)

    
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
        # Handle password change if any password fields are filled
        password_changed = False
        if any(request.POST.get(field) for field in ['old_password', 'new_password1', 'new_password2']):
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                password_changed = True
            else:
                for error in password_form.errors.values():
                    messages.error(request, error[0])

        # Handle user information update
        user = request.user
        username = request.POST.get('username')
        email = request.POST.get('email')
        
        # Validate username
        if username and username != user.username:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username is already taken.')
            else:
                user.username = username

        # Validate email
        if email and email != user.email:
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email is already registered.')
            else:
                user.email = email

        # Save user if no errors occurred
        if not messages.get_messages(request):
            try:
                user.save()
                if password_changed:
                    messages.success(request, 'Your settings and password were successfully updated!')
                else:
                    messages.success(request, 'Your settings were successfully updated!')
            except Exception as e:
                messages.error(request, 'An error occurred while saving your settings.')

        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success' if not messages.get_messages(request) else 'error',
                'messages': [{
                    'tags': message.tags,
                    'message': str(message)
                } for message in messages.get_messages(request)]
            })

        return redirect('settings')

    context = {
        'user': request.user,
    }
    return render(request, 'settings.html', context)

@login_required
@require_http_methods(["POST"])
def delete_account_view(request):
    try:
        # Delete the user account
        user = request.user
        user.delete()
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'redirect': '/logout/'
            })
        
        messages.success(request, 'Your account has been successfully deleted.')
        return redirect('logout')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to delete account.'
            }, status=400)
        
        messages.error(request, 'Failed to delete account. Please try again.')
        return redirect('settings')

@login_required
@require_http_methods(['POST'])
def ajax_get_students(request):
    class_id = request.POST.get('class_id')
    students = Student.objects.filter(assigned_class_id=class_id).values('id', 'first_name', 'last_name', 'student_id', 'short_id')
    data = list(students)
    return JsonResponse(data, safe=False)

FAQ_RESPONSES = {
    # Authentication & Account
    'login': {
        'keywords': ['login', 'signin', 'sign in', 'access', 'cant login', "can't login"],
        'response': """To log in to your account:  
• Click the 'Login' button in the top right  
• Enter your username and password  
• Click 'Sign In'  

If you're having trouble:  
✔ Ensure caps lock is off  
✔ Check your username and password  
✔ Use the correct email address"""
    },

    'register': {
        'keywords': ['register', 'signup', 'sign up', 'create account', 'new account'],
        'response': """To create a new account:  
• Click 'Register' on the login page  
• Fill in your details  
• Create a strong password  
• Click 'Create Account'"""
    },

    # Classes
    'add_class': {
        'keywords': ['add class', 'create class', 'new class', 'how to add class', 'class name', 'unique class'],
        'response': """To add a new class:  
• Go to 'Classes' in the navigation  
• Click 'Add Class'  
• Fill in class details  
• Click 'Create'  

Tips for class names:  
✔ Include the school year (e.g., "Math 101 2023-2024")  
✔ Add section identifiers (e.g., "Physics 1A 2024")  
✔ Include semester/term if needed (e.g., "Chemistry 1st Sem 2024")"""
    },

    'delete_class': {
        'keywords': ['delete class', 'remove class', 'how to delete class'],
        'response': """To delete a class:  
• Go to 'Classes'  
• Open the class you want to delete  
• Click 'Delete'  
• Confirm deletion  

⚠ Warning: This action cannot be undone!"""
    },

    # Students
    'add_student': {
        'keywords': ['add student', 'new student', 'enroll student', 'how to add student', 'csv', 'student data', 'excel'],
        'response': """To add students using StudentDataEntry.csv:  

1. Download & Open CSV File  
• Download the StudentDataEntry.csv template  
• Open in Excel  

2. Enable Data Form Entry  
• Press **Alt + D, then O** to open the Data Form  
• If not working, add Data Form to Quick Access Toolbar:  
  ✔ Right-click ribbon → Customize Quick Access Toolbar  
  ✔ Choose "Commands Not in Ribbon"  
  ✔ Find and add "Form"  

3. Enter Student Data  
• Click "New" for each student  
• Fill in required fields  
• Click "OK" or press Enter  

4. Upload CSV File  
• Go to class details  
• Click 'Bulk Upload'  
• Select your saved CSV file  
• Click 'Upload'  

CSV Format:  
✔ ID: Student ID number  
✔ First Name: Student's first name  
✔ Last Name: Student's last name  
✔ Middle Initial: (optional)"""
    },

    # Exams
    'create_exam': {
        'keywords': ['create exam', 'add exam', 'new exam', 'make exam', 'how to create exam', 'exam name', 'unique exam'],
        'response': """To create a new exam:  
• Go to 'Exams'  
• Click 'Add Exam'  
• Select the class  
• Add exam details and questions  
• Click 'Create'  

Tips for unique exam names:  
✔ Include school year (e.g., "2023-2024")  
✔ Mention exam type (Midterm, Finals, Quiz)  
✔ Specify term/quarter (Q1, Q2, etc.)  

Example formats:  
- "Midterm_Math101_2024Q1"  
- "Finals_Physics_2024S1"  
- "Quiz1_Chemistry_2024Q2" """
    },

    # General Help
    'help': {
        'keywords': ['help', 'support', 'guide', 'tutorial', 'how to'],
        'response': """I can help you with:  

📌 Classes:  
• Adding/deleting classes  
• Managing students  
• Bulk uploads  
• Naming conventions  

📌 Exams:  
• Creating exams  
• Scanning papers  
• Grading  
• Viewing results  
• Naming conventions  

🔎 Try searching keywords like:  
- "Add class"  
- "Scan exam"  
- "Grade test" """
    },
     # Exam Management
    'delete_exam': {
        'keywords': ['delete exam', 'remove exam', 'how to delete exam'],
        'response': """To delete an exam:  
• Go to 'Exams'  
• Select the exam you want to delete  
• Click 'Delete' and confirm  

⚠ Warning: This action cannot be undone!"""
    },
    
    'edit_exam': {
        'keywords': ['edit exam', 'update exam', 'modify exam'],
        'response': """To edit an existing exam:  
• Go to 'Exams'  
• Click on the exam you want to edit  
• Make changes to details or questions  
• Click 'Save Changes'"""
    },

    'add_question': {
        'keywords': ['add question', 'new question', 'how to add question'],
        'response': """To add a question to an exam:  
• Go to 'Exam Details'  
• Click 'Add Question'  
• Enter the question and answer choices  
• Select the correct answer  
• Click 'Save'"""
    },

    'edit_question': {
        'keywords': ['edit question', 'modify question', 'update question'],
        'response': """To edit a question:  
• Go to 'Exam Details'  
• Click 'Edit' next to the question  
• Make the necessary changes  
• Click 'Save Changes'"""
    },

    'delete_question': {
        'keywords': ['delete question', 'remove question', 'how to delete question'],
        'response': """To delete a question:  
• Go to 'Exam Details'  
• Click 'Delete' next to the question  
• Confirm deletion  

⚠ Warning: This action cannot be undone!"""
    },

    # Scanning & Grading
    'scan_exam': {
        'keywords': ['scan exam', 'scan answer sheet', 'grading', 'how to scan exam'],
        'response': """To scan answer sheets:  
• Go to 'Scan Exam'  
• Upload the scanned image or PDF  
• Click 'Process'  
• View results in the 'Grading' section"""
    },

    'grade_exam': {
        'keywords': ['grade exam', 'check answers', 'grading system'],
        'response': """To grade an exam:  
• Scan answer sheets  
• The system will automatically match responses  
• View the graded results in 'Exam Reports'"""
    },

    # User & Settings
    'settings': {
        'keywords': ['settings', 'profile settings', 'account settings'],
        'response': """To update your account settings:  
• Go to 'Settings'  
• Edit your username, email, or password  
• Click 'Save Changes'"""
    },

    'delete_account': {
        'keywords': ['delete account', 'remove account', 'how to delete account'],
        'response': """To delete your account:  
• Go to 'Settings'  
• Click 'Delete Account'  
• Confirm deletion  

⚠ Warning: This action is irreversible!"""
    },
        'about_creators': {
        'keywords': ['creator', 'developer', 'who made this', 'about the creators'],
        'response': """This system was created by:  

👨‍💻 John Kent Evangelista  
👨‍💻 Joevincent Maderal  

They developed and designed this platform to help manage classes, exams, and automated grading efficiently.  

For inquiries or collaborations, feel free to reach out!"""
    }

}



@require_http_methods(["POST"])
@ensure_csrf_cookie
def chat_message(request):
    if not request.user.is_authenticated:
        return JsonResponse({'response': 'Please login to use the chat feature.'}, status=403)
        
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').lower().strip()
        
        if not user_message:
            return JsonResponse({'response': 'Please type a message.'}, status=400)
            
        response = find_faq_response(user_message)
        return JsonResponse({'response': response})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid message format.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'An error occurred. Please try again.'}, status=500)

def find_faq_response(message):
    """Find the most appropriate FAQ response based on keywords."""
    message = message.lower()
    
    # First check for exact matches
    for faq_item in FAQ_RESPONSES.values():
        if message in faq_item['keywords']:
            return faq_item['response']
    
    # Then check for keyword containment
    for faq_item in FAQ_RESPONSES.values():
        if any(keyword in message for keyword in faq_item['keywords']):
            return faq_item['response']
    
    # Default response if no matching keywords
    return """I can help you with:
• Classes - adding, managing students, bulk uploads
• Exams - creating, scanning, grading
• Account - login, registration

Try using keywords like 'add class', 'scan exam', or 'grade' to get specific help."""



@login_required
def add_instructions(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method == 'POST':
        instructions = request.POST.get('instructions')
        time_limit_str = request.POST.get('time_limit', '')
        
        # Update instructions
        exam.instructions = instructions
        
        # Handle time_limit field - explicitly check for empty string
        if time_limit_str.strip():
            try:
                exam.time_limit = int(time_limit_str)
            except ValueError:
                messages.error(request, 'Time limit must be a valid number.')
                return redirect('exam_detail', exam_id=exam_id)
        else:
            # Set to None when empty (not empty string)
            exam.time_limit = None
        
        # Save the exam with the updated fields
        exam.save()
        
        messages.success(request, 'Instructions updated successfully!')
        
        return redirect('exam_detail', exam_id=exam_id)
    
    return redirect('exam_detail', exam_id=exam_id)
