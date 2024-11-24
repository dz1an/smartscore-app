from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
import random

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

class Question(models.Model):
    ANSWER_CHOICES = [
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
        ('E', 'Option E'),
    ]

    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]

    question_text = models.CharField(max_length=255)
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255, blank=True, null=True)  # Optional
    option_d = models.CharField(max_length=255, blank=True, null=True)  # Optional
    option_e = models.CharField(max_length=255, blank=True, null=True)  # Optional
    answer = models.CharField(max_length=1, choices=ANSWER_CHOICES, default='A')  # Default answer A
    difficulty = models.CharField(max_length=6, choices=DIFFICULTY_CHOICES)  # Difficulty level

    def __str__(self):
        return self.question_text

    class Meta:
        ordering = ['difficulty']


class Exam(models.Model):
    exam_id = models.CharField(max_length=3, unique=True, editable=False)
    name = models.CharField(max_length=50)
    class_assigned = models.ForeignKey(Class, related_name='exams', on_delete=models.SET_NULL, null=True)  # Set to NULL on class deletion
    questions = models.ManyToManyField(Question, related_name='exams')
    set_id = models.CharField(max_length=6, unique=True, blank=True)  

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.exam_id:
            self.exam_id = self.generate_exam_id()
        
        if not self.set_id:
            self.set_id = self.generate_set_id()
        
        super().save(*args, **kwargs)

    def generate_exam_id(self):
        # Get the last used exam_id and increment it
        last_exam = Exam.objects.order_by('-exam_id').first()
        if last_exam and last_exam.exam_id.isdigit():
            next_id = int(last_exam.exam_id) + 1
        else:
            next_id = 1
        return str(next_id).zfill(3)  # Zero-fill to ensure 3 digits (e.g., 001, 002)

    def generate_set_id(self):
        # Generate two random digits
        random_digits = str(random.randint(0, 99)).zfill(2)  # Two-digit random number with leading zero if necessary
        return f"{self.exam_id}{random_digits}"  # Concatenate exam_id with the random digits


class Student(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    middle_initial = models.CharField(max_length=1, blank=True)
    student_id = models.CharField(max_length=12, blank=True)  # Not unique
    assigned_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='students', null=False)
    short_id = models.CharField(max_length=8, editable=False, null=True, blank=True)


    class Meta:
        unique_together = ('first_name', 'last_name', 'middle_initial', 'assigned_class', 'short_id')


    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = self.generate_student_id()
        # Ensure `student_id` is long enough to extract last 7 characters
        if len(self.student_id) >= 7:
            self.short_id = self.student_id[-7:]
        else:
            self.short_id = self.student_id  # If shorter, use the full student_id
        super(Student, self).save(*args, **kwargs)

    def generate_student_id(self):
        prefix = 'xt'
        random_digits = ''.join([str(random.randint(0, 9)) for _ in range(9)])
        return f"{prefix}{random_digits}"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.short_id})"


class ExamSet(models.Model):
    exam = models.ForeignKey(Exam, related_name='exam_sets', on_delete=models.CASCADE)
    set_number = models.IntegerField()
    students = models.ManyToManyField(Student, related_name='exam_sets')
    questions = models.ManyToManyField(Question, related_name='exam_sets', blank=True)  # New field for questions

    class Meta:
        unique_together = ('exam', 'set_number')

    def __str__(self):
        return f"{self.exam.name} - Set {self.set_number}"

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
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='correct_answer')
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
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    set_no = models.IntegerField()
    set_id = models.CharField(max_length=5, blank=True)  # Removed unique=True
    questions = models.ManyToManyField('Question', related_name='test_sets', blank=True)
    answer_key = models.CharField(max_length=255, blank=True)
    
    class Meta:
        unique_together = [['exam', 'student']]  # Ensure one test set per student per exam

    def save(self, *args, **kwargs):
        if not self.set_id:  # Check if set_id is not already set
            self.set_id = self.generate_set_id()
        super().save(*args, **kwargs)

    @classmethod
    def get_or_generate_common_set_id(cls, exam):
        """
        Get existing set ID for single set exam or generate a new one
        """
        exam_id = str(exam.exam_id).zfill(3)[:3]
        existing_set = cls.objects.filter(exam=exam).first()
        
        if existing_set:
            return existing_set.set_id
        
        set_number = str(random.randint(0, 99)).zfill(2)
        return f"{exam_id}{set_number}"

    @classmethod
    def generate_unique_set_id(cls, exam):
        """
        Generate a unique set ID for multiple sets exam
        """
        exam_id = str(exam.exam_id).zfill(3)[:3]
        used_set_ids = set(cls.objects.filter(exam=exam).values_list('set_id', flat=True))
        
        while True:
            set_number = str(random.randint(0, 99)).zfill(2)
            set_id = f"{exam_id}{set_number}"
            if set_id not in used_set_ids:
                return set_id

    def generate_set_id(self):
        """
        Fallback method for generating set ID
        """
        exam_id = str(self.exam.exam_id).zfill(3)[:3]
        set_number = str(random.randint(0, 99)).zfill(2)
        return f"{exam_id}{set_number}"

    def __str__(self):
        return f"{self.exam.name} - {self.student.first_name} {self.student.last_name} (Set {self.set_no}, ID: {self.set_id})"

# Specify unique related_name attributes for groups and user_permissions fields
User._meta.get_field('groups').remote_field.related_name = 'custom_user_groups'
User._meta.get_field('user_permissions').remote_field.related_name = 'custom_user_permissions'

class ImageProcessingTask(models.Model):
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE)
    exam_id = models.ForeignKey(Exam, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='queued')  # 'queued', 'in_progress', 'completed'
    result_csv = models.FileField(upload_to='csv_results/', null=True, blank=True)

    def __str__(self):
        return f"Task {self.id} - {self.status}"
