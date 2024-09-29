# Generated by Django 4.2.16 on 2024-09-28 16:13

from django.conf import settings
import django.contrib.auth.models
import django.contrib.auth.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Class',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Exam',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('exam_id', models.CharField(editable=False, max_length=3, unique=True)),
                ('name', models.CharField(max_length=50)),
                ('set_id', models.CharField(blank=True, max_length=9, unique=True)),
                ('class_assigned', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exams', to='smartscoreapp.class')),
            ],
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_text', models.CharField(max_length=255)),
                ('option_a', models.CharField(max_length=255)),
                ('option_b', models.CharField(max_length=255)),
                ('option_c', models.CharField(max_length=255)),
                ('option_d', models.CharField(max_length=255)),
                ('option_e', models.CharField(max_length=255)),
                ('answer', models.CharField(choices=[('A', 'Option A'), ('B', 'Option B'), ('C', 'Option C'), ('D', 'Option D'), ('E', 'Option E')], default='A', max_length=1)),
            ],
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=50)),
                ('last_name', models.CharField(max_length=50)),
                ('middle_initial', models.CharField(blank=True, max_length=1)),
                ('student_id', models.CharField(max_length=12, unique=True)),
                ('short_id', models.CharField(blank=True, editable=False, max_length=8, null=True, unique=True)),
                ('assigned_class', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='students', to='smartscoreapp.class')),
            ],
            options={
                'unique_together': {('first_name', 'last_name', 'middle_initial', 'assigned_class', 'student_id')},
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='TestSet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('set_no', models.IntegerField()),
                ('set_id', models.CharField(editable=False, max_length=8, unique=True)),
                ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_sets', to='smartscoreapp.exam')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_sets', to='smartscoreapp.student')),
            ],
        ),
        migrations.AddField(
            model_name='exam',
            name='questions',
            field=models.ManyToManyField(related_name='exams', to='smartscoreapp.question'),
        ),
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answer', models.CharField(choices=[('A', 'Option A'), ('B', 'Option B'), ('C', 'Option C'), ('D', 'Option D'), ('E', 'Option E')], max_length=1)),
                ('option_a_value', models.IntegerField(default=0)),
                ('option_b_value', models.IntegerField(default=1)),
                ('option_c_value', models.IntegerField(default=2)),
                ('option_d_value', models.IntegerField(default=3)),
                ('option_e_value', models.IntegerField(default=4)),
                ('question', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='correct_answer', to='smartscoreapp.question')),
            ],
        ),
        migrations.CreateModel(
            name='StudentQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student_answer', models.CharField(blank=True, choices=[('A', 'Option A'), ('B', 'Option B'), ('C', 'Option C'), ('D', 'Option D'), ('E', 'Option E')], max_length=1, null=True)),
                ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='smartscoreapp.exam')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='smartscoreapp.question')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_questions', to='smartscoreapp.student')),
            ],
            options={
                'unique_together': {('student', 'question', 'exam')},
            },
        ),
        migrations.CreateModel(
            name='ExamSet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('set_number', models.IntegerField()),
                ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exam_sets', to='smartscoreapp.exam')),
                ('questions', models.ManyToManyField(blank=True, related_name='exam_sets', to='smartscoreapp.question')),
                ('students', models.ManyToManyField(related_name='exam_sets', to='smartscoreapp.student')),
            ],
            options={
                'unique_together': {('exam', 'set_number')},
            },
        ),
    ]