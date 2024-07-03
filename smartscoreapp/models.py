from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

class Class(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(default="No description provided")
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Add this line

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

    def __str__(self):
        return self.name

class Question(models.Model):
    exam = models.ForeignKey(Exam, related_name='questions', on_delete=models.CASCADE)
    question_text = models.TextField()
    correct_answer = models.CharField(max_length=10)

    def __str__(self):
        return self.question_text

class TestSet(models.Model):
    exam = models.ForeignKey(Exam, related_name='test_sets', on_delete=models.CASCADE)
    student = models.ForeignKey(Student, related_name='test_sets', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # Name or identifier for the test set

    def __str__(self):
        return f"{self.exam.name} - {self.student.name} ({self.name})"

# Specify unique related_name attributes for groups and user_permissions fields
User._meta.get_field('groups').remote_field.related_name = 'custom_user_groups'
User._meta.get_field('user_permissions').remote_field.related_name = 'custom_user_permissions'
