function processVideo(vidname,outputname,compress,fps,curTime,frame2read)



disp(frame2read)

v = VideoReader(vidname,'CurrentTime',curTime);

outputVideo = VideoWriter(outputname,'MPEG-4');
outputVideo.FrameRate = fps;
open(outputVideo)

fcnt = 0;

fprintf('Start writing video ......\n')
tic;
while hasFrame(v)
    
    fcnt = fcnt+1;
    
    if mod(fcnt,1000)==0
        fprintf('Current frame = %d\n',fcnt);
    end
    
    frame = readFrame(v);

    
    if fcnt>frame2read
        break;
    end
    
    
    
    imOut = imresize(frame, compress);
    writeVideo(outputVideo,imOut);
    
end

close(outputVideo)
b = toc;

fprintf('Finished writing video in %.1f s.\n',b)

    
    
    
    
    
    
    
    