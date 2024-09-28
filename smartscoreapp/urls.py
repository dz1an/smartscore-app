from django.contrib import admin
from django.urls import path
from smartscoreapp.views import (
    index, login_view, register_view, registered_users_view,
    classes_view, class_detail_view, exams_view, exam_detail_view,
    logout_view, add_class_view, add_student_view, add_exam_view,
    add_student_to_exam_view, settings_view, edit_student,
    update_class_name_view, students_view, delete_class_view, edit_question_view, delete_question_view,
    select_questions_view, generate_test_paper_view, print_test_paper_view, process_scanned_papers_view,
    generate_questionnaire_view, list_classes_view, class_exams_view, save_test_paper_view, student_test_papers_view,
    view_test_set_view, grade_exam_view, bulk_upload_students_view, scan_exam_view, scan_page, generate_exam_sets 
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
    path('classes/<int:class_id>/add_student/', add_student_view, name='add_student'),
    
    
    

    # Students
    path('students/', students_view, name='students'),
    path('students/<str:student_id>/edit/', views.edit_student, name='edit_student'),  # Changed to str
    path('students/<str:student_id>/delete/', views.delete_student, name='delete_student'),  # Changed to str
    path('students/<int:student_id>/test_papers/', student_test_papers_view, name='student_test_papers'),
    path('test_set/<int:test_set_id>/', view_test_set_view, name='view_test_set'),
    path('classes/<int:class_id>/bulk_upload/', bulk_upload_students_view, name='bulk_upload_students'),
    
    # Exams
    path('exams/', exams_view, name='exams'),
    path('exams/add/', add_exam_view, name='add_exam'),
    path('exams/<int:exam_id>/', exam_detail_view, name='exam_detail'),
    path('exams/<int:exam_id>/add_student/', add_student_to_exam_view, name='add_student_to_exam'),
    path('exams/<int:exam_id>/delete/', views.delete_exam, name='delete_exam'),
    path('exams/<int:exam_id>/add_question/', views.add_question_view, name='add_question'),
    path('edit_question/<int:question_id>/', edit_question_view, name='edit_question'),
    path('delete_question/<int:question_id>/', delete_question_view, name='delete_question'),
    path('exams/<int:exam_id>/select_questions/', select_questions_view, name='select_questions'),
    path('exams/<int:exam_id>/generate-test-paper/', generate_test_paper_view, name='generate_test_paper'),
    path('exams/<int:exam_id>/print-test-paper/', print_test_paper_view, name='print_test_paper'),
    path('process-scanned-papers/', process_scanned_papers_view, name='process_scanned_papers'),

    path('generate_questionnaire/<int:exam_id>/<int:student_id>/', generate_questionnaire_view, name='generate_questionnaire'),
    path('list_classes/', list_classes_view, name='list_classes'),
    path('class_exams/<int:class_id>/', class_exams_view, name='class_exams'),
    path('exams/<int:exam_id>/save_test_paper/', save_test_paper_view, name='save_test_paper'),

    # Grading
    path('grade_exam/<int:exam_id>/<int:student_id>/', grade_exam_view, name='grade_exam'),

    #scan
    path('scan_exam/', scan_exam_view, name='scan_exam_view'),
    path('exams/<int:class_id>/<int:exam_id>/scan/', scan_page, name='scan_page'),
    path('exam/generate-sets/<int:class_id>/<int:exam_id>/', views.generate_exam_sets, name='generate_sets'),

    




    # Settings
    path('settings/', settings_view, name='settings'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
