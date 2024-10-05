import cv2 # computer vision library
import numpy as np
import utilis # function files
import os
import shutil
from keras.models import load_model  # TensorFlow is required for Keras to work
from PIL import Image, ImageOps
from pathlib import Path



def rect_locator(image_path):
    try:
        widthImg = 700      # width img for resize
        heightImg = 713     # height img for resize
        img = cv2.imread(image_path) # load img using cv2 library

        # PREPROCESSING
        img = cv2.resize(img, (widthImg, heightImg)) # resize
        imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # process photo to grayscale
        imgBlur = cv2.GaussianBlur(imgGray, (5,5),1) # blur image
        imgCanny = cv2.Canny(imgBlur, 10, 50, apertureSize=3, L2gradient = True) # apply canny to the blurred img

        imgContours = img.copy() # copy of image for drawing contours
        imgBigContours = img.copy() # copy of image for plotting edge points
        imgWarpPage = img.copy() # copy of image for warping the answer box

        cnts, hierarchy = cv2.findContours (imgCanny,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE) # look for contour lines
        cv2.drawContours(imgContours, cnts, -1, (0,0,0), 10) # draw contours to the copy img
        pageCon = utilis.rectContour(cnts) 
        page = utilis.getCornerPoints(pageCon[0])
        cv2.drawContours(imgWarpPage,page,-1,(0,0,0),30)
        page = utilis.reorder(page)


        p1 = np.float32(page)
        p2 = np.float32([[0,0],[widthImg,0], [0,heightImg], [widthImg,heightImg]])
        matrix = cv2.getPerspectiveTransform(p1,p2)
        imgWarp = cv2.warpPerspective(img,matrix,(widthImg,heightImg)) #warp the page box

        imgDrawCon = imgWarp.copy()
        imgWarpCopy2 = imgWarp.copy()
        imgFinal = imgWarp.copy()

        img2 = cv2.resize(imgWarp, (widthImg, heightImg)) # resize


        imgGray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) 
        imgBlur2 = cv2.GaussianBlur(imgGray2, (5,5),1)
        imgCanny2 = cv2.Canny(imgBlur2, 10, 50, apertureSize=3, L2gradient = True)

        # LOCATE CONTOURS (PREPROCESSING)
        contours, hierarchy = cv2.findContours (imgCanny2,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(imgDrawCon, contours, -1, (0,255,0), 10) # Draw contours in the image


        # LOCATE RECTANGLES (PREPROCESSING)
        rectCon = utilis.rectContour(contours)
        biggestCon = utilis.getCornerPoints(rectCon[0])
        studCon = utilis.getCornerPoints(rectCon[1])
        examCon = utilis.getCornerPoints(rectCon[2])

        if biggestCon.size != 0 and studCon.size !=0 and examCon.size !=0:
            cv2.drawContours(imgWarpCopy2,biggestCon,-1,(0,255,0),30)
            cv2.drawContours(imgWarpCopy2,studCon,-1,(255,0,0),30)
            cv2.drawContours(imgWarpCopy2,examCon,-1,(0,0,255),30)

            biggestCon = utilis.reorder(biggestCon)
            studCon = utilis.reorder(studCon)
            examCon = utilis.reorder(examCon)

            pt1 = np.float32(biggestCon)
            pt2 = np.float32([[0,0],[widthImg,0], [0,heightImg], [widthImg,heightImg]])
            matrix = cv2.getPerspectiveTransform(pt1,pt2)
            imgWarpColored = cv2.warpPerspective(imgWarp,matrix,(widthImg,heightImg))

            ptS1 = np.float32(studCon)
            ptS2 = np.float32([[0,0],[276,0], [0,207], [276,207]])
            matrixS = cv2.getPerspectiveTransform(ptS1,ptS2)
            imgStudWarpColored = cv2.warpPerspective(imgWarp,matrixS,(276,207))

            ptSc1 = np.float32(examCon)
            ptSc2 = np.float32([[0,0],[276,0], [0,161], [276,161]])
            matrixSc = cv2.getPerspectiveTransform(ptSc1,ptSc2)
            imgExamWarpColored = cv2.warpPerspective(imgWarp,matrixSc,(276,161))


        # APPLY THRESHOLD (PREPROCESSING)
            imgWarpGray = cv2.cvtColor(imgWarpColored, cv2.COLOR_BGR2GRAY)
            gausAns = cv2.adaptiveThreshold(imgWarpGray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 99, 1)

            imgStudWarpGray = cv2.cvtColor(imgStudWarpColored, cv2.COLOR_BGR2GRAY)
            gausStud = cv2.adaptiveThreshold(imgStudWarpGray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 99, 1)

            imgExamWarpGray = cv2.cvtColor(imgExamWarpColored, cv2.COLOR_BGR2GRAY)
            gausExam = cv2.adaptiveThreshold(imgExamWarpGray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 99, 1)

        # IMAGE SPLITTING (PREPROCESSING)
            ansBox = utilis.splitBoxes(gausAns)
            studBox = utilis.splitBoxes2(gausStud)
            examBox = utilis.splitBoxes3(gausExam)
            # cv2.imshow("test" , boxes3 [13])
            # print((cv2.countNonZero(boxes3[26])), (cv2.countNonZero(boxes3[27])))
            cropAns = [utilis.crop_circle(box) for box in ansBox]
            # cv2.imshow("test" , crop_circles[27])
            cropStud = [utilis.crop_circle(box) for box in studBox]
            # cv2.imshow("test" , crop_circles2[13])
            cropExam = [utilis.crop_circle(box) for box in examBox]
            # cv2.imshow("test" , crop_circles3[14])

        return cropStud, cropExam, cropAns

        # imgBlank = np.zeros_like(img)
        # imageArray = ([imgWarpColored,imgStudWarpColored, imgExamWarpColored,imgWarpGray],
        #             [gausAns,gausStud, gausExam,imgBlank])
        # imgStacked = utilis.stackImages(0.5, imageArray)

        # cv2.imshow("Stacked images", imgStacked)
        # cv2.waitKey(0)
    except cv2.error:
        print("Unable to load photo. Retake photo.")
        return None, None, None, None, None, None, None
    except IndexError:
        print("Unable to load photo. Retake photo.")
        return None, None, None, None, None, None, None
    except ValueError as ve:
        print("Unable to load photo. Retake photo.")
        return None, None, None, None, None, None, None
    except Exception as e:
        return(e)


# image = rect_locator("resources/k1.jpg")


def id_scan(cropStud):
    # MODEL LOADING 
    np.set_printoptions(suppress=True)
    THIS_FOLDER = Path(__file__).parent.resolve()
    my_model = THIS_FOLDER / "keras_model.h5"
    model = load_model(my_model, compile=False) # Load the model
    my_labels = THIS_FOLDER / "labels.txt"
    class_names = open(my_labels, "r").readlines() # Load the labels
    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32) # Create the array of the right shape to feed into the keras model
    # IMAGE CHECKER FUNCTION
    def check(image):
        """
        Processes an image for prediction and returns a classification result.

        This function takes an image file path or an image object, resizes and normalizes it,
        and then uses a pre-trained model to make a prediction. The function returns `1` if the 
        model's prediction index is `1`, and `0` otherwise.

        Args:
            image (str or PIL.Image.Image): The path to the image file or a PIL Image object to be processed.

        Returns:
            int: Returns `1` if the model's prediction index is `1`, otherwise returns `0`.

        Raises:
            FileNotFoundError: If the provided image path does not exist (when `image` is a string).
            ValueError: If `image` is not a valid image file or PIL Image object.

        Example:
            >>> result = check("path/to/image.jpg")
            >>> print(result)
            1
        """

        # Replace this with the path to your image
        # image = Image.open("marked/marked (35).jpg").convert("RGB")
        image = Image.open(image).convert("RGB")
        # image = Image.fromarray(image).convert('RGB')
        size = (224, 224) # resizing the image to be at least 224x224 and then cropping from the center
        image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        image_array = np.asarray(image) # turn the image into a numpy array
        normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1 # Normalize the image
        data[0] = normalized_image_array # Load the image into the array
        prediction = model.predict(data) # Predicts the model
        index = np.argmax(prediction)

        return 1 if index == 1 else 0
    
    idMarks = []
    temp_dir = 'temp_images'

    os.makedirs(temp_dir, exist_ok=True)

    for i, img in enumerate(cropStud):
        filename = os.path.join(temp_dir, f"image{i+1}.jpg")  # Customize filename and format
        try: 
            cv2.imwrite(filename, img) # Save the image to the file
            result = check(filename) # Perform the check operation
            idMarks.append(result)
        except Exception as e:
            print(f"An error occurred: {e}")

    shutil.rmtree(temp_dir) # Clean up the directory after processing

    os.makedirs(temp_dir, exist_ok=True)
    
    return idMarks

def id_check(id_marks):
    idLen = 7

     # CHECKING OF IMAGES (student id)
    idMarkReshaped = utilis.id_mark_list_reshape(id_marks) #removes unwanted boxes
    idCheckedMarkings = utilis.check_and_replace(idMarkReshaped) #checks multi answers for each line

    #FINDING INDEX VALUES OF THE MARKINGS AND ANSWERS (student id)
    markIndex = utilis.locateAns(idCheckedMarkings, idLen) #checks the checked matrix fits the lenght of student id

    return markIndex

def exam_id_scan(cropExam):
    # MODEL LOADING 
    np.set_printoptions(suppress=True)
    THIS_FOLDER = Path(__file__).parent.resolve()
    my_model = THIS_FOLDER / "keras_model.h5"
    model = load_model(my_model, compile=False) # Load the model
    my_labels = THIS_FOLDER / "labels.txt"
    class_names = open(my_labels, "r").readlines() # Load the labels
    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32) # Create the array of the right shape to feed into the keras model
    # IMAGE CHECKER FUNCTION
    def check(image):
        """
        Processes an image for prediction and returns a classification result.

        This function takes an image file path or an image object, resizes and normalizes it,
        and then uses a pre-trained model to make a prediction. The function returns `1` if the 
        model's prediction index is `1`, and `0` otherwise.

        Args:
            image (str or PIL.Image.Image): The path to the image file or a PIL Image object to be processed.

        Returns:
            int: Returns `1` if the model's prediction index is `1`, otherwise returns `0`.

        Raises:
            FileNotFoundError: If the provided image path does not exist (when `image` is a string).
            ValueError: If `image` is not a valid image file or PIL Image object.

        Example:
            >>> result = check("path/to/image.jpg")
            >>> print(result)
            1
        """

        # Replace this with the path to your image
        # image = Image.open("marked/marked (35).jpg").convert("RGB")
        image = Image.open(image).convert("RGB")
        # image = Image.fromarray(image).convert('RGB')
        size = (224, 224) # resizing the image to be at least 224x224 and then cropping from the center
        image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        image_array = np.asarray(image) # turn the image into a numpy array
        normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1 # Normalize the image
        data[0] = normalized_image_array # Load the image into the array
        prediction = model.predict(data) # Predicts the model
        index = np.argmax(prediction)

        return 1 if index == 1 else 0
    
    exam_id_mark = []
    temp_dir = 'temp_images'

    os.makedirs(temp_dir, exist_ok=True)

    for i, img in enumerate(cropExam):
        filename = os.path.join(temp_dir, f"image{i+1}.jpg")  # Customize filename and format
        try: 
            cv2.imwrite(filename, img) # Save the image to the file
            result = check(filename) # Perform the check operation
            exam_id_mark.append(result)
        except Exception as e:
            print(f"An error occurred: {e}")

    shutil.rmtree(temp_dir) # Clean up the directory after processing

    os.makedirs(temp_dir, exist_ok=True)
    
    return exam_id_mark

def exam_id_check(exam_id_mark):
    exam_id_len = 5
    # CHECKING OF IMAGES (exam id)
    exMarkReshaped = utilis.exam_mark_list_reshape(exam_id_mark) #removes unwanted boxes
    exCheckedMarkings = utilis.check_and_replace(exMarkReshaped) #checks multi answers for each line

    #FINDING INDEX VALUES OF THE MARKINGS AND ANSWERS (exam id)
    examIndex = utilis.locateAns(exCheckedMarkings, exam_id_len) #checks the checked matrix fits the lenght of exam id

    return examIndex

def answer_scan(cropAns):
    # MODEL LOADING 
    np.set_printoptions(suppress=True)
    THIS_FOLDER = Path(__file__).parent.resolve()
    my_model = THIS_FOLDER / "keras_model.h5"
    model = load_model(my_model, compile=False) # Load the model
    my_labels = THIS_FOLDER / "labels.txt"
    class_names = open(my_labels, "r").readlines() # Load the labels
    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32) # Create the array of the right shape to feed into the keras model
    # IMAGE CHECKER FUNCTION
    def check(image):
        """
        Processes an image for prediction and returns a classification result.

        This function takes an image file path or an image object, resizes and normalizes it,
        and then uses a pre-trained model to make a prediction. The function returns `1` if the 
        model's prediction index is `1`, and `0` otherwise.

        Args:
            image (str or PIL.Image.Image): The path to the image file or a PIL Image object to be processed.

        Returns:
            int: Returns `1` if the model's prediction index is `1`, otherwise returns `0`.

        Raises:
            FileNotFoundError: If the provided image path does not exist (when `image` is a string).
            ValueError: If `image` is not a valid image file or PIL Image object.

        Example:
            >>> result = check("path/to/image.jpg")
            >>> print(result)
            1
        """

        # Replace this with the path to your image
        # image = Image.open("marked/marked (35).jpg").convert("RGB")
        image = Image.open(image).convert("RGB")
        # image = Image.fromarray(image).convert('RGB')
        size = (224, 224) # resizing the image to be at least 224x224 and then cropping from the center
        image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        image_array = np.asarray(image) # turn the image into a numpy array
        normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1 # Normalize the image
        data[0] = normalized_image_array # Load the image into the array
        prediction = model.predict(data) # Predicts the model
        index = np.argmax(prediction)

        return 1 if index == 1 else 0
    
    ans_mark = []
    temp_dir = 'temp_images'

    os.makedirs(temp_dir, exist_ok=True)

    for i, img in enumerate(cropAns):
        filename = os.path.join(temp_dir, f"image{i+1}.jpg")  # Customize filename and format
        try: 
            cv2.imwrite(filename, img) # Save the image to the file
            result = check(filename) # Perform the check operation
            ans_mark.append(result)
        except Exception as e:
            print(f"An error occurred: {e}")

    shutil.rmtree(temp_dir) # Clean up the directory after processing

    os.makedirs(temp_dir, exist_ok=True)
    
    return ans_mark

def ans_check(answer_marks,answer_key):
    questions = len(answer_key)
    answersKey = utilis.string_to_int_list(answer_key)
    # CHECKING OF IMAGES (ans sheet)
    ansMark = utilis.mark_list_reshape(answer_marks) #removes unwanted boxes
    ansMarkReshaped = utilis.extract_and_reshape(ansMark)
    ansCheckedMarkings = utilis.check_and_replace(ansMarkReshaped) #checks multi answers for each line

    #FINDING INDEX VALUES OF THE MARKINGS AND ANSWERS (ans sheet)
    ansIndex = utilis.locateAns(ansCheckedMarkings, questions) #checks the checked matrix fits the lenght of exam id
    ansIndex2 = ansIndex.copy()
    invAns = utilis.find_x_positions(ansIndex)
    
    ansResult = utilis.check_mirror_index(answersKey, ansIndex) # compares the scanned markings to the exam id number
    incAns = utilis.check_incorrect_ans(ansIndex2, ansResult)

    # GRADING
    grading = utilis.grade(ansResult, answersKey, questions)
    # print(len(grading))

    # EVALUATE SCORE
    score = utilis.score(grading, questions)

    return score, invAns, incAns