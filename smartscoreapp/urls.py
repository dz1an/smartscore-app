from django.contrib import admin
from django.urls import path
from smartscoreapp.views import (
    index, login_view, register_view, registered_users_view,
    classes_view, class_detail_view, exams_view, exam_detail_view,
    logout_view, add_class_view, add_student_view, add_exam_view,
    add_student_to_exam_view, settings_view, edit_student,
    update_class_name_view, students_view, delete_class_view, edit_question_view,delete_question_view,
    select_questions_view
)
from django.conf.urls.static import static
from django.conf import settings
from . import views 

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication
    path('register/', register_view, name='register'),
    path('', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # Home
    path('index/', index, name='index'),

    # Users
    path('registered-users/', registered_users_view, name='registered_users'),

    # Classes
    path('classes/', classes_view, name='classes'),
    path('classes/<int:class_id>/', class_detail_view, name='class_detail'),
    path('classes/add/', add_class_view, name='add_class'),
    path('classes/<int:class_id>/delete/', delete_class_view, name='delete_class'),
    path('classes/<int:class_id>/update/', update_class_name_view, name='update_class_name'),
    path('classes/<int:class_id>/add_student/', views.add_student_view, name='add_student'),
    

    # Students
    path('students/', students_view, name='students'),
    path('students/<int:student_id>/edit/', views.edit_student, name='edit_student'),
    path('students/<int:student_id>/delete/', views.delete_student, name='delete_student'),

    
    # Exams
    path('exams/', exams_view, name='exams'),
    path('exams/<int:exam_id>/', exam_detail_view, name='exam_detail'),
    path('exams/add/', add_exam_view, name='add_exam'),
    path('exams/<int:exam_id>/add_student/', add_student_to_exam_view, name='add_student_to_exam'),
    path('exams/<int:exam_id>/delete/', views.delete_exam, name='delete_exam'),
    path('exams/', views.exams_view, name='exams'),
    path('exams/<int:exam_id>/add_question/', views.add_question_view, name='add_question'),
    path('edit_question/<int:question_id>/', edit_question_view, name='edit_question'),
    path('delete_question/<int:question_id>/', delete_question_view, name='delete_question'),
    path('exams/<int:exam_id>/select-questions/', select_questions_view, name='select_questions'),
    path('exams/<int:exam_id>/generate-test-paper/', views.generate_test_paper_view, name='generate_test_paper'),
    path('exams/<int:exam_id>/print-test-paper/', views.print_test_paper_view, name='print_test_paper'),
    path('process-scanned-papers/', views.process_scanned_papers_view, name='process_scanned_papers'),

    
 # Delete Question
    path('exams/<int:exam_id>/delete_question/<int:question_id>/', views.delete_question_view, name='delete_question'),
    
     

    # Settings
    path('settings/', settings_view, name='settings'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)