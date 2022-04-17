# birdCam_ML_v2
# updated May 2021
# Use MobileNetV2 CNN for bird classification
# version 2 has 7 classes
# version 2.2 has functionality to turn on a device to deter rats at bird feeder

import cv2
import signal
import os
import time
import sys
import numpy as np
from birdCam_jetson_ml import *
import datetime
import requests

# GPIO Setup
import Jetson.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
pwr_pin =26 # pin for controlling device power
GPIO.setup(pwr_pin, GPIO.OUT, initial=GPIO.LOW)


base_folder = "/home/pichaya/birdCam_ML/"
output_folder = "/home/pichaya/birdCam_ML/ML06/"
model_path = '/home/pichaya/birdCam_ML/birdCam_MobileNetV2_20210530_TFTRT_FP16'
init_im_path = '/home/pichaya/birdCam_ML/last_sight.jpg'

# for gracefully terminate program with SIGINT
def terminateProcess(signalNumber, frame):
    global terminate # declare video capture from global variable
    terminate = True
    print('Received: SIGINT at %d'%time.time())
    print(terminate)
    return

def recordData(filename,data):
    file = open(filename,'a')
    file.write(data)
    file.close()

def uploadFile(filename,url):
    '''Upload video to server'''
    headers = requests.utils.default_headers()
    headers.update(
        {
            'User-Agent': 'My User Agent 1.0',
        }
    )
    data = {'password':'******', 'submit':'submit','ftype':'image'}
    files = {'my_file':(filename, open(filename, 'rb'))}    
    try:
        r = requests.post(url, data=data, files=files,headers = headers,timeout=5)
    except:
        print("Fail to upload data")
        return False
    print(r.text)
    return r.text=='OK'

def textImage(frame,species,confidence):
    # for putting text
    font = cv2.FONT_HERSHEY_SIMPLEX 
    org = (50, 50) 
    fontScale = 1
    color = (255, 0, 0) 
    thickness = 2
    if species == 0:
        text = "Sparrow   %.2f"%confidence
        imOut = cv2.putText(frame, text, org, font,fontScale, color, thickness, cv2.LINE_AA) 
    elif species == 1:
        text = "Junco   %.2f"%confidence
        imOut = cv2.putText(frame, text, org, font,fontScale, color, thickness, cv2.LINE_AA)
    else:
        text = "Towhee   %.2f"%confidence
        imOut = cv2.putText(frame, text, org, font,fontScale, color, thickness, cv2.LINE_AA) 
    return imOut

def outputFolderInit(classNum=4):
    '''Initialize system.'''
    global base_folder
    print("Initializing output folder...")
    # check for images directory
    if os.path.isdir(output_folder):
        print("Found images folder")
    else:
        print("Images folder not found. Creating the folder")
        os.system("mkdir %s"%output_folder)

    if os.path.isdir(output_folder+'bgimages'):
        print("Found images folder")
    else:
        print("Images folder not found. Creating the folder")
        os.system("mkdir %sbgimages"%output_folder)

    if os.path.isdir(output_folder+'blankIm'):
        print("Found images folder")
    else:
        print("Images folder not found. Creating the folder")
        os.system("mkdir %sblankIm"%output_folder)

    for k in range(classNum):
        if os.path.isdir(output_folder+"bird_%.2d/"%k):
            print("Found bird_%.2d folder"%k)
        else:
            print("Images folder not found. Creating the folder")
            os.system("mkdir %sbird_%.2d"%(output_folder,k))
    print("Done Initializing folder.")


# for SIGNINT interruption
terminate = False
signal.signal(signal.SIGINT, terminateProcess)

# url for uploading image
urlFile = '******'

print("-------BirdCam program----------")

# initialize output folder
outputFolderInit(classNum=7)

# initialize birdCam
className = ['Sparrow','Junco','Towhee','Juncojv','Rat','Snail','Blank']
print("Initializing BirdCam...")
birdCam = birdCam_trt(model_path,className = className, output_decoder = [6,1,4,5,3,0,2])
birdCam.initCNN(init_im_path) #initialize CNN model
birdCam.initCam() #initialize camera (has to be done after CNN initialization)
#birdCam.initCam(vidFile=base_folder+'1611933860.avi') # program exits if initialization fails


lostThresh = 3 # how long can bird gone before counting as new bird in seconds
picInterval = 0.5 # interval between image storage in seconds
dataFile = output_folder+"birdCam_ml06.dat"
first = True # for first run

bgTime = time.time()

blankTime = time.time()

nightTime = False # flag whether it is currently at night

valThresh = 12500
birdValThresh = 15000

birdCnt = 0 # for counting frames with bird
ratCnt = 0 # count number of frames that rat is in before turning pump on
ratCntThresh = 3

#---------- Main Loop of Camera----------------#
# the main loop runs until SIGINT is received.
ret_val = True # status of video stream
fcnt = 0
while ret_val:
    if terminate:
        birdCam.terminate()
        
    ret_val, frame = birdCam.readFrame()

    #print(birdCam.fcnt)

    if birdCam.fcnt<30: # wait for camera to stabilize
        continue

    # calibrate background
    if first:
        x1,x2 = birdCam.bgCalibrate(frame)
        print("Finished calibrating background")
        cv2.rectangle(frame, (x1, 0), (x2, 719), (255, 0, 0), 2)
        cv2.imwrite(output_folder+'bgimages/bg_%d.jpg'%time.time(),frame)
        first = False
    elif time.time()-bgTime>1800: # recalibrate background every half hour
        x1,x2 = birdCam.bgCalibrate(frame)
        print("Finished calibrating background")
        cv2.rectangle(frame, (x1, 0), (x2, 719), (255, 0, 0), 2)
        cv2.imwrite(output_folder+'bgimages/bg_%d.jpg'%time.time(),frame)
        bgTime = time.time()

    # check whether it is night time
    # tnow = datetime.datetime.now() # get current time in datetime format
    # h = tnow.hour
    # if h<6 or h>18: # if night time then skip taking pictures
    #     print("Currently nighttime. Skip imaging")
    #     continue

    # crop image to region of interest only
    roi = birdCam.getRoi(frame)
    # infer the bird in background
    species,confidence = birdCam.inference(roi)

    # when bird found in frame, wait for 10 frames to confirm that bird is actually present
    if birdCam.isBird(species) and birdCnt<10:
        birdCnt = birdCnt+1
    elif (time.time()-blankTime)>15*60: # take blank
        cv2.imwrite(output_folder+'blankIm/%d.jpg'%time.time(),roi)
        blankTime = time.time()
    else:
        continue

    print("Found bird!!!")
    birdCam.updateTime()
    startT = time.time()
    lostTime = time.time()
    lastPicT = time.time()
    birdCam.resetImSet() # initialize image array
    birdCam.resetDataArray()
    birdCam.flags = [True,True,False] #update flags
    birdCam.appendDataArray(np.array([[species,confidence]])) # append to data array
    ratCnt = 0 # reset rat count

    #------- Main loop while bird is present at feeder -----------#
    while(1): 
        ret_val, frame = birdCam.readFrame() # read new frame

        roi = birdCam.getRoi(frame)

        species,confidence = birdCam.inference(roi)

        if species==5 and confidence>0.4:
            ratCnt = ratCnt + 1

        # reset rat counter if other species is found instead
        if species!=5 and confidence>0.3:
            ratCnt = 0 

        print(ratCnt)
        


        if birdCam.isBird(species) and not birdCam.flags[2]: # take first image
            lastPicT = time.time() # update time image taken
            print("-----Taking picture--------")
            birdCam.appendImSet(roi) # add roi to image array
            birdCam.flags[2] = True # update flag
            birdCam.appendDataArray(np.array([[species,confidence]])) # append to data array

            # for detering rat
            if ratCnt>=ratCntThresh: # turn on after 4 frames
                GPIO.output(pwr_pin, GPIO.HIGH)




        elif birdCam.isBird(species) and (time.time()-lastPicT>picInterval): # take new image as time passes
            print('Still seeing...')
            lastPicT = time.time() # update time image taken
            birdCam.appendImSet(roi) # add roi to image array
            birdCam.flags[1] = True
            birdCam.appendDataArray(np.array([[species,confidence]])) # append to data array

            # for detering rat
            if ratCnt>=ratCntThresh: # turn on after 4 frames
                GPIO.output(pwr_pin, GPIO.HIGH)

            

        elif birdCam.isBird(species): # still seeing bird
            print('Still seeing...')
            birdCam.flags[1] = True
            birdCam.appendDataArray(np.array([[species,confidence]])) # append to data array

            # for detering rat
            if ratCnt>=ratCntThresh: # turn on after 4 frames
                GPIO.output(pwr_pin, GPIO.HIGH)


        elif birdCam.flags[1]: # bird initially gone from frame
            print("Bird leaving...")
            lostTime = time.time()
            birdCam.flags[1] = False

            # for detering rat
            GPIO.output(pwr_pin, GPIO.LOW)

        elif time.time()-lostTime > lostThresh: # bird gone too long
            print('Bird gone...')
            birdCam.resetFlags() # reset flags
            birdCam.resetFcnt(40)  # reset frame counter
            birdCnt = 0
            if birdCam.numImSet()>0:
                roi_save = birdCam.getImSet(3)
                # inference
                species_final,confidence_final = birdCam.modeDataArray() # inference from all images in the set
                cv2.imwrite(output_folder+'bird_%02d/%d.jpg'%(species_final,birdCam.time),roi_save)

                # record data
                dataStr = "%d,%d,%.2f,%.2f\n"%(birdCam.time,species_final,confidence,time.time()-birdCam.time)
                recordData(dataFile,dataStr)

                # upload data to server
                imText = textImage(roi_save,species,confidence)
                fname = base_folder+'last_sight.jpg'
                cv2.imwrite(fname,imText)
                uploadFile(fname,urlFile)
            else:
                print("No valid picture. Skip inference.")

            # for detering rat
            GPIO.output(pwr_pin, GPIO.LOW)


            break # end while loop for this detection
        else:
            print("Bird still missing...")



    



