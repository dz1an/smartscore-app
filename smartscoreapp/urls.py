from django.contrib import admin
from django.urls import path
from smartscoreapp.views import (
    index, login_view, register_view, registered_users_view,
    classes_view, class_detail_view, exams_view, exam_detail_view,
    logout_view, add_class_view, add_student_view, add_exam_view, add_student_to_exam_view, settings_view
)
from django.conf.urls.static import static
from django.conf import settings
from . import views 



urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', register_view, name='register'),
    path('', login_view, name='login'),
    path('index/', index, name='index'),
    path('logout/', logout_view, name='logout'),
    path('registered-users/', registered_users_view, name='registered_users'),
    path('classes/', classes_view, name='classes'),
    path('add-class/', add_class_view, name='add_class'),
    path('classes/<int:class_id>/', class_detail_view, name='class_detail'),
    path('add_student/<int:class_id>/', add_student_view, name='add_student'),
    path('students/', views.students_view, name='students'),
    path('exams/', exams_view, name='exams'),
    path('exams/<int:exam_id>/', exam_detail_view, name='exam_detail'),
    path('add_exam/', add_exam_view, name='add_exam'),
    path('add_student_to_exam/<int:exam_id>/', add_student_to_exam_view, name='add_student_to_exam'),
    path('settings/', settings_view, name='settings'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
