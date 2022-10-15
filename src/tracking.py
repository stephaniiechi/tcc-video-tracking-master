try:
    import cPickle as pickle
except ModuleNotFoundError:
    import pickle
    
import os
import json
import socket
import websockets
import asyncio
from multiprocessing import Process, Queue
import time
import math
import numpy as np
import cv2
import cv2.aruco as aruco
from marker_detection_settings import SINGLE_DETECTION, CUBE_DETECTION

class TrackingScheduler:
    def __init__(self, start_tracking, stop_tracking):
        self.start_tracking = start_tracking
        self.stop_tracking = stop_tracking

    def main(self):
        while True:
            self.start_tracking.wait()
            self.start_tracking.clear()
            tracking_config = TrackingCofig.persisted()
            queue = Queue(1)

            client_process = Process(target=DataPublishClientUDP(
                server_ip=tracking_config.server_ip,
                server_port=int(tracking_config.server_port),
                queue=queue
            ).listen)
            client_process.start()
            
            frame_queue = Queue(1)
            image_client_process = Process(target=ImagePublishClientUDP(
                server_ip=tracking_config.video_server_ip,
                server_port=int(tracking_config.video_server_port),
                queue=frame_queue,
                flip_video=tracking_config.flip_video
            ).listen)
            image_client_process.start()

            websocket_queue = Queue(1)
            websocket_client_process = Process(target=DataPublishWebsocketClient(
                server_ip=tracking_config.websocket_server_ip,
                server_port=tracking_config.websocket_server_port,
                queue=websocket_queue
            ).listen)
            websocket_client_process.start()
            
            websocket_frame_queue = Queue(1)
            websocket_image_client_process = Process(target=ImagePublishWebsocketClient(
                server_ip=tracking_config.websocket_video_server_ip,
                server_port=tracking_config.websocket_video_server_port,
                queue=websocket_frame_queue,
                flip_video=tracking_config.flip_video
            ).listen)
            websocket_image_client_process.start()

            tracking_process = Process(target=Tracking(
                queue=queue,
                websocket_queue=websocket_queue,
                frame_queue=frame_queue,
                websocket_frame_queue=websocket_frame_queue,
                device_number=tracking_config.device_number,
                show_video=tracking_config.show_video,
                flip_video=tracking_config.flip_video,
                marker_detection_settings=tracking_config.marker_detection_settings,
                translation_offset=tracking_config.translation_offset).track)
            tracking_process.start()

            while True:
                time.sleep(1)

                if not tracking_process.is_alive():
                    client_process.terminate()
                    websocket_client_process.terminate()
                    image_client_process.terminate()
                    websocket_image_client_process.terminate()
                    self.stop_tracking.clear()
                    break

                if self.stop_tracking.wait(0):
                    tracking_process.terminate()
                    client_process.terminate()
                    websocket_client_process.terminate()
                    image_client_process.terminate()
                    websocket_image_client_process.terminate()
                    self.stop_tracking.clear()
                    break


class Tracking:
    def __init__(self, queue, websocket_queue, frame_queue, websocket_frame_queue, device_number, show_video, flip_video, marker_detection_settings, translation_offset):
        self.__data_queue = queue
        self.__data_queue_websocket = websocket_queue
        self.__frame_queue = frame_queue
        self.__frame_queue_websocket = websocket_frame_queue
        self.__device_number = device_number
        self.__show_video = show_video
        self.__flip_video = flip_video
        self.__marker_detection_settings = marker_detection_settings
        self.__translation_offset = translation_offset
        self.oscillation = False

    def track(self):
        #Descomentar quando nao for utilizar o DroidCam
        #video_capture = cv2.VideoCapture(
            #self.__device_number, cv2.CAP_DSHOW)
        video_capture = cv2.VideoCapture(
            self.__device_number)

        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        detection_result = {}
        kalman_filter = create_kalman_filter(18, 6, 0.0334)
        while True:
            _, frame = video_capture.read()

            if self.__marker_detection_settings.identifier == SINGLE_DETECTION:
                detection_result = self.__single_marker_detection(frame, kalman_filter)
            elif self.__marker_detection_settings.identifier == CUBE_DETECTION:
                detection_result = self.__markers_cube_detection(frame, kalman_filter)
            else:
                raise Exception("Invalid detection identifier. Received: {}".format(
                    self.__marker_detection_settings.identifier))

            self.__publish_video_and_coordinates(json.dumps(detection_result), frame)

            if self.__show_video:
                self.__show_video_result(frame, detection_result)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        video_capture.release()
        cv2.destroyAllWindows()
        if self.__frame_queue_websocket.full():
            self.__frame_queue_websocket.get()

    def __single_marker_detection(self, frame, filter):

        corners, ids = self.__detect_markers(frame)

        marker_rvec = None
        marker_tvec = None
        if np.all(ids is not None):
            marker_found = False
            marker_index = None

            for i in range(0, ids.size):
                if ids[i][0] == self.__marker_detection_settings.marker_id:
                    marker_found = True
                    marker_index = i
                    break

            if marker_found:
                cam_mtx, dist = self.__camera_parameters()
                rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(
                    corners, float(self.__marker_detection_settings.marker_length), cam_mtx, dist)

                marker_position = self.__get_position_matrix(
                    rvecs[marker_index], tvecs[marker_index])

                marker_position = self.__apply_transformation(
                    marker_position, self.__translation_offset)

                marker_rvec, marker_tvec = self.__get_rvec_and_tvec(
                    marker_position)

                aruco.drawAxis(frame, cam_mtx, dist,
                               marker_rvec, marker_tvec, 5)

        return self.__detection_result(marker_rvec, marker_tvec, filter)

    def __markers_cube_detection(self, frame, filter):
        corners, ids = self.__detect_markers(frame)

        main_marker_rvec = None
        main_marker_tvec = None
        if np.all(ids is not None):
            
            cam_mtx, dist = self.__camera_parameters()
            rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(
                corners, float(self.__marker_detection_settings.markers_length), cam_mtx, dist)

            choosen_marker_index = 0
            choosen_marker_id = ids[0][0]
            for i in range(0, ids.size):
                if tvecs[choosen_marker_index][0][2] > tvecs[i][0][2]:
                    choosen_marker_id = ids[i][0]
                    choosen_marker_index = i

            if choosen_marker_id == self.__marker_detection_settings.up_marker_id or choosen_marker_id in self.__marker_detection_settings.transformations:
                choosen_marker_position = self.__get_position_matrix(
                    rvecs[choosen_marker_index], tvecs[choosen_marker_index])

                if choosen_marker_id != self.__marker_detection_settings.up_marker_id:
                    choosen_marker_position = self.__apply_transformation(
                        choosen_marker_position, self.__marker_detection_settings.transformations[choosen_marker_id])

                choosen_marker_position = self.__apply_transformation(
                    choosen_marker_position, self.__translation_offset)

                main_marker_rvec, main_marker_tvec = self.__get_rvec_and_tvec(
                    choosen_marker_position)

                aruco.drawAxis(frame, cam_mtx, dist,
                            main_marker_rvec, main_marker_tvec, 5)

        return self.__detection_result(main_marker_rvec, main_marker_tvec, filter)

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

    def __camera_parameters(self):
        if os.path.exists('../assets/configs/') and os.path.isfile('../assets/configs/selected_cam_mtx.npy') and os.path.isfile('../assets/configs/selected_dist.npy'):
            cam_mtx = np.load(
                '../assets/configs/selected_cam_mtx.npy')
            dist = np.load(
                '../assets/configs/selected_dist.npy')
        
        return cam_mtx, dist

    def __get_position_matrix(self, rvec, tvec):
        rot_mtx = np.zeros(shape=(3, 3))
        cv2.Rodrigues(rvec, rot_mtx)

        position = np.concatenate(
            (rot_mtx, np.transpose(tvec)), axis=1)
        position = np.concatenate(
            (position, np.array([[0, 0, 0, 1]])))

        return position

    def __get_rvec_and_tvec(self, position_matrix):

        tvec_t = np.delete(position_matrix[:, 3], (3))

        position_matrix = np.delete(
            position_matrix, 3, 0)
        position_matrix = np.delete(
            position_matrix, 3, 1)

        rvec_t, _ = cv2.Rodrigues(position_matrix)

        return rvec_t.T, tvec_t.T

    def __apply_transformation(self, position_matrix, transformation):
        return np.dot(position_matrix, transformation)

    def __detection_result(self, rvec, tvec, filter):
        detection_result = {}

        detection_result['timestamp'] = time.time()

        success = rvec is not None and tvec is not None
        detection_result['success'] = success

        if success:
            rot_mtx = np.zeros(shape=(3, 3))
            cv2.Rodrigues(rvec, rot_mtx)

            detection_result['translation_x'] = tvec.item(0)
            detection_result['translation_y'] = tvec.item(1)
            detection_result['translation_z'] = tvec.item(2)
            detection_result['rotation_right_x'] = rot_mtx.item(0, 0)
            detection_result['rotation_right_y'] = rot_mtx.item(1, 0)
            detection_result['rotation_right_z'] = rot_mtx.item(2, 0)
            detection_result['rotation_up_x'] = rot_mtx.item(0, 1)
            detection_result['rotation_up_y'] = rot_mtx.item(1, 1)
            detection_result['rotation_up_z'] = rot_mtx.item(2, 1)
            detection_result['rotation_forward_x'] = rot_mtx.item(0, 2)
            detection_result['rotation_forward_y'] = rot_mtx.item(1, 2)
            detection_result['rotation_forward_z'] = rot_mtx.item(2, 2)

            measurements = create_measurement_matrix(detection_result, rot_mtx)
            self.oscillation = update_detection_result(filter, measurements, detection_result, self.oscillation)
        
        return detection_result

    def __publish_video_and_coordinates(self, data, frame):
        if self.__data_queue.full():
            self.__data_queue.get()

        self.__data_queue.put(data)

        if self.__data_queue_websocket.full():
            self.__data_queue_websocket.get()

        self.__data_queue_websocket.put(data)

        if self.__frame_queue.full():
            self.__frame_queue.get()

        self.__frame_queue.put(frame)

        if self.__frame_queue_websocket.full():
            self.__frame_queue_websocket.get()

        self.__frame_queue_websocket.put(frame)

    def __show_video_result(self, frame, detection_result):
        win_name = "Tracking"
        cv2.namedWindow(win_name, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(
            win_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        if self.__flip_video:
            frame = cv2.flip(frame, 1)

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_color = (0, 255, 0)

        cv2.putText(frame, 'timestamp: {}'.format(detection_result['timestamp']), (0, 20),
                    font, font_scale, font_color, 2, cv2.LINE_AA)
        cv2.putText(frame, 'success: {}'.format(detection_result['success']), (0, 40),
                    font, font_scale, font_color, 2, cv2.LINE_AA)

        if detection_result['success'] == 1:
            cv2.putText(frame, 'translation_x: {:.2f}'.format(detection_result['translation_x']), (0, 60),
                        font, font_scale, font_color, 2, cv2.LINE_AA)     
            cv2.putText(frame, 'translation_y: {:.2f}'.format(detection_result['translation_y']), (0, 80),
                        font, font_scale, font_color, 2, cv2.LINE_AA)
            cv2.putText(frame, 'translation_z: {:.2f}'.format(detection_result['translation_z']), (0, 100),
                        font, font_scale, font_color, 2, cv2.LINE_AA)
            cv2.putText(frame, 'rotation_right_x: {:.2f}'.format(detection_result['rotation_right_x']), (0, 120),
                        font, font_scale, font_color, 2, cv2.LINE_AA)
            cv2.putText(frame, 'rotation_right_y: {:.2f}'.format(detection_result['rotation_right_y']), (0, 140),
                        font, font_scale, font_color, 2, cv2.LINE_AA)
            cv2.putText(frame, 'rotation_right_z: {:.2f}'.format(detection_result['rotation_right_z']), (0, 160),
                        font, font_scale, font_color, 2, cv2.LINE_AA)
            cv2.putText(frame, 'rotation_up_x: {:.2f}'.format(detection_result['rotation_up_x']), (0, 180),
                        font, font_scale, font_color, 2, cv2.LINE_AA)
            cv2.putText(frame, 'rotation_up_y: {:.2f}'.format(detection_result['rotation_up_y']), (0, 200),
                        font, font_scale, font_color, 2, cv2.LINE_AA)
            cv2.putText(frame, 'rotation_up_z: {:.2f}'.format(detection_result['rotation_up_z']), (0, 220),
                        font, font_scale, font_color, 2, cv2.LINE_AA)
            cv2.putText(frame, 'rotation_forward_x: {:.2f}'.format(detection_result['rotation_forward_x']), (0, 240),
                        font, font_scale, font_color, 2, cv2.LINE_AA)
            cv2.putText(frame, 'rotation_forward_y: {:.2f}'.format(detection_result['rotation_forward_y']), (0, 260),
                        font, font_scale, font_color, 2, cv2.LINE_AA)
            cv2.putText(frame, 'rotation_forward_z: {:.2f}'.format(detection_result['rotation_forward_z']), (0, 280),
                        font, font_scale, font_color, 2, cv2.LINE_AA)

        cv2.putText(frame, "Q - Quit ", (0, 305), font,
                    font_scale, font_color, 2, cv2.LINE_AA)

        cv2.imshow(win_name, frame)

class DataPublishClientUDP:

    def __init__(self, server_ip, server_port, queue):
        self.__server_ip = server_ip
        self.__server_port = server_port
        self.__queue = queue

    def listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        while True:
            data = self.__queue.get()
            sock.sendto(data.encode(), (self.__server_ip, self.__server_port))

class ImagePublishClientUDP:

    def __init__(self, server_ip, server_port, queue, flip_video):
        self.__server_ip = server_ip
        self.__server_port = server_port
        self.__queue = queue
        self.__flip_video = flip_video
    
    def listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

        while True:
            frame = self.__queue.get()
            if self.__flip_video:
                frame = cv2.flip(frame, 1)
            frame = bytes(cv2.imencode(".jpg", frame, encode_param)[1].tostring())
            sock.sendto(frame, (self.__server_ip, self.__server_port))


class DataPublishWebsocketClient:

    def __init__(self, server_ip, server_port, queue):
        self.__queue = queue
        self.__server_ip = server_ip
        self.__server_port = server_port

    
    def listen(self):
        start_server = websockets.serve(self.time, self.__server_ip, self.__server_port, max_queue=1)

        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    async def time(self, websocket, path):

        while True:
            data = self.__queue.get()
            await websocket.send(data)
            await asyncio.sleep(0.016)

class ImagePublishWebsocketClient:

    def __init__(self, server_ip, server_port, queue, flip_video):
        self.__queue = queue
        self.__server_ip = server_ip
        self.__server_port = server_port
        self.__flip_video = flip_video
    
    def listen(self):
        start_server = websockets.serve(self.time, self.__server_ip, self.__server_port, max_queue=1)

        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    async def time(self, websocket, path):
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

        while True:
            frame = self.__queue.get()
            if self.__flip_video:
                frame = cv2.flip(frame, 1)
            frame = bytes(cv2.imencode(".jpg", frame, encode_param)[1].tostring())
            await websocket.send(frame)
            await asyncio.sleep(0.016)



class TrackingCofig:

    def __init__(self, device_number, device_calibration_dir, calibration_number, cube_number, show_video, flip_video,
                 server_ip, server_port, video_server_ip, video_server_port,
                 websocket_server_ip, websocket_server_port, websocket_video_server_ip, websocket_video_server_port, marker_detection_settings, translation_offset):
        self.device_number = device_number
        self.device_calibration_dir = device_calibration_dir
        self.calibration_number = calibration_number
        self.cube_number = cube_number
        self.show_video = show_video
        self.flip_video = flip_video
        self.server_ip = server_ip
        self.server_port = server_port
        self.video_server_ip = video_server_ip
        self.video_server_port = video_server_port
        self.websocket_server_ip = websocket_server_ip
        self.websocket_server_port = websocket_server_port
        self.websocket_video_server_ip = websocket_video_server_ip
        self.websocket_video_server_port = websocket_video_server_port
        self.marker_detection_settings = marker_detection_settings
        self.translation_offset = translation_offset

    @classmethod
    def persisted(cls):
        if not os.path.exists('../assets/configs/'):
            os.makedirs('../assets/configs/')

        try:
            with open('../assets/configs/tracking_config_data.pkl', 'rb') as file:
                tracking_config_data = pickle.load(file)

                return cls(tracking_config_data['device_number'],
                           tracking_config_data['device_calibration_dir'],
                           tracking_config_data['calibration_number'],
                           tracking_config_data['cube_number'],
                           tracking_config_data['show_video'],
                           tracking_config_data['flip_video'],
                           tracking_config_data['server_ip'],
                           tracking_config_data['server_port'],
                           tracking_config_data['video_server_ip'],
                           tracking_config_data['video_server_port'],
                           tracking_config_data['websocket_server_ip'],
                           tracking_config_data['websocket_server_port'],
                           tracking_config_data['websocket_video_server_ip'],
                           tracking_config_data['websocket_video_server_port'],
                           tracking_config_data['marker_detection_settings'],
                           tracking_config_data['translation_offset'])
        except FileNotFoundError:
            return cls(0, "", 0, 0, True, False, "localhost", "9000", "localhost", "9000", "localhost", "5678", "localhost", "9000", None, np.zeros(shape=(4, 4)))

    def persist(self):
        # Overwrites any existing file.
        with open('../assets/configs/tracking_config_data.pkl', 'wb+') as output:
            pickle.dump({
                'device_number': self.device_number,
                'device_calibration_dir': self.device_calibration_dir,
                'calibration_number': self.calibration_number,
                'cube_number': self.cube_number,
                'show_video': self.show_video,
                'flip_video': self.flip_video,
                'server_ip': self.server_ip,
                'server_port': self.server_port,
                'video_server_ip': self.video_server_ip,
                'video_server_port': self.video_server_port,
                'websocket_server_ip': self.websocket_server_ip,
                'websocket_server_port': self.websocket_server_port,
                'websocket_video_server_ip': self.websocket_video_server_ip,
                'websocket_video_server_port': self.websocket_video_server_port,
                'marker_detection_settings': self.marker_detection_settings,
                'translation_offset': self.translation_offset}, output, pickle.HIGHEST_PROTOCOL)

def rotation_matrix_to_euler(R):
    
    sy = math.sqrt(R[0,0] * R[0,0] +  R[1,0] * R[1,0])
    
    singular = sy < 1e-6

    if  not singular :
        x = math.atan2(R[2,1] , R[2,2])
        y = math.atan2(-R[2,0], sy)
        z = math.atan2(R[1,0], R[0,0])
    else :
        x = math.atan2(-R[1,2], R[1,1])
        y = math.atan2(-R[2,0], sy)
        z = 0

    return np.array([x, y, z])

def euler_to_rotation_matrix(theta):
    
    R_x = np.array([[1,         0,                  0                   ],
                    [0,         math.cos(theta[0]), -math.sin(theta[0]) ],
                    [0,         math.sin(theta[0]), math.cos(theta[0])  ]])
        
    R_y = np.array([[math.cos(theta[1]),    0,      math.sin(theta[1])  ],
                    [0,                     1,      0                   ],
                    [-math.sin(theta[1]),   0,      math.cos(theta[1])  ]])
                               
    R_z = np.array([[math.cos(theta[2]),    -math.sin(theta[2]),    0],
                    [math.sin(theta[2]),    math.cos(theta[2]),     0],
                    [0,                     0,                      1]])
                    
    R = np.dot(R_z, np.dot(R_y, R_x ))

    return R

def create_kalman_filter(num_state, num_measurements, delta_time):
    kalman_filter = cv2.KalmanFilter(num_state, num_measurements, type=cv2.CV_64FC1)

    kalman_filter.processNoiseCov = np.eye(num_state)*1e-5
    kalman_filter.measurementNoiseCov = np.eye(num_measurements)*1e-4
    kalman_filter.errorCovPost = np.eye(num_state)

    kalman_filter.transitionMatrix = np.eye(num_state)
    kalman_filter.transitionMatrix[0, 3] = delta_time
    kalman_filter.transitionMatrix[1, 4] = delta_time
    kalman_filter.transitionMatrix[2, 5] = delta_time
    kalman_filter.transitionMatrix[3, 6] = delta_time
    kalman_filter.transitionMatrix[4, 7] = delta_time
    kalman_filter.transitionMatrix[5, 8] = delta_time
    kalman_filter.transitionMatrix[9, 12] = delta_time
    kalman_filter.transitionMatrix[10, 13] = delta_time
    kalman_filter.transitionMatrix[11, 14] = delta_time
    kalman_filter.transitionMatrix[12, 15] = delta_time
    kalman_filter.transitionMatrix[13, 16] = delta_time
    kalman_filter.transitionMatrix[14, 17] = delta_time
    kalman_filter.transitionMatrix[0, 6] = 0.5 * delta_time ** 2
    kalman_filter.transitionMatrix[1, 7] = 0.5 * delta_time ** 2
    kalman_filter.transitionMatrix[2, 8] = 0.5 * delta_time ** 2
    kalman_filter.transitionMatrix[9, 15] = 0.5 * delta_time ** 2
    kalman_filter.transitionMatrix[10, 16] = 0.5 * delta_time ** 2
    kalman_filter.transitionMatrix[11, 17] = 0.5 * delta_time ** 2


    kalman_filter.measurementMatrix = np.zeros((num_measurements, num_state))
    kalman_filter.measurementMatrix[0, 0] = 1
    kalman_filter.measurementMatrix[1, 1] = 1
    kalman_filter.measurementMatrix[2, 2] = 1
    kalman_filter.measurementMatrix[3, 9] = 1
    kalman_filter.measurementMatrix[4, 10] = 1
    kalman_filter.measurementMatrix[5, 11] = 1
    return kalman_filter

def create_measurement_matrix(measurement, rot_mtx):
    euler_angles = rotation_matrix_to_euler(rot_mtx)
    measurements = np.zeros(6)
    measurements[0] = measurement.get('translation_x')
    measurements[1] = measurement.get('translation_y')
    measurements[2] = measurement.get('translation_z')
    measurements[3] = euler_angles[0]
    measurements[4] = euler_angles[1]
    measurements[5] = euler_angles[2]
        
    return measurements

def update_detection_result(filter, measurements, detection_result, oscillation):
    filter.predict()
    filter.correct(measurements)
    
    estimated_position = filter.statePost
    detection_result['translation_x'] = float(estimated_position[0])
    detection_result['translation_y'] = float(estimated_position[1])
    detection_result['translation_z'] = float(estimated_position[2])

    filtered_euler_angle = np.array([estimated_position[9], estimated_position[10], estimated_position[11]])

    rot_mtx = np.array([[detection_result.get('rotation_right_x'), detection_result.get('rotation_up_x'), detection_result.get('rotation_forward_x')],
                         [detection_result.get('rotation_right_y'), detection_result.get('rotation_up_y'), detection_result.get('rotation_forward_y')],
                         [detection_result.get('rotation_right_z'), detection_result.get('rotation_up_z'), detection_result.get('rotation_forward_z')]])
    euler_angle = rotation_matrix_to_euler(rot_mtx)
    for i in range(0, 3):
        if abs(euler_angle[i] - filtered_euler_angle[i]) > 1.0:
            oscillation = True
            break
        elif oscillation:
            if abs(euler_angle[i] - filtered_euler_angle[i]) > 0.05:
                break
        if i == 2:
            oscillation = False
    if not oscillation:
        filtered_rot_mtx = euler_to_rotation_matrix(filtered_euler_angle)
        detection_result['rotation_right_x'] = filtered_rot_mtx.item(0, 0)
        detection_result['rotation_right_y'] = filtered_rot_mtx.item(1, 0)
        detection_result['rotation_right_z'] = filtered_rot_mtx.item(2, 0)
        detection_result['rotation_up_x'] = filtered_rot_mtx.item(0, 1)
        detection_result['rotation_up_y'] = filtered_rot_mtx.item(1, 1)
        detection_result['rotation_up_z'] = filtered_rot_mtx.item(2, 1)
        detection_result['rotation_forward_x'] = filtered_rot_mtx.item(0, 2)
        detection_result['rotation_forward_y'] = filtered_rot_mtx.item(1, 2)
        detection_result['rotation_forward_z'] = filtered_rot_mtx.item(2, 2)
    return oscillation