import os
import signal
import subprocess
import time
import argparse

#--------------Argument Parser-----------------------#
parser = argparse.ArgumentParser(description = "NVIDIA JETSON GSTREAMER VIDEO CONTROLLER")
parser.add_argument("-f", "--format", type=str, default="mp4",help="Select video format: mp4 or avi")
parser.add_argument("-t", "--duration", type=int, default=10,help="Select duration of recording in seconds")
parser.add_argument("-o", "--output", type=str, default=" ",help="Output filename without extension")
parser.add_argument("-s", "--shutter", type=int, default=1000,help="Exposure time in microseconds")
parser.add_argument("-ag", "--again", type=int, default=4,help="Analog gain")
parser.add_argument("-dg", "--dgain", type=int, default=4,help="Digital gain")
parser.add_argument("-dc", "--dualcam", type=bool, default=False,help="Select True to run dual cameras")
parser.add_argument("-fps", "--framerate", type=int, default=30,help="Select framerate in fps")
parser.add_argument("-ww", "--width", type=int, default=4032,help="Image width. Default 4032.")
parser.add_argument("-hh", "--height", type=int, default=3040,help="Image height. Default 3040.")

args = parser.parse_args()

if args.output==" ":
    output_name = str(time.time())
else:
    output_name = args.output

if args.format=='mp4' or args.format=='MP4':
    cmd0 =("gst-launch-1.0 -e nvarguscamerasrc sensor-id=0 "
        "gainrange=\"%d %d\" ispdigitalgainrange=\"%d %d\" exposuretimerange=\"%d %d\" "
        "! \"video/x-raw(memory:NVMM),width=%d,height=%d,framerate=%d/1\" !"
        " nvv4l2h264enc ! h264parse ! mp4mux ! filesink location=%s_0.mp4") %(args.again,
        args.again,args.dgain,args.dgain,args.shutter*1000,args.shutter*1000,
        args.width,args.height,args.framerate,output_name)
    cmd1 =("gst-launch-1.0 -e nvarguscamerasrc sensor-id=1 "
        "gainrange=\"%d %d\" ispdigitalgainrange=\"%d %d\" exposuretimerange=\"%d %d\" "
        "! \"video/x-raw(memory:NVMM),width=%d,height=%d,framerate=%d/1\" !"
        " nvv4l2h264enc ! h264parse ! mp4mux ! filesink location=%s_1.mp4") %(args.again,
        args.again,args.dgain,args.dgain,args.shutter*1000,args.shutter*1000,
        args.width,args.height,args.framerate,output_name)

elif args.format=='avi' or args.format=='AVI':
    cmd0 =("gst-launch-1.0 -e nvarguscamerasrc sensor-id=0 "
        "gainrange=\"%d %d\" ispdigitalgainrange=\"%d %d\" exposuretimerange=\"%d %d\" "
        "! \"video/x-raw(memory:NVMM),width=%d,height=%d,framerate=%d/1\" !"
        " nvjpegenc ! avimux ! filesink location=%s_0.avi") %(args.again,
        args.again,args.dgain,args.dgain,args.shutter*1000,args.shutter*1000,
        args.width,args.height,args.framerate,output_name)
    cmd1 =("gst-launch-1.0 -e nvarguscamerasrc sensor-id=1 "
        "gainrange=\"%d %d\" ispdigitalgainrange=\"%d %d\" exposuretimerange=\"%d %d\" "
        "! \"video/x-raw(memory:NVMM),width=%d,height=%d,framerate=%d/1\" !"
        " nvjpegenc ! avimux ! filesink location=%s_1.avi") %(args.again,
        args.again,args.dgain,args.dgain,args.shutter*1000,args.shutter*1000,
        args.width,args.height,args.framerate,output_name)

    cmd0 =("gst-launch-1.0 -e nvarguscamerasrc sensor-id=0 !"
        " \"video/x-raw(memory:NVMM),width=4032,height=3040,framerate=30/1\" !"
        " nvjpegenc ! avimux ! filesink location=%s_0.avi") %(args.output)
    cmd1 =("gst-launch-1.0 -e nvarguscamerasrc sensor-id=1 !"
        " \"video/x-raw(memory:NVMM),width=4032,height=3040,framerate=30/1\" !"
        " nvjpegenc ! avimux ! filesink location=%s_1.avi") %(args.output)
else:
    print("Invalid requested video format. Please select MP4 or AVI")
    quit()

print(cmd0)
if args.dualcam:
    print(cmd1)

process0 = subprocess.Popen(cmd0, shell = True)

if args.dualcam:
    process1 = subprocess.Popen(cmd1, shell = True)

time.sleep(args.duration+4)

os.killpg(os.getpgid(process0.pid), signal.SIGINT)

if args.dualcam:
    os.killpg(os.getpgid(process1.pid), signal.SIGINT)