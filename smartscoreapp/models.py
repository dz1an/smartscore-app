from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
import random
from django.core.exceptions import ValidationError

def generate_student_code(exam_id):
    set_identifier = random.randint(0, 99)
    id_part = exam_id % 10000
    return f"{set_identifier:02d}-{id_part:04d}"

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

class Exam(models.Model):
    exam_id = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=50)
    class_assigned = models.ForeignKey(Class, related_name='exams', on_delete=models.CASCADE)
    questions = models.ManyToManyField('Question', related_name='exams')

    def __str__(self):
        return self.name

class Student(models.Model):
    first_name = models.CharField(max_length=50, default='')
    last_name = models.CharField(max_length=50, default='')
    middle_initial = models.CharField(max_length=1, blank=True, default='')
    student_id = models.CharField(max_length=7, unique=True, editable=False, default='')
    assigned_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='students')
    year = models.IntegerField()

    class Meta:
        unique_together = ('first_name', 'last_name', 'middle_initial', 'assigned_class')

    def save(self, *args, **kwargs):
        if not self.student_id:
            year_part = str(self.year)[-2:] 
            id_part = ''.join([str(random.randint(0, 9)) for _ in range(5)])  
            self.student_id = f"{year_part}{id_part}"
        super(Student, self).save(*args, **kwargs)



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
    set_no = models.IntegerField()
    set_id = models.CharField(max_length=8, unique=True)

    def save(self, *args, **kwargs):
        if not self.set_id:
            exam_id = str(self.exam.id).zfill(3)[:3]
            set_number = str(random.randint(0, 99)).zfill(2)
            random_digits = ''.join([str(random.randint(0, 9)) for _ in range(3)])
            self.set_id = f"{exam_id}{random_digits}{set_number}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.exam.name} - {self.student.first_name} {self.student.last_name} (Set {self.set_no}, ID: {self.set_id})"

# Specify unique related_name attributes for groups and user_permissions fields
User._meta.get_field('groups').remote_field.related_name = 'custom_user_groups'
User._meta.get_field('user_permissions').remote_field.related_name = 'custom_user_permissions'
