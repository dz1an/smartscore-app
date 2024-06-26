from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'


class Class(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Student(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    class_assigned = models.ForeignKey(
        Class, related_name='students', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Exam(models.Model):
    name = models.CharField(max_length=100)
    class_assigned = models.ForeignKey(
        Class, related_name='exams', on_delete=models.CASCADE)
    date = models.DateField()

    def __str__(self):
        return self.name


class Question(models.Model):
    exam = models.ForeignKey(
        Exam, related_name='questions', on_delete=models.CASCADE)
    question_text = models.TextField()
    correct_answer = models.CharField(max_length=10)

    def __str__(self):
        return self.question_text



# Specify unique related_name attributes for groups and user_permissions fields
User._meta.get_field('groups').remote_field.related_name = 'custom_user_groups'
User._meta.get_field('user_permissions').remote_field.related_name = 'custom_user_permissions'