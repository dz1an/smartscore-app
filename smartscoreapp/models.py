from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

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
    year = models.IntegerField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    assigned_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='students')

    def __str__(self):
        return self.name

class Exam(models.Model):
    name = models.CharField(max_length=100)
    class_assigned = models.ForeignKey(Class, related_name='exams', on_delete=models.CASCADE)
    date = models.DateField()
    exam_id = models.CharField(max_length=50, unique=True)  # Unique identifier for each exam set
    questions = models.ManyToManyField('Question', related_name='exams')  # Specify a custom related_name

    def __str__(self):
        return self.name

class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    question_text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    option_e = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=1, choices=[
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
    question_order = models.IntegerField(default=1)  #

    def __str__(self):
        return self.question_text


    def __str__(self):
        return self.question_text

class TestSet(models.Model):
    exam = models.ForeignKey(Exam, related_name='test_sets', on_delete=models.CASCADE)
    student = models.ForeignKey(Student, related_name='test_sets', on_delete=models.CASCADE)
    set_no = models.IntegerField()  # Set number to identify the exam set for the student

    def __str__(self):
        return f"{self.exam.name} - {self.student.name} (Set {self.set_no})"

# Specify unique related_name attributes for groups and user_permissions fields
User._meta.get_field('groups').remote_field.related_name = 'custom_user_groups'
User._meta.get_field('user_permissions').remote_field.related_name = 'custom_user_permissions'
