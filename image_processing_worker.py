# image_processing_worker.py
import os
import time
import django
from django.conf import settings

# Initialize Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartscoreapp.settings")
django.setup()

from smartscoreapp.models import ImageProcessingTask
from omr2 import omr  # Assuming omr() is in your app

def process_images():
    while True:
        # Query for tasks in the 'queued' status
        task = ImageProcessingTask.objects.filter(status='queued').first()

        if task:
            try:
                task.status = 'in_progress'
                task.save()

                # Call OMR with the paths from the task
                result_csv = omr(task.result_csv.name, task.class_id.upload_path)

                # Update task status
                task.result_csv = result_csv
                task.status = 'completed'
                task.save()

                print(f"Task {task.id} completed successfully.")
            except Exception as e:
                task.status = 'failed'
                task.save()
                print(f"Task {task.id} failed: {str(e)}")

        time.sleep(10)  # Check every 10 seconds for new tasks

if __name__ == "__main__":
    process_images()
