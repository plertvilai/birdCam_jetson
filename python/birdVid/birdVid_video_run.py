import signal
from birdVid_jetson import *

# for gracefully terminate program with SIGINT
def terminateProcess(signalNumber, frame):
    global terminate # declare video capture from global variable
    terminate = True
    print('Received: SIGINT at %d'%time.time())
    print(terminate)
    return

# for SIGNINT interruption
terminate = False
signal.signal(signal.SIGINT, terminateProcess)

# for foreground mask cleanup
se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))

birdVid = videoDetector()

birdVid.initVideoStream(vidFile='1627193035.mp4')
birdVid.initOutputVideo('1627193035_out.mp4')
birdVid.initDetector()


srtT = time.time()
fcnt = 0
while True:

	fcnt = fcnt+1
	ret_val, frame = birdVid.getFrame()

	if frame is None:
		print("End of video file")
		break

	if not ret_val:
		print("Failed to read video frame")
		break

	if terminate:
		print("Terminate processing from SIGINT")
		break

	birdVid.detectForeground()
	birdVid.recordFrame()

birdVid.closeVideoStream()
birdVid.closeOutputVideo()

endT = time.time()
tt = endT - srtT

print("Finished processing video in %.2f s"%(tt))
print("Analyzed %d frames at the rate of %.2f s/frame"%(fcnt,tt/fcnt))