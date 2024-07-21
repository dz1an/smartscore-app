from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils.crypto import get_random_string

def generate_student_id():
    return 'TEMP_' + get_random_string(8)

class User(AbstractUser):
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

class Class(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Student(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=20, unique=True, default=generate_student_id)
    year = models.IntegerField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    assigned_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='students')

    def __str__(self):
        return f"{self.name} ({self.student_id})"
    

class Exam(models.Model):
    exam_id = models.CharField(max_length=50, unique=True)  # Add this if you need it
    name = models.CharField(max_length=100)
    class_assigned = models.ForeignKey(Class, related_name='exams', on_delete=models.CASCADE)
    date = models.DateField()
    questions = models.ManyToManyField('Question', related_name='exams')

    def __str__(self):
        return self.name
    
class ExamSet(models.Model):
    exam = models.ForeignKey(Exam, related_name='exam_sets', on_delete=models.CASCADE)
    set_number = models.IntegerField()
    students = models.ManyToManyField(Student, related_name='exam_sets')

    class Meta:
        unique_together = ('exam', 'set_number')

    def __str__(self):
        return f"{self.exam.name} - Set {self.set_number}"

class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    question_text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    option_e = models.CharField(max_length=255)
    question_order = models.IntegerField(default=1)

    def __str__(self):
        return self.question_text

class StudentQuestion(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='student_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student_answer = models.CharField(max_length=1, choices=[
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
        ('E', 'Option E')
    ], null=True, blank=True)
    
    class Meta:
        unique_together = ('student', 'question', 'exam')

class Answer(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='answer')
    answer = models.CharField(max_length=1, choices=[
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
        ('E', 'Option E')
    ])
    option_a_value = models.IntegerField(default=0)
    option_b_value = models.IntegerField(default=1)
    option_c_value = models.IntegerField(default=2)
    option_d_value = models.IntegerField(default=3)
    option_e_value = models.IntegerField(default=4)

    def __str__(self):
        return f"Answer for: {self.question.question_text[:50]}..."
    

class TestSet(models.Model):
    exam = models.ForeignKey(Exam, related_name='test_sets', on_delete=models.CASCADE)
    student = models.ForeignKey(Student, related_name='test_sets', on_delete=models.CASCADE)
    set_no = models.IntegerField()  # Set number to identify the exam set for the student

    def __str__(self):
        return f"{self.exam.name} - {self.student.name} (Set {self.set_no})"

# Specify unique related_name attributes for groups and user_permissions fields
User._meta.get_field('groups').remote_field.related_name = 'custom_user_groups'
User._meta.get_field('user_permissions').remote_field.related_name = 'custom_user_permissions'
