import numpy as np
import cv2
import sys, os
import subprocess

class Player(object):
    def __init__(self, verbose = False):
        self.window_name = 'video'
        self.trackbar_name = "frame"
        cv2.namedWindow('video')
        self.verbose = verbose

    def print_help(self):
        print("Use trackbar to scroll in video, 'f' to enter frame number, 'q' to quit.")

    def dispatch(self, key):
        if key == "f":
            new_frame = int(input("Frame: "))
            self.set_trackbar(new_frame)


    def open(self, path):
        if not os.path.exists(path):
            raise ValueError("No file {}".format(path))
        self.path = path
        self.filename = os.path.split(self.path)[1]
        self.basename, self.baseext = os.path.splitext(self.filename)

        cv2.setWindowTitle(self.window_name, self.filename)
        self.cap = cv2.VideoCapture(self.path)
        if not self.cap.isOpened():
            raise Exception("Could not open video {}".format(self.path))
        self.update_trackbar()

    def update_trackbar(self):
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if self.verbose:
            print("Total frames: {}".format(self.total_frames))
        cv2.createTrackbar(self.trackbar_name, self.window_name, 0, self.total_frames - 1, self.update_frame)
        self.update_frame(0)

    def set_trackbar(self, new_value):
        cv2.setTrackbarPos(self.trackbar_name, self.window_name, new_value)
        #self.update_frame(new_value)

    def update_frame(self, value):
        self.current_frame = value
        if self.verbose:
            print(self.current_frame)

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)

        success, frame = self.cap.read()
        if not success:
            raise Exception("Error")
        self.frame = frame
        cv2.imshow(self.window_name, self.frame)

    def run(self):
        while(True):
            key = chr(cv2.waitKey(0))
            self.dispatch(key)
            if key == 'q':
                break

class BaseCutter(Player):
    def __init__(self, outdir = "output"):
        super().__init__()
        self.start = None
        self.stop = None
        self.n_cuts = 0
        self.outdir = outdir
        os.makedirs(self.outdir, exist_ok = True)

    def dispatch(self, key):
        super().dispatch(key)
        if key == "s":
            self.cut()

    def make_output(self):
        raise NotImplemented()

    def cut(self):
        current_frame = cv2.getTrackbarPos(self.trackbar_name, self.window_name)
        if self.start is None:
            print("First frame: {}".format(current_frame))
            self.start = current_frame
            return
        print("Last frame: {}".format(current_frame))
        self.stop = current_frame

        if self.stop > self.start:
            self.make_output()
            self.n_cuts += 1
        else:
            print("Ignoring cut since stop <= start.")

        # reset
        self.start = None
        self.stop = None


class VidCutter(BaseCutter):
    def get_outfile(self):
        outname = self.basename + "_{:03}".format(self.n_cuts) + self.baseext
        return os.path.join(self.outdir, outname)

    def make_output(self):
        print("Cutting from frames {} to {}".format(self.start, self.stop))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        start_time = self.start / fps
        stop_time = self.stop / fps
        print("Cutting from time {} to {}".format(start_time, stop_time))
        duration = stop_time - start_time

        infile = self.path
        outfile = self.get_outfile()
        command = "ffmpeg -ss {start_time} -i {infile} -t {duration} -c copy {outfile}".format(
                start_time = start_time, duration = duration,
                infile = infile, outfile = outfile)
        print(command)
        subprocess.call(command, shell = True)


class ImgCutter(BaseCutter):
    def get_outfile(self):
        outname = self.basename + "_{:03}".format(self.n_cuts) + "_%06d.png"
        return os.path.join(self.outdir, outname)

    def make_output(self):
        print("Cutting from frames {} to {}".format(self.start, self.stop))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        start_time = self.start / fps
        stop_time = self.stop / fps
        print("Cutting from time {} to {}".format(start_time, stop_time))
        duration = stop_time - start_time

        infile = self.path
        outpattern = self.get_outfile()
        command = "ffmpeg -ss {start_time} -i {infile} -t {duration} {outpattern}".format(
                start_time = start_time, duration = duration,
                infile = infile, outpattern = outpattern)
        print(command)
        subprocess.call(command, shell = True)



if __name__ == "__main__":
    path = sys.argv[1]

    cut = ImgCutter()
    cut.print_help()
    cut.open(path)
    cut.run()
