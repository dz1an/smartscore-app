# Generated by Django 4.2.16 on 2024-10-01 13:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smartscoreapp', '0005_alter_student_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='student_id',
            field=models.CharField(blank=True, max_length=12),
        ),
    ]