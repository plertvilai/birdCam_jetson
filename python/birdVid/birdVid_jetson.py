#!/usr/bin/python

# library for Jetson Nano Bird Camera motion detection video
# P. Lertvilai
# July 2021

import sys
import numpy as np
import cv2
import subprocess
import glob
import os
from datetime import datetime
import time
from datetime import datetime # for converting timestamp to readable format
import pytz # for timezone in datetime


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

def tstmp2dt(tstmp,tz = "America/Los_Angeles"):
  '''Convert unix timestamp to a datetime object with timezone.'''
  timezone = pytz.timezone(tz)
  dt_object = datetime.fromtimestamp(int(tstmp))
  utc_now = pytz.utc.localize(dt_object)
  return utc_now.astimezone(timezone)

# def addTstamp2Im(im,tstamp,org=(50,50),color=(0, 255, 255),fontScale=1.25,thickness=2,format = "%H:%M %d/%b/%y"):
#   '''Add a timestamp to an image.
#   tstamp = unix timestamp in string format.'''
#   dt = tstmp2dt(tstamp)
#   text = dt.strftime(format)
#   # font
#   font = cv2.FONT_HERSHEY_SIMPLEX
#   # Using cv2.putText() method
#   return cv2.putText(im, text, org, font, 
#                     fontScale, color, thickness, cv2.LINE_AA)

def addTstamp2Im(im,org=(50,50),color=(0, 255, 255),fontScale=1.25,thickness=2,format = "%H:%M %d/%b/%y"):
  '''Add a timestamp to an image.
  tstamp = unix timestamp in string format.'''
  dt = datetime.now()
  text = dt.strftime(format)
  # font
  font = cv2.FONT_HERSHEY_SIMPLEX
  # Using cv2.putText() method
  return cv2.putText(im, text, org, font, 
                    fontScale, color, thickness, cv2.LINE_AA)

class videoDetector():

	def __init__(self,output_type='frame',fgThresh=150,contDetectThresh=60,max_invis_frames=90):
		self.fgThresh = fgThresh
		self.contDetectThresh = contDetectThresh
		# self.se_array = se_array
		
		self.max_invis_frames = max_invis_frames
		self.output_type = output_type

	def initVideoStream(self,vidSize=(1920,1080),fps=30,vidFile=' '):
		'''
		Initialize opencv video capture.
		INPUT: 	vidFile = filename of video to run; if left blank, BirdCam uses gstreamer for capture
		OUTPUT: boolean True if successfully open video capture stream
		'''
		self.gstream = gstreamer_pipeline(capture_width=vidSize[0], capture_height=vidSize[1], display_width=vidSize[0], display_height=vidSize[1],framerate=fps)
		self.vidSize = vidSize
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
			self.w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
			self.h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
			self.fps = self.cap.get(cv2.CAP_PROP_FPS)
			print('-------------------------')
			print('Src opened, %dx%d @ %d fps' % (self.w, self.h, self.fps))
			print('-------------------------')
			return True

	def closeVideoStream(self):
		self.cap.release()

	def getFrame(self):
		ret_val, frame = self.cap.read()
		self.frame = frame
		return ret_val,frame

	def initOutputVideo(self,output_vidname,fps=10.0,vidSize=(1920,1080)):
		self.output_vidname = output_vidname
		fourcc = cv2.VideoWriter_fourcc(*'MP4V')
		self.output_vid = cv2.VideoWriter(self.output_vidname,fourcc, fps, vidSize)
		self.output_vidSize = vidSize

	def initGSTOutputVideo(self,output_vidname,fps=10.0,vidSize=(1920,1080)):
		self.output_vidname = output_vidname
		gst_out = ("appsrc ! video/x-raw, format=BGR ! queue !"
		" videoconvert ! video/x-raw,format=BGRx ! nvvidconv !"
		" nvv4l2h264enc ! h264parse ! matroskamux ! filesink location=%s ")%output_vidname
		self.output_vid = cv2.VideoWriter(gst_out, cv2.CAP_GSTREAMER, 0, float(self.fps), (int(self.w), int(self.h)))
		if not self.output_vid.isOpened():
			print("Failed to open output")
			exit()

		self.output_vidSize = vidSize

	def closeOutputVideo(self):
		self.output_vid.release()

	def initDetector(self):
		self.fgbg = cv2.createBackgroundSubtractorMOG2()
		# detection frame counter handlers
		self.detect_frames = 0
		self.invis_frames = 0
		self.recordStat = False
		self.motion_frames = 0

	def detectForeground(self,scale=4):
		fsmall = cv2.resize(self.frame,(int(self.vidSize[0]/scale),int(self.vidSize[1]/scale)))
		fgmask = self.fgbg.apply(fsmall)
		ret,mask = cv2.threshold(fgmask,250,255,cv2.THRESH_BINARY)
		# im_open = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.se_array[0])
		# mask = im_open
		print('%.2f,%.1f'%(time.time(),np.sum(mask)/255))
		# if foreground pixles are more than threshold, then add to counter 
		if np.sum(mask)/255>=self.fgThresh: 
			self.detect_frames = self.detect_frames+1
			self.invis_frames = 0 # reset invis frame counter
		elif self.recordStat: # if we are currently recording,
			if self.invis_frames > self.max_invis_frames: # if invis frames exceed max, then 
				self.recordStat = False # stop recording
				self.detect_frames = 0 # reset detected frame count
			self.invis_frames = self.invis_frames + 1 # if not exceed, then add a counter to invis

		if self.detect_frames >= self.contDetectThresh:
			self.recordStat = True

	def recordFrame(self):
		# recording
		if self.recordStat:
			self.motion_frames = self.motion_frames+1
			if self.output_type=='mask':
				mask2 = cv2.resize(self.mask,self.output_vidSize)
				mask3 = np.zeros((self.output_vidSize[0],self.output_vidSize[1]))
				mask3[:,:,0] = mask2
				mask3[:,:,1] = mask2
				mask3[:,:,2] = mask2
				self.output_vid.write(addTstamp2Im(mask3))
			else:
				#frame = cv2.resize(self.frame,(self.output_vidSize[0],self.output_vidSize[1]))
				self.output_vid.write(addTstamp2Im(self.frame))
				# self.output_vid.write(self.frame)