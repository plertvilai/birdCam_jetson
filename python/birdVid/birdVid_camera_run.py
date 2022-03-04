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

birdVid = videoDetector(fgThresh=800)

birdVid.initVideoStream(fps=30)
# birdVid.initVideoStream(vidSize=(4000,3000),fps=30)
birdVid.initGSTOutputVideo('%d.mp4'%time.time())
# birdVid.initOutputVideo('test_out.mp4',fps=10)
birdVid.initDetector()


srtT = time.time()
fcnt = 0
while True:

	fcnt = fcnt+1
	ret_val, frame = birdVid.getFrame()

	if (frame is None) or (not ret_val):
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