from django.contrib import admin
from django.urls import path
from smartscoreapp.views import (
    index, login_view, register_view, registered_users_view, download_exam_sets_csv,
    classes_view, class_detail_view, exams_view, exam_detail_view, scan_results_view, 
    logout_view, add_class_view, add_student_view, add_exam_view, delete_account_view,
    add_student_to_exam_view, settings_view, edit_student, delete_student_view,
    update_class_name_view, students_view, delete_class_view, edit_question_view, delete_question_view,
    select_questions_view,  process_scanned_papers_view,
    generate_questionnaire_view, list_classes_view, class_exams_view, 
    view_test_set_view, grade_exam_view, bulk_upload_students_view, scan_exam_view, scan_page, generate_exam_sets, download_test_paper
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
    path('delete_account/', delete_account_view, name='delete_account'),

    # Classes
    path('classes/', classes_view, name='classes'),
    path('classes/<int:class_id>/', class_detail_view, name='class_detail'),
    path('classes/add/', add_class_view, name='add_class'),
    path('classes/<int:class_id>/delete/', delete_class_view, name='delete_class'),
    path('classes/<int:class_id>/update/', update_class_name_view, name='update_class_name'),
    path('classes/<int:class_id>/add_student/', add_student_view, name='add_student'),
    
    
    

    # Students
    path('students/', students_view, name='students'),
    path('edit-student/<str:student_id>/', edit_student, name='edit_student'), 

    path('test_set/<int:test_set_id>/', view_test_set_view, name='view_test_set'),
    path('classes/<int:class_id>/bulk_upload/', bulk_upload_students_view, name='bulk_upload_students'),
# Only keeping the delete path under class context
    path('classes/<int:class_id>/students/<str:student_id>/delete/', views.delete_student_view, name='delete_student'),
    path('classes/<int:class_id>/students/<int:student_id>/delete/', delete_student_view, name='delete_student'),
    
    
    # Exams
    path('exams/', exams_view, name='exams'),
    path('exams/add/', add_exam_view, name='add_exam'),
    path('exams/<int:exam_id>/', exam_detail_view, name='exam_detail'),
    path('exams/<int:exam_id>/add_student/', add_student_to_exam_view, name='add_student_to_exam'),
    path('exams/<int:exam_id>/delete/', views.delete_exam, name='delete_exam'),
    path('exams/<int:exam_id>/add_question/', views.add_question_view, name='add_question'),
    path('exams/<int:exam_id>/add_instructions/', views.add_instructions, name='add_instructions'),

    path('student_test_papers/<int:student_id>/', views.student_test_papers_view, name='student_test_papers'),
    path('delete_question/<int:question_id>/', delete_question_view, name='delete_question'),
    path('exams/<int:exam_id>/select_questions/', select_questions_view, name='select_questions'),


    path('process-scanned-papers/', process_scanned_papers_view, name='process_scanned_papers'),
    path('edit_question/<int:question_id>/', views.edit_question_view, name='edit_question'),
    path('delete-test-set/<int:test_set_id>/', views.delete_test_set, name='delete_test_set'),



    path('generate_questionnaire/<int:exam_id>/<int:student_id>/', generate_questionnaire_view, name='generate_questionnaire'),
    path('list_classes/', list_classes_view, name='list_classes'),
    path('class_exams/<int:class_id>/', class_exams_view, name='class_exams'),
    path('exam/<int:exam_id>/download-answer-sheet/', views.download_answer_sheet, name='download_answer_sheet'),

    # Grading
    path('grade_exam/<int:exam_id>/<int:student_id>/', grade_exam_view, name='grade_exam'),

    #scan
    path('scan_exam/', scan_exam_view, name='scan_exam_view'),
    path('exams/<int:class_id>/<int:exam_id>/scan/', scan_page, name='scan_page'),
    path('exam/generate-sets/<int:class_id>/<int:exam_id>/', generate_exam_sets, name='generate_exam_sets'),
    path('exams/<int:class_id>/<int:exam_id>/generate-sets/', generate_exam_sets, name='generate_sets'),
    path('exams/<int:class_id>/<int:exam_id>/generate-sets/', generate_exam_sets, name='generate_exam_sets'),
    path('exams/<int:class_id>/<int:exam_id>/download_test_paper/', download_test_paper, name='download_test_paper'),
    path('scan/<int:class_id>/<int:exam_id>/remove_image/<str:image_name>/', views.remove_image, name='remove_image'),
    path('exams/<int:class_id>/<int:exam_id>/scan/', views.scan_page, name='scan_page'),
    path('exams/<int:class_id>/<int:exam_id>/remove-image/<str:image_name>/',views.remove_image, name='remove_image'), 


    path('exams/<int:class_id>/<int:exam_id>/scan-results/', views.scan_results_view, name='scan_results'),
    path('class/<int:class_id>/exam/<int:exam_id>/export/', views.export_results, name='export_results'),
    path('exams/<int:class_id>/<int:exam_id>/scan/', scan_page, name='scan_page'),
    
    # Exam Sets and Test Paper Generation
    path('exams/<int:class_id>/<int:exam_id>/generate-sets/', generate_exam_sets, name='generate_sets'),
    path('exams/<int:class_id>/<int:exam_id>/download_test_paper/', download_test_paper, name='download_test_paper'),
    
    # Scan Results
    path('exams/<int:class_id>/<int:exam_id>/scan-results/', scan_results_view, name='scan_results'),

    path('api/delete-account/', views.delete_account_view, name='delete_account'),

    path('class/<int:class_id>/exam/<int:exam_id>/delete_result/<str:result_file>/<str:student_id>/', views.delete_scan_result, name='delete_scan_result'),
    # Settings
    path('settings/', settings_view, name='settings'),
    path('chat/message/', views.chat_message, name='chat_message'),
    path('class/<int:class_id>/exam/<int:exam_id>/download-exam-sets/', views.download_exam_sets_csv, name='download_exam_sets_csv'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


