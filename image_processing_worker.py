# image_processing_worker.py
import os
import django
import time
from smartscoreapp.models import ImageProcessingTask, Class, Exam
from django.conf import settings
from omr2 import omr  # Import your existing image processing function

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartscoreapp.settings")
django.setup()

def process_task(task):
    """Process an image processing task."""
    current_class = task.class_id
    current_exam = task.exam_id
    base_upload_path = os.path.join('uploads', f'class_{current_class.id}', f'exam_{current_exam.id}')
    absolute_upload_path = os.path.join(settings.MEDIA_ROOT, base_upload_path)
    
    # Path to CSV file (ensure it exists)
    csv_file = os.path.join(settings.MEDIA_ROOT, 'csv', f'class_{current_class.id}', f'exam_{current_exam.id}_sets.csv')
    
    if not os.path.exists(csv_file):
        task.status = 'failed'
        task.save()
        print(f"CSV file {csv_file} not found.")
        return

    try:
        # Call your OMR function
        result_csv = omr(csv_file, absolute_upload_path)

        if result_csv and os.path.exists(result_csv):
            task.result_csv = result_csv  # Save the path to the result
            task.status = 'completed'
        else:
            task.status = 'failed'

    except Exception as e:
        task.status = 'failed'
        print(f"Error processing task {task.id}: {str(e)}")
    
    task.save()  # Update task status in the database

def run_image_processing_worker():
    """Continuously check for tasks to process."""
    while True:
        tasks = ImageProcessingTask.objects.filter(status="queued")
        for task in tasks:
            task.status = "in_progress"
            task.save()
            process_task(task)
        time.sleep(10)  # Sleep before checking again

if __name__ == "__main__":
    run_image_processing_worker()  # Start the worker process
