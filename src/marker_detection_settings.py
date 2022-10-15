try:
    import cPickle as pickle
except ModuleNotFoundError:
    import pickle

import os
import statistics
import cv2
import numpy as np
import cv2.aruco as aruco

CUBE_DETECTION = "MARKERS CUBE"
SINGLE_DETECTION = "SINGLE MARKER"


class SingleMarkerDetectionSettings():

    def __init__(self, marker_length, marker_id):
        self.identifier = SINGLE_DETECTION
        self.marker_length = marker_length
        self.marker_id = marker_id

    def persist(self):
        # Overwrites any existing file.
        with open('../assets/configs/single_marker.pkl', 'wb+') as output:
            pickle.dump({
                'marker_length': self.marker_length,
                'marker_id': self.marker_id}, output, pickle.HIGHEST_PROTOCOL)

    @classmethod
    def persisted(cls):
        if not os.path.exists('../assets/configs/'):
            os.makedirs('../assets/configs/')

        try:
            with open('../assets/configs/single_marker.pkl', 'rb') as file:
                settings = pickle.load(file)

                return cls(settings['marker_length'],
                           settings['marker_id'])

        except FileNotFoundError:
            return cls("13.2", "0")


class MarkersCubeDetectionSettings():

    def __init__(self, markers_length, up_marker_id, side_marker_ids, down_marker_id, transformations):
        self.identifier = CUBE_DETECTION
        self.markers_length = markers_length
        self.up_marker_id = up_marker_id
        self.side_marker_ids = side_marker_ids
        self.down_marker_id = down_marker_id
        self.transformations = transformations

    def persist(self, cube_id):
        # Overwrites any existing file.
        with open('../assets/configs/marker_cubes/{}.pkl'.format(cube_id), 'wb+') as output:
            pickle.dump({
                'markers_length': self.markers_length,
                'up_marker_id': self.up_marker_id,
                'side_marker_ids': self.side_marker_ids,
                'down_marker_id': self.down_marker_id,
                'transformations': self.transformations}, output, pickle.HIGHEST_PROTOCOL)

    @classmethod
    def persisted(cls, cube_id):
        if not os.path.exists('../assets/configs/marker_cubes/'):
            os.makedirs('../assets/configs/marker_cubes/')

        try:
            with open('../assets/configs/marker_cubes/{}.pkl'.format(cube_id), 'rb') as file:
                settings = pickle.load(file)

                return cls(settings['markers_length'],
                           settings['up_marker_id'],
                           settings['side_marker_ids'],
                           settings['down_marker_id'],
                           settings['transformations'])

        except FileNotFoundError:
            return cls("", "", ["", "", "", ""], "", None)


class MarkerCubeMapping:

    def __init__(self, cube_id, calibration_name, video_source, markers_length, up_marker_id, side_marker_ids, down_marker_id, database_calibrations):
        self.__cube_id = cube_id
        self.__calibration_name = calibration_name
        self.__calibration_dir = '{}/{}'.format('../assets/camera_calibration_data', calibration_name)
        self.__video_source = video_source
        self.__markers_length = markers_length
        self.__up_marker_id = up_marker_id
        self.__side_marker_ids = []
        for side_marker_id in side_marker_ids:
            if side_marker_id != "":
                self.__side_marker_ids.append(int(side_marker_id))
            else:
                self.__side_marker_ids.append(side_marker_id)

        if down_marker_id != "":
            self.__down_marker_id = int(down_marker_id)
        else:
            self.__down_marker_id = down_marker_id

        self.__acquire_min_count = 100
        self.__database_calibrations = database_calibrations

    def map(self):
        side_up_transformations = {}
        if self.__down_marker_id != "":
            down_side_transformations = {}
        for side_marker_id in self.__side_marker_ids:
            if side_marker_id != "":
                side_up_transformations[side_marker_id] = []
                if self.__down_marker_id != "":
                    down_side_transformations[side_marker_id] = []
        if os.path.exists(self.__calibration_dir) and os.path.isfile("{}/cam_mtx.npy".format(self.__calibration_dir)) and os.path.isfile("{}/dist.npy".format(self.__calibration_dir)):
            cam_mtx = np.load(
                "{}/cam_mtx.npy".format(self.__calibration_dir))
            print(cam_mtx)
            dist = np.load(
                "{}/dist.npy".format(self.__calibration_dir))
        else:
            for calibration in self.__database_calibrations:
                if calibration.to_dict().get('name', '') == self.__calibration_name:
                    calibration_dict = calibration.to_dict()
                    cam_mtx = np.array([[calibration_dict['camera matrix'][0], 0                              ,  calibration_dict['camera matrix'][2]],
                                        [0                              , calibration_dict['camera matrix'][1],  calibration_dict['camera matrix'][3]],
                                        [0                              , 0                              , 1                               ]])
                    dist = np.array([calibration_dict['distortion coefficients']])

        win_name = "Markers Cube Calibration Image Capture"
        cv2.namedWindow(win_name, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(
            win_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        #Descomentar quando nao for utilizar o DroidCam
        #video_capture = cv2.VideoCapture(self.__video_source, cv2.CAP_DSHOW)
        video_capture = cv2.VideoCapture(self.__video_source)

        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        while True:
            _, frame = video_capture.read()

            done = True
            for side_marker_id in self.__side_marker_ids:
                if side_marker_id != "":
                    done &= len(
                        side_up_transformations[side_marker_id]) == self.__acquire_min_count
                    
                    if self.__down_marker_id != "":
                        done &= len(
                            down_side_transformations[side_marker_id]) == self.__acquire_min_count

            if not done:
                corners, ids = self.__detect_markers(frame)

                font = cv2.FONT_HERSHEY_SIMPLEX
                scale = 0.6
                blue = (255, 0, 0)
                red = (0, 0, 255)
                green = (0, 255, 0)

                if np.all(ids is not None):
                    rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(
                        corners, float(self.__markers_length), cam_mtx, dist)

                    up_marker_index = None
                    down_marker_index = None
                    side_marker_index = None
                    for i in range(0, ids.size):
                        if ids[i][0] == self.__up_marker_id:
                            up_marker_index = i
                        elif ids[i][0] == self.__down_marker_id:
                            down_marker_index = i
                        elif side_marker_index is None or tvecs[side_marker_index][0][2] > tvecs[i][0][2]:
                            side_marker_index = i
                        else:
                            pass

                    target_marker_index = None
                    other_marker_index = None
                    destination_index = None
                    transformation_destination = None
                    if up_marker_index is not None and side_marker_index is not None:
                        target_marker_index = up_marker_index
                        other_marker_index = side_marker_index
                        destination_index = side_marker_index
                        transformation_destination = side_up_transformations
                    elif down_marker_index is not None and side_marker_index is not None:
                        target_marker_index = side_marker_index
                        other_marker_index = down_marker_index
                        destination_index = side_marker_index
                        transformation_destination = down_side_transformations

                    if target_marker_index is not None and other_marker_index is not None and destination_index is not None and transformation_destination is not None:
                        cv2.putText(frame, "marker {} -> marker {} mapping".format(
                            ids[other_marker_index][0], ids[target_marker_index][0]), (0, 20), font, scale, blue, 2, cv2.LINE_AA)

                        acquired_transformations_count = len(
                            transformation_destination[ids[destination_index][0]])
                        if acquired_transformations_count < self.__acquire_min_count:
                            cv2.putText(frame, "Count: {}".format(
                                acquired_transformations_count), (0, 40), font, scale, red, 2, cv2.LINE_AA)

                            target_marker_transformation = self.__get_transformation_matrix(
                                rvecs[target_marker_index], tvecs[target_marker_index])
                            other_marker_transformation = self.__get_transformation_matrix(
                                rvecs[other_marker_index], tvecs[other_marker_index])
                            transformation_other_to_target = np.dot(np.linalg.inv(
                                other_marker_transformation), target_marker_transformation)

                            acquire = {}
                            acquire["target"] = target_marker_transformation
                            acquire["other"] = other_marker_transformation
                            acquire["other_to_target"] = transformation_other_to_target
                            transformation_destination[ids[destination_index][0]].append(
                                acquire)

                        else:
                            cv2.putText(frame, "Done!", (0, 40),
                                        font, scale, green, 2, cv2.LINE_AA)

                cv2.putText(frame, "Q - Quit ", (0, 65), font,
                            scale, blue, 2, cv2.LINE_AA)

                cv2.imshow(win_name, frame)

            else:
                cv2.putText(frame, "Markers cube mapping finished, saving ...", (0, 40), font,
                            scale, green, 2, cv2.LINE_AA)

                cv2.imshow(win_name, frame)
                cv2.waitKey(1000)

                if self.__down_marker_id != "":
                    transformations = self.__compute_transformations(
                        side_up_transformations, down_side_transformations)
                else:
                    transformations = self.__compute_transformations(
                        side_up_transformations)

                settings = MarkersCubeDetectionSettings(
                    self.__markers_length, self.__up_marker_id, self.__side_marker_ids, self.__down_marker_id, transformations)
                settings.persist(self.__cube_id)

                cv2.waitKey(1000)
                video_capture.release()
                cv2.destroyAllWindows()
                break

            pressed_key = cv2.waitKey(1)
            if pressed_key == ord('q'):
                video_capture.release()
                cv2.destroyAllWindows()
                break

    def __detect_markers(self, frame):
        parameters = aruco.DetectorParameters_create()
        parameters.adaptiveThreshConstant = 7
        parameters.cornerRefinementMethod = aruco.CORNER_REFINE_CONTOUR

        corners, ids, _ = aruco.detectMarkers(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
            aruco.Dictionary_get(aruco.DICT_6X6_250),
            parameters=parameters)

        aruco.drawDetectedMarkers(frame, corners)

        return corners, ids

    def __get_transformation_matrix(self, rvec, tvec):
        rot_mtx = np.zeros(shape=(3, 3))
        cv2.Rodrigues(rvec, rot_mtx)

        transformation = np.concatenate(
            (rot_mtx, np.transpose(tvec)), axis=1)
        transformation = np.concatenate(
            (transformation, np.array([[0, 0, 0, 1]])))

        return transformation

    def __compute_transformations(self, side_up_transformations, down_side_transformations=None):
        transformations = {}
        side_up_transformation_errors = {}

        for side_marker_id in self.__side_marker_ids:
            if side_marker_id != "":
                best_transformation, error = self.__find_best_transformation(
                    side_up_transformations[side_marker_id])

                transformations[side_marker_id] = best_transformation
                side_up_transformation_errors[side_marker_id] = error

        best_down_up_transformation = np.zeros(shape=(4, 4))
        min_error = None
        if down_side_transformations is not None:
            for side_marker_id in self.__side_marker_ids:
                if side_marker_id != "":
                    best_down_side_transformation, error = self.__find_best_transformation(
                        down_side_transformations[side_marker_id])

                    if min_error is None or min_error > side_up_transformation_errors[side_marker_id] + error:
                        best_down_up_transformation = np.dot(
                            best_down_side_transformation, transformations[side_marker_id])
                        min_error = side_up_transformation_errors[side_marker_id] + error

            transformations[self.__down_marker_id] = best_down_up_transformation

        return transformations

    def __find_best_transformation(self, transformations):
        best_transformation = np.zeros(shape=(4, 4))
        rows_count, cols_count = best_transformation.shape
        min_error = None

        for testing_transformation in transformations:
            local_errors = []
            for transformation in transformations:
                local_error = 0
                calculated_result = np.dot(
                    transformation["other"], testing_transformation["other_to_target"])

                for row in range(0, rows_count):
                    for col in range(0, cols_count):
                        local_error += (transformation["target"][row][col] -
                                        calculated_result[row][col])**2

                local_errors.append(local_error)

            local_errors_mean = statistics.mean(local_errors)
            if min_error is None or min_error > local_errors_mean:
                best_transformation = testing_transformation["other_to_target"]
                min_error = local_errors_mean

        return best_transformation, min_error
