import cv2 # computer vision library
import numpy as np
import utilis # function files
import os
from keras.models import load_model  # TensorFlow is required for Keras to work
from PIL import Image, ImageOps 



#############################################################################

# VARIABLES

answers = [0,1,2,3,4,0,1,2,3,4,0,1,2,3,4,0,1,2,3,4
           ,0,1,2,3,4,0,1,2,3,4,0,1,2,3,4,0,1,2,3,4
           ,0,1,2,3,4,0,1,2,3,4,0,1,2,3,4,0,1,2,3,4
           ,0,1,2,3,4,0,1,2,3,4,0,1,2,3,4,0,1,2,3,4
           ,0,1,2,3,4,0,1,2,3,4,0,1,2,3,4,0,1,2,3,4] # correct answers
questions = len(answers)   # number of items
choices = 5

############################################################################

image_path = "resources/qw1.jpg"
widthImg = 700      # width img for resize
heightImg = 713     # height img for resize
img = cv2.imread(image_path) # load img using cv2 library

#############################################################################

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
imgWarp = cv2.warpPerspective(img,matrix,(widthImg,heightImg))

imgWarpCopy = imgWarp.copy()
imgWarpCopy2 = imgWarp.copy()
imgFinal = imgWarp.copy()

img2 = cv2.resize(imgWarp, (widthImg, heightImg)) # resize

imgGray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) 

imgBlur2 = cv2.GaussianBlur(imgGray2, (5,5),1)
imgCanny2 = cv2.Canny(imgBlur2, 10, 50, apertureSize=3, L2gradient = True)

# try:
        # LOCATE CONTOURS
contours, hierarchy = cv2.findContours (imgCanny2,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
cv2.drawContours(imgWarpCopy, contours, -1, (0,255,0), 10) 

# LOCATE RECTANGLES
rectCon = utilis.rectContour(contours)
biggestCon = utilis.getCornerPoints(rectCon[0])
studId = utilis.getCornerPoints(rectCon[1])
scoreCon = utilis.getCornerPoints(rectCon[2])

if biggestCon.size != 0 and studId.size !=0 and scoreCon.size !=0:
    cv2.drawContours(imgWarpCopy2,biggestCon,-1,(0,255,0),30)
    cv2.drawContours(imgWarpCopy2,studId,-1,(255,0,0),30)
    cv2.drawContours(imgWarpCopy2,scoreCon,-1,(0,0,255),30)

    biggestCon = utilis.reorder(biggestCon)
    studId = utilis.reorder(studId)
    scoreCon = utilis.reorder(scoreCon)

    pt1 = np.float32(biggestCon)
    pt2 = np.float32([[0,0],[widthImg,0], [0,heightImg], [widthImg,heightImg]])
    matrix = cv2.getPerspectiveTransform(pt1,pt2)
    imgWarpColored = cv2.warpPerspective(imgWarp,matrix,(widthImg,heightImg))

    ptS1 = np.float32(studId)
    ptS2 = np.float32([[0,0],[325,0], [0,150], [325,150]])
    matrixS = cv2.getPerspectiveTransform(ptS1,ptS2)
    imgStudWarpColored = cv2.warpPerspective(imgWarp,matrixS,(325,150))

    ptSc1 = np.float32(scoreCon)
    ptSc2 = np.float32([[0,0],[325,0], [0,150], [325,150]])
    matrixSc = cv2.getPerspectiveTransform(ptSc1,ptSc2)
    imgScoreWarpColored = cv2.warpPerspective(imgWarp,matrixSc,(325,150))


# APPLY THRESHOLD
    imgWarpGray = cv2.cvtColor(imgWarpColored, cv2.COLOR_BGR2GRAY)
    # imgWarpBlur = cv2.GaussianBlur(imgWarpGray, (5,5),1)
    # imgThresh = cv2.threshold(imgWarpGray, 165, 255, cv2.THRESH_BINARY_INV)[1]
    gaus = cv2.adaptiveThreshold(imgWarpGray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 99, 1)

    boxes = utilis.splitBoxes(gaus)
    # cv2.imshow("test" , boxes [246])
    # print((cv2.countNonZero(boxes[26])), (cv2.countNonZero(boxes[27])))

    crop_circles = [utilis.crop_circle(box) for box in boxes]
    cv2.imshow("test" , crop_circles[27])

    # for i, img in enumerate(crop_circles):
    #     # # Optional: Convert to BGR if needed
    #     # # img = img[..., ::-1].copy()
    #         filename = f"image{i+1}.jpg"  # Customize filename and format
    #         cv2.imwrite(filename, img)

np.set_printoptions(suppress=True)

# Load the model
model = load_model("keras_model.h5", compile=False)

# Load the labels
class_names = open("labels.txt", "r").readlines()

# Create the array of the right shape to feed into the keras model
# The 'length' or number of images you can put into the array is
# determined by the first position in the shape tuple, in this case 1
data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)


def check(image):
    # Replace this with the path to your image
    # image = Image.open("marked/marked (35).jpg").convert("RGB")
    image = Image.open(image).convert("RGB")
    # image = Image.fromarray(image).convert('RGB')

    # resizing the image to be at least 224x224 and then cropping from the center
    size = (224, 224)
    image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)

    # turn the image into a numpy array
    image_array = np.asarray(image)

    # Normalize the image
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1

    # Load the image into the array
    data[0] = normalized_image_array

    # Predicts the model
    prediction = model.predict(data)
    index = np.argmax(prediction)
    # class_name = class_names[index]
    # confidence_score = prediction[0][index]

    # Print prediction and confidence score
    # print("Class:", class_name[2:], end="")
    # print("Confidence Score:", confidence_score)

    return 1 if index == 1 else 0


marks = []

for i, img in enumerate(crop_circles):
# Optional: Convert to BGR if needed
# img = img[..., ::-1].copy()
    filename = f"image{i+1}.jpg"  # Customize filename and format
    cv2.imwrite(filename, img)
    result = check(filename)
    marks.append(result)
    os.remove(filename)

# for box in crop_circles:
#     result = utilis.calculate_white_percentage(box)
#     marks.append(result)



markings = utilis.mark_list_reshape(marks)

pixels = utilis.pixelCount(crop_circles)

markingsVal = utilis.extract_and_reshape(markings)

checkedMarkings = utilis.check_and_replace(markingsVal)

pixelVal = utilis.extract_and_reshape(pixels)


#FINDING INDEX VALUES OF THE MARKINGS AND ANSWERS
ansIndex = utilis.locateAns(pixelVal, questions)
# print(ansIndex)

markIndex = utilis.locateAns(checkedMarkings, questions)
# Print the two columns
# for i, value in enumerate(markIndex):
#     print(f"{i + 1}\t{value}")

ansList = utilis.check_mirror_index(ansIndex, markIndex)
# print(ansList)

# GRADING
grading = utilis.grade(ansList, answers, questions)
# print(len(grading))

# EVALUATE SCORE
score = utilis.score(grading, questions)
# print(score)

# DISPLAY SCORE
imgRawGrade = np.zeros_like(imgScoreWarpColored)
cv2.putText(imgRawGrade, str(int(score))+"%" + ' '+ str(sum(grading))+ '/' + str(questions) , (0,80), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.5, (0,255,255),3)
invMatrixSc = cv2.getPerspectiveTransform(ptSc2,ptSc1)
imgScoreInv = cv2.warpPerspective(imgRawGrade,invMatrixSc,(widthImg,heightImg))

imgFinal = cv2.addWeighted(imgFinal, 1, imgScoreInv,1,0 )

imgResult = imgWarpColored.copy()
# imgResult = utilis.showAnswers(imgResult, ansIndex, grading, answers, questions, choices)

imgBlank = np.zeros_like(img)
imageArray = ([img2,imgGray2,imgBlur2, imgCanny2],
            [imgWarpCopy,imgWarpCopy2, imgWarpColored,gaus])
imgStacked = utilis.stackImages(0.5, imageArray)
# except:
    # imgBlank = np.zeros_like(img)
    # imageArray = ([img,imgGray,imgBlur, imgCanny],
    #                     [imgBlank,imgBlank, imgBlank,imgBlank])
    # imgStacked = utilis.stackImages(0.3, imageArray)

cv2.imshow("Results", imgFinal)
# cv2.imshow("Results", gaus)
cv2.imshow("Stacked images", imgStacked)
# if cv2.waitKey(1) & 0xFF == ord('s'):
#     cv2.imwrite("FinalResult.jpg", imgFinal)
#     cv2.waitKey(300)
cv2.waitKey(0)
