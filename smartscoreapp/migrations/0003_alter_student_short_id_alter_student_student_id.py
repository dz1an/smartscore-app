# Generated by Django 4.2.13 on 2024-08-03 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smartscoreapp', '0002_alter_student_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='short_id',
            field=models.CharField(blank=True, editable=False, max_length=8, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='student',
            name='student_id',
            field=models.CharField(max_length=12, unique=True),
        ),
    ]
