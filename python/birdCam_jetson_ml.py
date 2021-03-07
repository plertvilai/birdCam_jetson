#!/usr/bin/python

# library for Jetson Nano Bird Camera
# P. Lertvilai
# March 2021

import cv2
import os
import time
import sys
import numpy as np
import datetime
#from skimage import feature as sk
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.python.saved_model import tag_constants
from scipy import stats

className = ['Sparrow','Junco','Towhee','Blank']

#-------------General Functions-----------------#
def gstreamer_pipeline (capture_width=3280, capture_height=2464, display_width=1280, display_height=720, framerate=20, flip_method=0) :   
    return ('nvarguscamerasrc ! ' 
    'video/x-raw(memory:NVMM), '
    'width=(int)%d, height=(int)%d, '
    'format=(string)NV12, framerate=(fraction)%d/1 ! '
    'nvvidconv flip-method=%d ! '
    'video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! '
    'videoconvert ! '
    'video/x-raw, format=(string)BGR ! appsink '
    'max-buffers=60 drop=True'  % (capture_width,capture_height,framerate,flip_method,display_width,display_height))



#-------------BirdCam Class-----------------#
class birdCam():
	def __init__(self,imDim=(1280,720),fps=30,flip=0, scale=2, thresh=50,maxImSet = 10):
		# Gstreamer pipeline from camera setting
		self.gstream = gstreamer_pipeline(capture_width=imDim[0], capture_height=imDim[1],framerate=fps,flip_method=flip)

		# image processing
		self.scale = scale
		self.thresh = thresh
		self.xlim = [0,0] # X limit from background calibration
		self.fcnt = 0

		# time keeping
		self.time = time.time()
		self.birdTime = time.time()
		self.lostTime = time.time()
		self.bgTime = time.time()

		self.im_array = []
		self.maxImSet = maxImSet


		# flags
		self.flags = [False,False,False] # feeder_flag, bird_flag, capture_flag

	def initCam(self,vidFile=' '):
		'''
		Initialize opencv video capture.
		INPUT: 	vidFile = filename of video to run; if left blank, BirdCam uses gstreamer for capture
		OUTPUT: boolean True if successfully open video capture stream
		'''
		if vidFile==' ': # gstreamer mode
			print("Initialize gstreamer")
			print(self.gstream)
			self.cap = cv2.VideoCapture(self.gstream, cv2.CAP_GSTREAMER)
		else: # read from video file
			print("Initialize video")
			print(vidFile)
			self.cap = cv2.VideoCapture(vidFile)

		if not self.cap.isOpened(): # if fails to open gstreamer pipeline
			print("Unable to open camera.")
			print("Terminating program.")
			sys.exit("Unable to open camera")
		else:
			print("Successfully initialize camera stream.")
			return True

	def readFrame(self):
		'''Read one frame from stream.'''
		ret_val, frame = self.cap.read()
		self.fcnt = self.fcnt+1
		return ret_val, frame

	def bgCalibrate(self,bgim):
		'''Calibrate for background position of the feeder.
		INPUT:
		bgim = background image in RGB format.
		OUTPUT:
		min X index = minimum value of x index for cropping
		max X index = maximum value of x index for cropping.'''
		bgimg = cv2.cvtColor(bgim, cv2.COLOR_BGR2GRAY)
		w = bgimg.shape[1]
		bgcrop1 = bgimg[:,int(w*0.2):int(w*0.8)]
		ret,bgct = cv2.threshold(bgcrop1,self.thresh,255,cv2.THRESH_BINARY_INV)
		se = cv2.getStructuringElement(cv2.MORPH_RECT,(6,6))
		im_open = cv2.morphologyEx(bgct, cv2.MORPH_OPEN, se)
		ind = np.nonzero(im_open)
		self.xlim = [np.min(ind[1])+int(w*0.2) ,np.max(ind[1])+int(w*0.2)]
		return self.xlim

	def threshImage(self,frame,otsu=True):
		# crop image to region of interest only
		roi = frame[:,self.xlim[0]:self.xlim[1]]
		roi2 = cv2.resize(roi, (0,0), fx=1.0/self.scale, fy=1.0/self.scale) 
		# convert to grayscale
		roig = cv2.cvtColor(roi2, cv2.COLOR_BGR2GRAY)
		if otsu: # using Otsu method for thresholding
			blur = cv2.GaussianBlur(roig,(5,5),0)
			otsu_t,_ = cv2.threshold(blur,0,1,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
			_,threshIm = cv2.threshold(blur,otsu_t*0.7,1,cv2.THRESH_BINARY_INV)
		else:
			_,threshIm = cv2.threshold(roig,self.thresh,1,cv2.THRESH_BINARY_INV)
		# calculate sum of thresholded values
		val = np.sum(threshIm)
		return val, threshIm, roi

	def checkBgTime(self):
		return time.time()-self.bgTime

	def terminate(self):
		'''Terminate program gracefully. Use with SIGINT.'''
		print("Starting exit sequence")
		time.sleep(1)
		self.cap.release()
		time.sleep(1)
		print("Finished closing gstream pipeline...")
		print("Exiting gracefully")
		sys.exit()

	def updateTime(self):
		self.time = time.time()

	def resetFlags(self):
		self.flags = [False,False,False]

	def resetFcnt(self,val):
		self.fcnt = val

	def resetImSet(self):
		self.im_array = []

	def appendImSet(self,frame):
		if len(self.im_array)<self.maxImSet: # only add frame if the limit is not reached
			self.im_array.append(frame)

	def numImSet(self):
		return len(self.im_array)

	def getImSet(self,n):
		if n>=self.numImSet():
			return self.im_array[-1]
		else:
			return self.im_array[n]

class birdCam_trt(birdCam):
	def __init__(self,model_path):
		# inheriting properties from the main birdCam
		birdCam.__init__(self,imDim=(1280,720),fps=30,flip=0, scale=2, thresh=50,maxImSet = 10)
		self.model_path = model_path

	def initCNN(self,init_im_path=None):
		'''Initialize TensorFlow CNN model.'''
		print("Loading TensorRT model. This might take a while...")
		print("Start loading TRT model %s" %self.model_path)
		startT = time.time()
		saved_model_loaded = tf.saved_model.load(self.model_path, tags=[tag_constants.SERVING])
		endT = time.time()
		print("Finished loading model in %.2f s"%(endT-startT))

		signature_keys = list(saved_model_loaded.signatures.keys())
		print(signature_keys)

		self.infer = saved_model_loaded.signatures['serving_default']
		print(self.infer.structured_outputs)
		self.outputLayer = list(self.infer.structured_outputs.keys())[0] 

		if init_im_path != None: # if an init image is given, then initialize
			img = image.load_img(init_im_path, target_size=(224, 224))
			x = image.img_to_array(img)
			x = np.expand_dims(x, axis=0)
			x = preprocess_input(x)
			x = tf.constant(x)
			print("Start loading inference")
			startT = time.time()
			labeling = self.infer(x)
			endT = time.time()
			print("Finished loading inference in %.2f s"%(endT-startT))
		else:
			print("No init image is given. The model will run slowly the first inference.")
		return True

	def inference(self,frame):
		'''CNN inference. Return Class Number and confidence.'''
		x = cv2.resize(frame, (224,224)) 
		x = np.expand_dims(x, axis=0)
		x = preprocess_input(x)
		x = tf.constant(x)
		labeling = self.infer(x)
		#y_pred = labeling['predictions'].numpy()
		y_pred = labeling[self.outputLayer].numpy()
		ind = np.argmax(y_pred)
		print("%s: %.2f"%(className[ind],y_pred[0][ind]))
		return ind,y_pred[0][ind]

	def inferSet(self):
		y_array = np.array([])
		for im in self.im_array:
			ind,_ = self.inference(im)
			y_array = np.append(y_array,ind)
		m = stats.mode(y_array)
		print(m)
		return m[0][0],m[1][0]/len(y_array)


class birdCam_tflite(birdCam):
	def __init__(self,model_path):
		# inheriting properties from the main birdCam
		birdCam.__init__(self,imDim=(1280,720),fps=30,flip=0, scale=2, thresh=50,maxImSet = 10)
		self.model_path = model_path

	def initCNN(self,init_im_path=None):
		'''Initialize TensorFlow Lite CNN model.'''
		print("Load TF Lite model %s"%self.model_path)
		self.interpreter = tf.lite.Interpreter(model_path=self.model_path)
		print("Finish loading model.")
		self.interpreter.allocate_tensors()

		self.input_details = self.interpreter.get_input_details()
		self.output_details = self.interpreter.get_output_details()

		print(self.input_details)
		print(self.output_details)

		# check the type of the input tensor
		floating_model = self.input_details[0]['dtype'] == np.float32

		# NxHxWxC, H:1, W:2
		height = self.input_details[0]['shape'][1]
		width = self.input_details[0]['shape'][2]

		if init_im_path!=None:
			im = cv2.imread(init_im_path)
			self.inference(im)
			print("Finish loading inference.")
		else:
			print("No init image is given. The model will run slowly the first inference.")
		return True

	def inference(self,frame):
		'''CNN inference. Return Class Number and confidence.'''
		x = cv2.resize(frame, (224,224)) 
		x = np.expand_dims(x, axis=0)
		x = preprocess_input(x)
		input_data = tf.constant(x)
		self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
		self.interpreter.invoke()
		output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
		results = np.squeeze(output_data)
		ind = np.argmax(results)
		print("%s: %.2f"%(className[ind],results[ind]))
		return ind,results[ind]

	def inferSet(self):
		y_array = np.array([])
		for im in self.im_array:
			ind,_ = self.inference(im)
			y_array = np.append(y_array,ind)
		m = stats.mode(y_array)
		print(m)
		return m[0][0],m[1][0]/len(y_array)
