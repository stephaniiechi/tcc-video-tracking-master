import time
import cv2


class FpsTester:

    def __init__(self, source=0):
        self.video = cv2.VideoCapture(source)

    def run(self):

        frame_count = 0
        current_fps = 0
        while True:
            if(frame_count == 0):
                start = time.time()

            _, frame = self.video.read()
            frame_count += 1

            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(frame, "FPS: {:.2f}".format(current_fps), (0, 32), font,
                        0.6, (0, 255, 0), 2, cv2.LINE_AA)

            cv2.imshow("FPS TESTING", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            if(frame_count == 10):
                current_fps = (frame_count)/(time.time() - start)
                frame_count = 0


if __name__ == "__main__":

    fps_tester = FpsTester()
    fps_tester.run()
