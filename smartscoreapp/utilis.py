import cv2
import numpy as np
from keras.models import load_model  # TensorFlow is required for Keras to work
from PIL import Image, ImageOps  # Install pillow instead of PIL
import numpy as np
import test

def capture_and_save_image(file_path):
    # Open a connection to the camera (0 represents the default camera)
    cap = cv2.VideoCapture(1)

    # Check if the camera opened successfully
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    while True:
        # Capture a single frame
        ret, frame = cap.read()

        # Display the captured frame
        cv2.imshow('Press q to capture and save', frame)

        # Check for the 'q' key to be pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            # Save the captured frame to the specified file path
            cv2.imwrite(file_path, frame)
            print(f"Image captured and saved to {file_path}")
            break

    # Release the camera and close the window
    cap.release()
    cv2.destroyAllWindows()

def show_captured_image(file_path):
    # Load the saved image
    img = cv2.imread(file_path)

    # Display the image
    cv2.imshow('Captured Image', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def stackImages(scale,imgArray):
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
    peri = cv2.arcLength(cont, True)
    approx = cv2.approxPolyDP(cont,0.02*peri,True)
    return approx

def reorder(mypoints):
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
    rows = np.vsplit(img,31)
    boxes = []
    for r in rows:
        cols = np.hsplit(r,25)
        for box in cols:
            boxes.append(box)
    return boxes



def calculate_white_percentage(image):
    # Calculate the total number of pixels in the image
    total_pixels = image.size

    # Count the number of white pixels (pixel value = 255 in a grayscale image)
    white_pixels = np.sum(image == 255)

    # Calculate the percentage of white area
    white_percentage = (white_pixels / total_pixels) * 100
    return 1 if white_percentage > 53 else 0



# def ans_list_arrays(crop_circles):
#     reshaped_arr = np.reshape(crop_circle, (31, 25))
#     skipped_indices = list(range(0, 25)) + list(range(150, 175)) + list(range(300, 325)) + list(range(450, 475)) + list(range(600, 625)) + list(range(750, 775))
#     filtered_array = np.delete(reshaped_arr, skipped_indices)

#     num_columns = 25
#     num_rows = len(filtered_array) // num_columns

#     # Reshape the array
#     reshaped_array = filtered_array[:num_rows * num_columns].reshape((num_rows, num_columns))

#     # Indices to remove from each row
#     indices_to_remove = [0, 6, 12, 18, 24]

#     # Remove specified indices from each row
#     modified_array = np.delete(reshaped_array, indices_to_remove, axis=1)
#     print(modified_array)

#     return modified_array


def mark_list_reshape(marks):
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
    print(modified_array)

    return modified_array

def pixelCount(boxes):
    countPixel = []
    for image in boxes:
        totalPixel = cv2.countNonZero(image)
        countPixel.append(totalPixel)

    # print(len(countPixel))
    
    reshaped_arr = np.reshape(countPixel, (31, 25))
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

    return modified_array


def extract_and_reshape(array):
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
    return extracted_rows

def check_and_replace(matrix):
    for i, row in enumerate(matrix):
        if all(value == 0 for value in row):
            matrix[i] = [6] * len(row)
        elif sum(row) > 1:
            matrix[i] = [7] * len(row)
    return matrix

def locateAns(matrix, num_questions):
    myIndex = []
    for x in range(0, num_questions):
        arr = matrix[x]
        if np.all(arr == arr[0]):
            myIndexVal = 8
        else:
            myIndexVal = np.where(arr == np.amax(arr))[0][0]
        myIndex.append(myIndexVal)
    return myIndex

def check_mirror_index(ansIndex, markIndex):
    # Ensure both lists are of the same length
    if len(ansIndex) != len(markIndex):
        raise ValueError("Input lists must have the same length")

    # Iterate through the indices of the lists
    for i in range(len(ansIndex)):
        # Check if the elements at the current index are different
        if ansIndex[i] != markIndex[i]:
            # If different, set the element in the 'mark' list to 5
            markIndex[i] = 5

    return markIndex


def grade(myIndex, answer, questions):
    grading = []
    for x in range (0,questions):
        if answer[x] == myIndex[x]:
            grading.append(1)
        else: grading.append(0)
    return grading

def score(results, questions):
    score = (sum(results)/questions)*100
    return score 

def remove_shadows(image):
    # Convert the image to the LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

    # Split the LAB image into L, A, and B channels
    l, a, b = cv2.split(lab)

    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to the L channel
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)

    # Merge the CLAHE-enhanced L channel with the original A and B channels
    updated_lab = cv2.merge([cl, a, b])

    # Convert the LAB image back to BGR color space
    result = cv2.cvtColor(updated_lab, cv2.COLOR_LAB2BGR)

    return result

def crop_circle(image):
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
