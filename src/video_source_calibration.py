try:
    import cPickle as pickle
except ModuleNotFoundError:
    import pickle

import os
import glob
import cv2
import numpy as np
import cv2.aruco as aruco


class VideoSourceCalibration:

    def __init__(self, calibration_dir, video_source, chessboard_square_size):
        self.__criteria = (cv2.TERM_CRITERIA_EPS +
                           cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

        self.__calibration_dir = calibration_dir
        self.__video_source = video_source
        self.__chessboard_square_size = chessboard_square_size

    def calibrate(self):
        win_name = "Video Source Calibration Image Capture"
        cv2.namedWindow(win_name, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(
            win_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        red = (0, 0, 255)
        green = (0, 255, 0)

        #Descomentar quando nao for utilizar o DroidCam
        #video_capture = cv2.VideoCapture(self.__video_source, cv2.CAP_DSHOW)
        video_capture = cv2.VideoCapture(self.__video_source)

        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        calibration_frames = []
        ready_to_calibrate = False
        start_calibration = False
        status_color = red
        while True:
            option = cv2.waitKey(1)

            _, frame = video_capture.read()

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            cv2.putText(frame, "calibration image count: {}. Minimum 50".format(
                len(calibration_frames)), (0, 20), font, font_scale, status_color, 2, cv2.LINE_AA)

            cv2.putText(frame, "ENTER - Capture frame for calibration", (0, 40),
                        font, font_scale, green, 2, cv2.LINE_AA)

            if option == 13:
                found, _ = cv2.findChessboardCorners(gray, (9, 6), None)

                if found:
                    calibration_frames.append(gray)

            if ready_to_calibrate:
                cv2.putText(frame, "C - Start Calibration", (0, 60),
                            font, font_scale, green, 2, cv2.LINE_AA)

                if option == ord('c'):
                    start_calibration = True
                    cv2.putText(frame, "Running, this may take a while ...", (0, 80),
                                font, font_scale, green, 2, cv2.LINE_AA)

            cv2.putText(frame, "Q - Quit ", (0, 105), font,
                        font_scale, green, 2, cv2.LINE_AA)

            cv2.imshow(win_name, frame)

            if start_calibration:
                cv2.waitKey(2000)
                score = self.__run(calibration_frames)
                cv2.imshow(win_name, frame)
                cv2.waitKey(1000)
                video_capture.release()
                cv2.destroyAllWindows()
                return score

            if option == ord('q'):
                video_capture.release()
                cv2.destroyAllWindows()
                break

            if len(calibration_frames) >= 50:
                ready_to_calibrate = True
                status_color = green

    def __run(self, calibration_frames):
        objp = np.zeros((9*6, 3), np.float32)
        objp[:, :2] = np.mgrid[0:9, 0:6].T.reshape(-1, 2)*float(
            self.__chessboard_square_size)

        objpoints = []
        imgpoints = []

        img_size = calibration_frames[0].shape[::-1]
        for frame in calibration_frames:
            found, corners = cv2.findChessboardCorners(frame, (9, 6), None)
            if found:
                objpoints.append(objp)
                corners2 = cv2.cornerSubPix(
                    frame, corners, (11, 11), (-1, -1), self.__criteria)
                imgpoints.append(corners2)

        ret_val, cam_mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
            objpoints, imgpoints, img_size, None, None)

        if ret_val:
            mean_error = 0
            for i in range(len(objpoints)):
                imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], cam_mtx, dist)
                error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2)/len(imgpoints2)
                mean_error += error
            
            if not os.path.exists(self.__calibration_dir):
                os.makedirs(self.__calibration_dir)

            np.save('{}/cam_mtx.npy'.format(self.__calibration_dir), cam_mtx)
            np.save('{}/dist.npy'.format(self.__calibration_dir), dist)

            if (mean_error/len(objpoints)) < 1: 
                return 10 - 10*(mean_error/len(objpoints))
            else:
                return 0

    def test(self):
        win_name = "Calibration Test Image Capture"
        cv2.namedWindow(win_name, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(
            win_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        red = (0, 0, 255)
        green = (0, 255, 0)

        #if self.__calibration_dir.find('DroidCam_Source') != -1:
        #    video_capture = cv2.VideoCapture(self.__video_source)
        #else:
        #    video_capture = cv2.VideoCapture(self.__video_source, cv2.CAP_DSHOW)
        
        video_capture = cv2.VideoCapture(self.__video_source)

        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        calibration_frames = []
        ready_to_test = False
        start_test = False
        status_color = red
        while True:
            option = cv2.waitKey(1)

            _, frame = video_capture.read()

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            cv2.putText(frame, "test image count: {}. Minimum 10".format(
                len(calibration_frames)), (0, 20), font, font_scale, status_color, 2, cv2.LINE_AA)

            cv2.putText(frame, "ENTER - Capture frame for test", (0, 40),
                        font, font_scale, green, 2, cv2.LINE_AA)

            if option == 13:
                found, _ = cv2.findChessboardCorners(gray, (9, 6), None)

                if found:
                    calibration_frames.append(gray)

            if ready_to_test:
                cv2.putText(frame, "C - Start Test", (0, 60),
                            font, font_scale, green, 2, cv2.LINE_AA)

                if option == ord('c'):
                    start_test = True
                    cv2.putText(frame, "Running, this may take a while ...", (0, 80),
                                font, font_scale, green, 2, cv2.LINE_AA)

            cv2.putText(frame, "Q - Quit ", (0, 105), font,
                        font_scale, green, 2, cv2.LINE_AA)

            cv2.imshow(win_name, frame)

            if start_test:
                cv2.waitKey(2000)
                score = self.__run_test(calibration_frames)
                cv2.imshow(win_name, frame)
                cv2.waitKey(1000)
                video_capture.release()
                cv2.destroyAllWindows()
                return score

            if option == ord('q'):
                video_capture.release()
                cv2.destroyAllWindows()
                return -1

            if len(calibration_frames) >= 10:
                ready_to_test = True
                status_color = green

    def __run_test(self, calibration_frames):
        if os.path.exists('../assets/configs/') and os.path.isfile('../assets/configs/selected_cam_mtx.npy') and os.path.isfile('../assets/configs/selected_dist.npy'):
            cam_mtx = np.load(
                '../assets/configs/selected_cam_mtx.npy')
            dist = np.load(
                '../assets/configs/selected_dist.npy')
        
            objp = np.zeros((9*6, 3), np.float32)
            objp[:, :2] = np.mgrid[0:9, 0:6].T.reshape(-1, 2)*float(
                self.__chessboard_square_size)

            objpoints = []
            imgpoints = []
            rvecs = []
            tvecs = []

            for frame in calibration_frames:
                found, corners = cv2.findChessboardCorners(frame, (9, 6), None)
                if found:
                    objpoints.append(objp)
                    corners2 = cv2.cornerSubPix(
                        frame, corners, (11, 11), (-1, -1), self.__criteria)
                    imgpoints.append(corners2)
                    ret_val, rvec, tvec = cv2.solvePnP(objp, corners2, cam_mtx, dist)
                    rvecs.append(rvec)
                    tvecs.append(tvec)

            if ret_val:
                mean_error = 0
                for i in range(len(objpoints)):
                    imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], cam_mtx, dist)
                    error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2)/len(imgpoints2)
                    mean_error += error

                if (mean_error/len(objpoints)) < 1: 
                    return 10 - 10*(mean_error/len(objpoints))
                else:
                    return 0

class VideoSourceCalibrationConfig:

    def __init__(self, chessboard_square_size, score):
        self.chessboard_square_size = chessboard_square_size
        self.score = score

    @classmethod
    def persisted(cls, calibration_dir):
        if not os.path.exists('../assets/configs/'):
            os.makedirs('../assets/configs/')

        try:
            with open('{}/calibration_config_data.pkl'.format(calibration_dir), 'rb') as file:
                calibration_config_data = pickle.load(file)
                return cls(calibration_config_data['chessboard_square_size'],
                           calibration_config_data['score'])
        except FileNotFoundError:
            return cls("", 0)

    def persist(self, calibration_dir, score):
        # Overwrites any existing file.
        with open('{}/calibration_config_data.pkl'.format(calibration_dir), 'wb+') as output:
            pickle.dump({
                'chessboard_square_size': self.chessboard_square_size,
                'score': score}, output, pickle.HIGHEST_PROTOCOL)
