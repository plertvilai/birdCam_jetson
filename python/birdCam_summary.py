#!/usr/bin/python

import time
import argparse
import os
import datetime
import numpy as np
import sys
import glob
import pytz

# argument parser
parser = argparse.ArgumentParser(description = "BirdCam summary script")
parser.add_argument("-p", "--path", type=str,help="Path to the output folder")
parser.add_argument("-n", "--classNum", type=int,default=4,help="Number of classes")
args = parser.parse_args()

def checkFolder(folder_path,classNum=4):
	'''Initialize system.'''
	print("Checking output folder...")
	# check for images directory
	if not os.path.isdir(folder_path):
		print("Output folder not found. Please make sure to input valid folder.")
		return False

	if not os.path.isdir(folder_path+'bgimages'):
		print("Background folder not found.")
		return False

	for k in range(classNum):
		if not os.path.isdir(folder_path+"bird_%.2d/"%k):
			print("bird_%.2d folder not found."%k)
			return False
	print("All output folders are valid.")
	return True

def get_pst_time(unaware_dt):
	now_aware = pytz.utc.localize(unaware_dt)
	now_aware = now_aware.astimezone(pytz.timezone('US/Pacific'))
	return now_aware

def fname2dt(fname):
	fname = os.path.basename(fname)
	return int(fname[0:-4])

def extractDataDate(dataSet,target_date):
	sight = []
	for fname in dataSet:
		#print(fname2dt(fname))
		dt0 = datetime.datetime.utcfromtimestamp(fname2dt(fname))
		dt0 = get_pst_time(dt0)
		if dt0.strftime(timeStrFormat) == target_date:
			sight.append(dt0)
	return sight

def sortedGlob(path):
	return sorted(glob.glob(path), key=lambda x: int(os.path.basename(x)[0:-4]))

def folderSummarize(folder,dateStr):
	'''Summarize the information of the given folder in the given date.'''
	dataSet = sortedGlob(folder+'*.jpg')
	sight = extractDataDate(dataSet,dateStr)

	print('--------------------')
	print(folder)

	if len(sight)==0:
		print('Total sighting = %d'%len(sight))
	else:
		print('Total sighting = %d'%len(sight))
		print('First sight at %s'%sight[0].strftime('%H:%M'))
		print('Last sight at %s'%sight[-1].strftime('%H:%M'))


folder_path = args.path
# get current time
today = datetime.datetime.now()
today = get_pst_time(today)

timeStrFormat = '%d-%b-%y'

tdayStr = today.strftime(timeStrFormat)

print("BirdCam Summary of "+tdayStr)
print('--------------------')

if not checkFolder(folder_path,args.classNum):
	sys.exit("System exit: Folder not found.")

for k in range(args.classNum):
	folder = folder_path+"bird_%.2d/"%k
	folderSummarize(folder,tdayStr)
