import cv2
import numpy as np
import os
import csv
import glob
# from tkinter import Tk, filedialog

def stackImages(scale,imgArray):
    """
    Stacks a list of images into a single image.

    Parameters:
    scale (float): Scaling factor for resizing images. A value of 1.0 means no resizing, less than 1.0 will shrink the image, and greater than 1.0 will enlarge it.
    imgArray (list): A 2D list of images (each element being a list of images) or a 1D list of images. Each image should be a NumPy array (e.g., from cv2.imread).

    Returns:
    numpy.ndarray: A single image containing the stacked images, either horizontally and vertically combined.

    """
    rows = len(imgArray)
    cols = len(imgArray[0])
    rowsAvailable = isinstance(imgArray[0], list)
    width = imgArray[0][0].shape[1]
    height = imgArray[0][0].shape[0]
    if rowsAvailable:
        for x in range ( 0, rows):
            for y in range(0, cols):
                if imgArray[x][y].shape[:2] == imgArray[0][0].shape [:2]:
                    imgArray[x][y] = cv2.resize(imgArray[x][y], (0, 0), None, scale, scale)
                else:
                    imgArray[x][y] = cv2.resize(imgArray[x][y], (imgArray[0][0].shape[1], imgArray[0][0].shape[0]), None, scale,scale)
                if len(imgArray[x][y].shape) == 2: imgArray[x][y] = cv2.cvtColor(imgArray[x][y], cv2.COLOR_GRAY2BGR)
        imageBlank = np.zeros((height, width, 3), np.uint8)
        hor = [imageBlank]*rows
        hor_con = [imageBlank]*rows
        for x in range(0, rows):
            hor[x] = np.hstack(imgArray[x])
        ver = np.vstack(hor)
    else:
        for x in range(0, rows):
            if imgArray[x].shape[:2] == imgArray[0].shape[:2]:
                imgArray[x] = cv2.resize(imgArray[x], (0, 0), None, scale, scale)
            else:
                imgArray[x] = cv2.resize(imgArray[x], (imgArray[0].shape[1], imgArray[0].shape[0]), None, scale, scale)
            if len(imgArray[x].shape) == 2: imgArray[x] = cv2.cvtColor(imgArray[x], cv2.COLOR_GRAY2BGR)
        hor = np.hstack(imgArray)
        ver = hor
    return ver

def rectContour(contours):
    """
    Filters and sorts contours in an image to find those that approximate rectangles.

    Args:
        contours (list of numpy.ndarray): A list of contour arrays, where each contour
            is represented as a numpy array of points.

    Returns:
        list of numpy.ndarray: A list of contours that approximate rectangles, sorted
            by their area in descending order. Each contour is represented as a numpy
            array of points.
    """
    rectCon = []
    for i in contours:
        area = cv2.contourArea(i)
        if area>50:
            peri = cv2.arcLength(i, True)
            approx = cv2.approxPolyDP(i,0.02*peri,True)
            # print("Corner points: ", len(approx))
            if len(approx)==4:
                rectCon.append(i)
    rectCon = sorted(rectCon,key=cv2.contourArea, reverse=True)

    return rectCon

def getCornerPoints(cont):
    """
    Extracts and approximates the corner points of a contour.

    This function approximates the polygonal curves of a contour and returns the
    corner points of the contour. It uses the `cv2.approxPolyDP` function to
    approximate the contour to a polygon and returns the points of the approximated
    polygon.

    Args:
        cont (numpy.ndarray): A numpy array of contour points, where the contour is
            represented as a sequence of points.

    Returns:
        numpy.ndarray: An array of points representing the approximated corner points
            of the contour. The array is in the format of (N, 1, 2), where N is the
            number of vertices in the approximated polygon.
    """
    peri = cv2.arcLength(cont, True)
    approx = cv2.approxPolyDP(cont,0.02*peri,True)
    return approx

def reorder(mypoints):
    """
    Reorders four corner points of a quadrilateral to a standard sequence.

    Args:
        mypoints (numpy.ndarray): An array of shape (4, 2) containing four points
            representing the corners of a quadrilateral. Each point is a pair of
            coordinates (x, y).

    Returns:
        numpy.ndarray: An array of shape (4, 1, 2) containing the reordered points
            in the sequence: top-left, top-right, bottom-right, bottom-left.
    """

    mypoints = mypoints.reshape((4,2))
    mypointsNew = np.zeros ((4,1,2), np.int32)
    add = mypoints.sum(1)
    # print(mypoints)
    # print(add)
    mypointsNew[0] = mypoints[np.argmin(add)] # [0, 0]
    mypointsNew[3] = mypoints[np.argmax(add)] # [w, h]
    diff = np.diff(mypoints, axis =1 )
    mypointsNew[1] = mypoints[np.argmin(diff)] # [w, 0]
    mypointsNew[2] = mypoints[np.argmax(diff)] # [0, h]
    # print(diff)

    return mypointsNew

def splitBoxes(img):
    """
    Splits an image into a grid of smaller boxes with 31 rows and 25 columns.

    Args:
        img (numpy.ndarray): The input image to be split, represented as a 2D or 3D
            numpy array.

    Returns:
        list of numpy.ndarray: A list of smaller boxes extracted from the image. Each
            box is represented as a numpy array, and the list contains all the boxes
            created by splitting the original image into a grid of 31 rows and 25 columns.
    """
    
    rows = np.vsplit(img,31)
    boxes = []
    for r in rows:
        cols = np.hsplit(r,25)
        for box in cols:
            boxes.append(box)
    return boxes

def splitBoxes2(img):
    """
    Splits an image into a grid of smaller boxes with 9 rows and 12 columns.

    Args:
        img (numpy.ndarray): The input image to be split, represented as a 2D or 3D
            numpy array.

    Returns:
        list of numpy.ndarray: A list of smaller boxes extracted from the image. Each
            box is represented as a numpy array, and the list contains all the boxes
            created by splitting the original image into a grid of 9 rows and 12 columns.
    """
    rows = np.vsplit(img,9)
    boxes = []
    for r in rows:
        cols = np.hsplit(r,12)
        for box in cols:
            boxes.append(box)
    return boxes

def splitBoxes3(img):
    """
    Splits an image into a grid of smaller boxes with 7 rows and 12 columns.

    Args:
        img (numpy.ndarray): The input image to be split, represented as a 2D or 3D
            numpy array.

    Returns:
        list of numpy.ndarray: A list of smaller boxes extracted from the image. Each
            box is represented as a numpy array, and the list contains all the boxes
            created by splitting the original image into a grid of 7 rows and 12 columns.
    """
    
    rows = np.vsplit(img,7)
    boxes = []
    for r in rows:
        cols = np.hsplit(r,12)
        for box in cols:
            boxes.append(box)
    return boxes

def crop_circle(image):
    """
    Crops a circular region from an image.

    Args:
        image (numpy.ndarray): The input image from which the circular region will be
            extracted. It is represented as a 2D or 3D numpy array.

    Returns:
        numpy.ndarray: The cropped image containing only the circular region. The
            result is a subsection of the original image, bounded by the smallest
            rectangle that fits the circular mask.
    """
    # Get the center and radius of the circle
    height, width = image.shape
    center = (width // 2, height // 2)
    radius = min(center)

    # Create a mask
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.circle(mask, center, radius, (255, 255, 255), thickness=-1)

    # Bitwise AND operation to get the circular region
    result = cv2.bitwise_and(image, image, mask=mask)

    # Find the bounding box of the circle
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    x, y, w, h = cv2.boundingRect(contours[0])

    # Crop the circular region
    cropped_circle = result[y:y+h, x:x+w]

    return cropped_circle



def mark_list_reshape(marks):
    """
    Reshapes and filters an array of marks, removing specified indices.

    Args:
        marks (numpy.ndarray): A flat array of mark values. The length of this array
            should be sufficient to reshape it into a 31x25 matrix.

    Returns:
        numpy.ndarray: A 2D array of shape (31, 20) after reshaping and removing
            specified indices. Each row in the resulting array has been filtered
            based on pre-defined criteria.
    """
    reshaped_arr = np.reshape(marks, (31, 25))
    skipped_indices = list(range(0, 25)) + list(range(150, 175)) + list(range(300, 325)) + list(range(450, 475)) + list(range(600, 625)) + list(range(750, 775))
    filtered_array = np.delete(reshaped_arr, skipped_indices)

    num_columns = 25
    num_rows = len(filtered_array) // num_columns

    # Reshape the array
    reshaped_array = filtered_array[:num_rows * num_columns].reshape((num_rows, num_columns))

    # Indices to remove from each row
    indices_to_remove = [0, 6, 12, 18, 24]

    # Remove specified indices from each row
    modified_array = np.delete(reshaped_array, indices_to_remove, axis=1)
    # print(modified_array)

    return modified_array

def id_mark_list_reshape(marks):
    """
    Reshapes and filters an array of marks for identification purposes.

    Args:
        marks (numpy.ndarray): A flat array of mark values. The length of this array
            should be sufficient to reshape it into a 9x12 matrix.

    Returns:
        numpy.ndarray: A 2D array of shape (9, 10) after reshaping and removing
            specified indices. The array has been processed to exclude certain columns
            based on the predefined criteria.
    """
    reshaped_arr = np.reshape(marks, (9, 12))
    skipped_indices = list(range(1, 12)) + list(range(97, 108))
    filtered_array = np.delete(reshaped_arr, skipped_indices)

    num_columns = 12
    num_rows = len(filtered_array) // num_columns

    # Reshape the array
    reshaped_array = filtered_array[:num_rows * num_columns].reshape((num_rows, num_columns))

    # Indices to remove from each row
    indices_to_remove = [0,1]

    # Remove specified indices from each row
    modified_array = np.delete(reshaped_array, indices_to_remove, axis=1)

    return modified_array

def exam_mark_list_reshape(marks):
    """
    Reshapes and filters an array of exam marks for processing purposes.

    Args:
        marks (numpy.ndarray): A flat array of mark values. The length of this array
            should be sufficient to reshape it into a 7x12 matrix.

    Returns:
        numpy.ndarray: A 2D array of shape (7, 10) after reshaping and removing
            specified indices. The array has been processed to exclude certain columns
            based on the predefined criteria.
    """
    reshaped_arr = np.reshape(marks, (7, 12))
    skipped_indices = list(range(1, 12)) + list(range(73, 84))
    filtered_array = np.delete(reshaped_arr, skipped_indices)

    num_columns = 12
    num_rows = len(filtered_array) // num_columns

    # Reshape the array
    reshaped_array = filtered_array[:num_rows * num_columns].reshape((num_rows, num_columns))

    # Indices to remove from each row
    indices_to_remove = [0,1]

    # Remove specified indices from each row
    modified_array = np.delete(reshaped_array, indices_to_remove, axis=1)
    # print(modified_array)

    return modified_array


def extract_and_reshape(array):
    """
    Extracts and reshapes a 2D array into smaller grids.

    Args:
        array (numpy.ndarray): The input 2D array to be processed. The height of the array
            should be a multiple of 5, and the width should be a multiple of 5 to ensure
            proper extraction of 5x5 grids.

    Returns:
        numpy.ndarray: A 2D array consisting of the vertically stacked 5x5 grids extracted
            from the original array. The resulting array has been reshaped to include all
            extracted grids.
    """
    grids = []
    rows = array.shape[0] // 5

    for i in range(rows):
        for j in range(4):
            start_row = i * 5
            end_row = (i + 1) * 5
            start_col = j * 5
            end_col = (j + 1) * 5
            grid = array[start_row:end_row, start_col:end_col]
            grids.append(grid)

    extracted_rows = np.vstack(grids)
    # print(extracted_rows)
    return extracted_rows


def check_and_replace(matrix):
    """
    Checks and replaces rows in a matrix based on specific conditions.

    This function iterates through each row of the matrix and performs the following checks:
    - If all elements in a row are zero, the entire row is replaced with the string '6'.
    - If the sum of elements in a row is greater than 1, the entire row is replaced with the string '7'.

    Args:
        matrix (numpy.ndarray): A 2D array where each element is a numeric value. The function
            processes this matrix to replace rows based on the specified conditions.

    Returns:
        numpy.ndarray: A matrix of the same shape as the input, where rows have been replaced
            according to the conditions specified. The output matrix contains strings '6' or
            '7' in place of the original values, based on the checks performed.
    """
    for i, row in enumerate(matrix):
        if all(value == 0 for value in row):
            matrix[i] = ['6'] * len(row)
        elif sum(row) > 1:
            matrix[i] = ['7'] * len(row)
    return matrix


def locateAns(matrix, num_questions):
    """
    Identifies the most frequent answer or marks 'x' if all elements in a row are the same.

    This function processes each row of the given matrix to determine the most frequent value
    for each question. If all elements in a row are the same, it marks that row with 'x' to
    indicate a uniform answer. Otherwise, it identifies the index of the maximum value in the
    row.

    Args:
        matrix (numpy.ndarray): A 2D array where each row corresponds to answers or marks for
            a question. The matrix should have shape (num_questions, num_options), where
            `num_options` is the number of possible answers or marks.
        num_questions (int): The number of questions or rows in the matrix.

    Returns:
        list: A list of the most frequent values or 'x' for each row. Each entry corresponds
            to a question, with either the index of the maximum value or 'x' if all values
            in the row are the same.
    """
    myIndex = []
    for x in range(0, num_questions):
        arr = matrix[x]
        if np.all(arr == arr[0]):
            myIndexVal = 'x'
        else:
            myIndexVal = np.where(arr == np.amax(arr))[0][0]
        myIndex.append(myIndexVal)
    return myIndex

def find_x_positions(arr):
    """
    Finds and returns the 1-based positions of elements marked as 'x' in the array.

    This function scans through the given array to identify the positions of all elements
    that are equal to 'x'. It returns these positions in a list, with the positions adjusted
    to be 1-based.

    Args:
        arr (list or numpy.ndarray): A 1D array or list where each element is a value or 'x'.
            The function processes this array to find the positions of 'x' values.

    Returns:
        list: A list of integers representing the 1-based positions of the elements marked
            as 'x' in the input array. Each position is offset by 1 to convert from 0-based
            to 1-based indexing.
    """
    positions = [index + 1 for index, value in enumerate(arr) if value == 'x']
    return positions


def check_mirror_index(ansIndex, markIndex):
    """
    Compares two lists of indices and replaces mismatched values with 'x'.

    Args:
        ansIndex (list): A list of indices representing the correct answers.
        markIndex (list): A list of indices representing the marked answers.

    Returns:
        list: The modified `markIndex` list where mismatched values have been replaced with 'x'.
    
    Raises:
        ValueError: If `ansIndex` and `markIndex` are not of the same length.
    """
    try: # Ensure both lists are of the same length
        if len(ansIndex) != len(markIndex):
            raise ValueError("Input lists must have the same length")

        # Iterate through the indices of the lists
        for i in range(len(ansIndex)):
            # Check if the elements at the current index are different
            if ansIndex[i] != markIndex[i]:
                # If different, set the element in the 'mark' list to 5
                markIndex[i] = "x"
    except ValueError as e:
        print(f"Error: {e}")
    return markIndex

def check_incorrect_ans(ansIndex, markIndex):
    """
    Identifies indices where answers do not match between two lists.

    Args:
        ansIndex (list): A list of correct answer indices.
        markIndex (list): A list of marked answer indices to be compared with `ansIndex`.

    Returns:
        list: A list of 1-based indices where the answers in `markIndex` do not match those
            in `ansIndex`. Each index in the list is offset by 1 to convert from 0-based
            to 1-based indexing.
    """
    non_matching_indices = []
    # Loop through the arrays based on the minimum length to avoid index errors
    for i in range(min(len(ansIndex), len(markIndex))):
        if ansIndex[i] != markIndex[i]:
            # Append index with an offset of +1
            non_matching_indices.append(i + 1)
    return non_matching_indices


def grade(myIndex, answer, questions):
    """
    Compares student answers to correct answers and calculates grades.

    This function compares two lists: `myIndex`, which contains the student's answers, and
    `answer`, which contains the correct answers. It calculates the grade for each question
    by checking if the student's answer matches the correct answer. A grade of 1 is assigned
    for a correct answer, and 0 for an incorrect answer.

    Args:
        myIndex (list): A list of indices representing the student's answers.
        answer (list): A list of indices representing the correct answers.
        questions (int): The total number of questions to be graded.

    Returns:
        list: A list of grades where each element is 1 for a correct answer and 0 for an
            incorrect answer. The list has a length equal to the number of questions.
    """
    grading = []
    for x in range (0,questions):
        if answer[x] == myIndex[x]:
            grading.append(1)
        else: grading.append(0)
    return grading

def score(results, points_per_diff, questions):
    """
    Calculates the total score by multiplying the results with points per question difficulty.

    Args:
        results (list): A list of grades, where each grade is 1 for a correct answer and 0 for an incorrect answer.
        points_per_diff (list): A list of points assigned to each question based on difficulty.
        questions (int): The total number of questions.

    Returns:
        float: The total score, calculated by summing the products of results and points_per_diff.
    """
    # Ensure the length of results and points_per_diff matches the number of questions
    if len(results) != questions or len(points_per_diff) != questions:
        raise ValueError("Length of results and points_per_diff must match the number of questions.")
    
    # Multiply the results and points_per_diff element-wise
    multiplication_result = [results[i] * points_per_diff[i] for i in range(questions)]
    
    # Print the multiplication result
    print("Multiplication result:", multiplication_result)
    
    # Sum the multiplication results to get the total score
    total_score = sum(multiplication_result)
    
    return total_score

class InvalidStudentIDError(Exception):
    """Custom exception for invalid student ID"""
    pass

class InvalidExamIDError(Exception):
    """Custom exception for invalid exam ID"""
    pass

def check_student_ids(student_ids):
    """
    Validates a list of student IDs to ensure there are no invalid values.

    This function checks each student ID in the given list to determine if any ID is marked
    as 'x', which indicates an invalid ID. If any such invalid ID is found, an exception is
    raised. If all IDs are valid, a confirmation message is returned.

    Args:
        student_ids (list): A list of student IDs where each ID is expected to be a valid
            identifier or 'x' indicating an invalid ID.

    Returns:
        str: A message indicating whether the student IDs are valid or if an error occurred.

    Raises:
        InvalidStudentIDError: If any student ID in the list is 'x', indicating an invalid ID.
    """
    try:
        # Check for invalid values
        for id in student_ids:
            if id == 'x':
                raise InvalidStudentIDError("Invalid student ID")
        return("student ID is valid.")
    except InvalidStudentIDError as e:
        return(f"Error: {e}")

def check_exam_ids(exam_ids):
    """
    Validates a list of exam IDs to ensure there are no invalid values.

    This function checks each exam ID in the given list to determine if any ID is marked
    as 'x', which indicates an invalid ID. If any such invalid ID is found, an exception is
    raised. If all IDs are valid, a confirmation message is returned.

    Args:
        exam_ids (list): A list of exam IDs where each ID is expected to be a valid identifier
            or 'x' indicating an invalid ID.

    Returns:
        str: A message indicating whether the exam IDs are valid or if an error occurred.

    Raises:
        InvalidExamIDError: If any exam ID in the list is 'x', indicating an invalid ID.
    """
    try:
        # Check for invalid values
        for id in exam_ids:
            if id == 'x':
                raise InvalidExamIDError("Invalid exam ID")
        return("exam ID is valid.")
    except InvalidExamIDError as e:
        return(f"Error: {e}")

def check_id_pair(resultPair, studExamPair):
    """
    Validates that a pair of student ID and exam ID matches the expected result pair.

    This function compares the provided `resultPair` with the `studExamPair` to ensure they
    match. If the pairs do not match, a `ValueError` is raised. If they match, a confirmation
    message is returned.

    Args:
        resultPair (tuple): A tuple containing the expected student ID and exam ID.
        studExamPair (tuple): A tuple containing the actual student ID and exam ID to be checked.

    Returns:
        str: A message indicating whether the student ID and exam ID pair is valid or if an
            error occurred.

    Raises:
        ValueError: If `resultPair` and `studExamPair` do not match, indicating an invalid pair.
    """
    try:
        # Check if resultPair and studExamPair are the same
        if resultPair != studExamPair:
            raise ValueError("Invalid student ID and exam ID pair.")
        return ("Valid student ID and exam ID pair.")
    except ValueError as e:
        return(e)
    
def string_to_int_list(s):
    return [int(char) for char in s]

def int_list_to_string(lst):
    return ''.join(str(num) for num in lst)


def get_image_files(folder_path):
    # Check if the folder exists
    if not os.path.isdir(folder_path):
        print(f"The folder '{folder_path}' does not exist.")
        return []

    # Supported image file extensions
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.tiff']

    # List to hold the image files found
    image_files = []

    # Loop through each extension and find files matching the pattern
    for ext in image_extensions:
        # Use glob to get all files matching the extension
        found_files = glob.glob(os.path.join(folder_path, ext))
        image_files.extend(found_files)
    
    return image_files

# def choose_folder():
#     # Hide the root Tk window
#     root = Tk()
#     root.withdraw()

#     # Open a file dialog to choose a directory
#     folder_path = filedialog.askdirectory(title="Select a folder")

#     # Close the Tk window
#     root.destroy()

#     return folder_path

# def select_csv_file():
#     # Create a Tkinter root window (it will not be shown)
#     root = Tk()
#     root.withdraw()  # Hide the root window

#     try:
#         # Open the file dialog
#         file_path = filedialog.askopenfilename(
#             title="Select a CSV file",
#             filetypes=[("CSV files", "*.csv")]
#         )

#         if not file_path:  # Check if no file was selected
#             raise ValueError("No file selected.")
        
#         return file_path

#     except ValueError as e:
#         print(f"Error: {e}")
#         return None

def create_text_file(folder_path, file_name, content):
    # Ensure the folder exists
    os.makedirs(folder_path, exist_ok=True)
    
    # Define the full path to the text file
    file_path = os.path.join(folder_path, file_name)
    
    # Create and write content to the text file
    with open(file_path, 'w') as file:
        file.write(content)
    
    print(f"File '{file_name}' has been created in '{folder_path}'.")


def append_to_text_file(folder_path, file_name, additional_content): 
    # Define the full path to the text file
    file_path = os.path.join(folder_path, file_name)
    
    # Append additional content to the text file
    with open(file_path, 'a') as file:
        file.write(f'\n{additional_content}')
    
    print(f"Additional content has been appended to '{file_name}'.")

def are_strings_equal(string1, string2):
    if not isinstance(string1, str) or not isinstance(string2, str):
        raise ValueError("Both inputs must be strings.")
    
    if string1 == string2:
        return string1
    else:
        return "invalid exam id"
    
# Function to create and append data to CSV
def append_to_csv(data, file_name):
    # Check if the file already exists
    file_exists = os.path.isfile(file_name)
    
    # Open the file in append mode ('a') or create a new one if it doesn't exist
    with open(file_name, 'a', newline='') as file:
        writer = csv.writer(file)
        
        # If the file doesn't exist, write the header first
        if not file_exists:
            writer.writerow(['String1', 'String2', 'String3', 'String4', 'String5', 'String6', 'String7', 'String8'])
        
        # Write the data
        writer.writerow(data)

# Function to create the CSV file if it doesn't exist
def create_csv(file_name):
    if not os.path.isfile(file_name):
        with open(file_name, 'w', newline='') as file:
            writer = csv.writer(file)
            # Write the header
            writer.writerow(["Last Name", "First Name", "Middle Initial", "ID", "Set ID", "Score", "Invalid Answer", "Incorrect Answer"])
        print(f"File '{file_name}' created successfully with headers.")



