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


class ScriptMixin(object):
    def append_command(self, command):
        scriptfile = os.path.join(self.outdir, "onescripttocutthemall.sh")
        with open(scriptfile, "a") as f:
            f.write(command + "\n")


class VidCutter(BaseCutter, ScriptMixin):
    def __init__(self, outdir = "output", generate_script = False):
        super().__init__(outdir)
        self.generate_script = generate_script

    def print_help(self):
        super().print_help()
        if self.generate_script:
            print("Press 's' once to set starting point, then again 's' to")
            print("set end point and produce the cutting script which produces")
            print("videos.")
        else:
            print("Press 's' once to set starting point, then again 's' to")
            print("set end point and produce the cut video.")

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
        command = "ffmpeg -ss {start_time} -i '{infile}' -t {duration} '{outfile}'".format(
                start_time = start_time, duration = duration,
                infile = infile, outfile = outfile)
        print(command)
        if self.generate_script:
            self.append_command(command)
        else:
            subprocess.call(command, shell = True)


class ImgCutter(BaseCutter, ScriptMixin):
    def __init__(self, outdir = "output", generate_script = False):
        super().__init__(outdir)
        self.generate_script = generate_script

    def print_help(self):
        super().print_help()
        if self.generate_script:
            print("Press 's' once to set starting point, then again 's' to")
            print("set end point and produce the cutting script which produces")
            print("images.")
        else:
            print("Press 's' once to set starting point, then again 's' to")
            print("set end point and produce the cut images.")

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
        command = "ffmpeg -ss {start_time} -i '{infile}' -t {duration} '{outpattern}'".format(
                start_time = start_time, duration = duration,
                infile = infile, outpattern = outpattern)
        print(command)
        if self.generate_script:
            self.append_command(command)
        else:
            subprocess.call(command, shell = True)



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--mode",
            metavar = "mode", choices = ["vids", "imgs"], default = "vids", help="produce images or videos")
    parser.add_argument("-s", "--script",
            action = "store_true", help = "produce script instead of cutting immediately")
    parser.add_argument("path",
            metavar = "video", help = "path to video to cut")
    opt = parser.parse_args()

    path = opt.path

    if opt.mode == "imgs":
        cut = ImgCutter(generate_script = opt.script)
    elif opt.mode == "vids":
        cut = VidCutter(generate_script = opt.script)
    cut.print_help()
    cut.open(path)
    cut.run()
