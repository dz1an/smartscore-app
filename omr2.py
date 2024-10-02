import utilis
import scan
import pandas as pd
import os
import datetime

current_time = datetime.datetime.now()

def omr(csv_path, images):
    # Define the expected headers
    expected_headers = ['Last Name', 'First Name', 'Middle Initial', 'ID', 'Exam ID', 'Answer Key']
    
    try:
        # Load the CSV file and validate headers
        df = load_and_validate_csv(csv_path, expected_headers)
        id_to_info = build_id_to_info(df)

        # Process image files
        image_file_paths = load_image_files(images)
        
        # Generate result CSV filename
        last_folder = os.path.basename(images)
        filename = os.path.join(images, f"Results_{last_folder}_{current_time.strftime('%Y-%m-%d_%H-%M-%S')}.csv")
        utilis.create_csv(filename)
        
        # Check if image paths and student data match
        if len(image_file_paths) != len(id_to_info):
            raise ValueError("Error: Mismatch between the number of images and the student data in CSV.")
        
        # Process each image
        for image_path in image_file_paths:
            process_image(image_path, id_to_info, filename)
        
        return filename

    except Exception as e:
        print(f"An error occurred: {e}")


def load_and_validate_csv(csv_path, expected_headers):
    """Load CSV and ensure headers match."""
    try:
        df = pd.read_csv(csv_path, dtype={'ID': str, 'Exam ID': str, 'Answer Key': str})
        if list(df.columns) != expected_headers:
            raise ValueError(f"CSV headers do not match the expected headers: {expected_headers}")
        print("CSV file loaded successfully with correct headers.")
        return df
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: The file at '{csv_path}' was not found.")
    except pd.errors.EmptyDataError:
        raise ValueError("Error: The file is empty.")
    except pd.errors.ParserError:
        raise ValueError("Error: There was an issue parsing the CSV file.")
    except Exception as e:
        raise e


def build_id_to_info(df):
    """Create a dictionary mapping IDs to personal information from CSV."""
    return {
        row['ID']: {
            'Last Name': row['Last Name'],
            'First Name': row['First Name'],
            'Middle Initial': row['Middle Initial'],
            'Exam ID': row['Exam ID'],
            'Answer Key': row['Answer Key']
        }
        for _, row in df.iterrows()
    }


def load_image_files(image_folder_path):
    """Load image files from a folder."""
    if not os.path.exists(image_folder_path):
        raise FileNotFoundError(f"Image folder not found: {image_folder_path}")

    image_files = utilis.get_image_files(image_folder_path)
    if not image_files:
        raise ValueError(f"No image files found in folder: {image_folder_path}")
    
    print(f"Found {len(image_files)} image files.")
    return image_files


def process_image(image_path, id_to_info, filename):
    """Process a single image and append results to the CSV."""
    try:
        cropStud, cropExam, cropAns = scan.rect_locator(image_path)
        
        # Student ID
        stud_id = utilis.int_list_to_string(scan.id_check(scan.id_scan(cropStud)))
        if stud_id not in id_to_info:
            raise ValueError(f"Error: Student ID {stud_id} not found in CSV data.")
        
        id_info = id_to_info[stud_id]
        
        # Exam ID
        exam_id = utilis.int_list_to_string(scan.exam_id_check(scan.exam_id_scan(cropExam)))
        exam_id_valid = utilis.are_strings_equal(id_info['Exam ID'], exam_id)

        # Answer checking
        score, invAns, incAns = scan.ans_check(scan.answer_scan(cropAns), id_info['Answer Key'])
        
        # Output student info and exam results
        additional_content = [
            id_info['Last Name'],
            id_info['First Name'],
            id_info['Middle Initial'],
            stud_id,
            exam_id_valid,
            score,
            invAns,
            incAns
        ]
        
        utilis.append_to_csv(additional_content, filename)
        print(f"Processed {stud_id}: Score = {score}, Invalid = {invAns}, Incorrect = {incAns}")
        print("-" * 40)
        
    except Exception as e:
        print(f"Failed to process image {image_path}: {e}")
