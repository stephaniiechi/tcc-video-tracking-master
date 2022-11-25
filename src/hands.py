import cv2
import mediapipe as mp
import socket

class HandsTracking():
    def __init__(self, socket):
        self.socket = socket
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.mp_hands = mp.solutions.hands

    def tracking(self):
        video_capt = cv2.VideoCapture(0)
        with self.mp_hands.Hands(model_complexity=0, min_detection_confidence=0.5, min_tracking_confidence = 0.5) as hands:
            while video_capt.isOpened():
                success, image = video_capt.read()
                if not success:
                    print("Ignoring empty camera frame.")
                    # If loading a video, use 'break' instead of 'continue'.
                    continue

                # To improve performance, optionally mark the image as not writeable to
                # pass by reference.
                image.flags.writeable = False
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = hands.process(image)

                # Draw the hand annotations on the image.
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        x_coordinate = -0.5 + \
                            hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP].x
                        y_coordinate = 0.5 - \
                            hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y
                        z_coordinate = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP].z

                        # DESCOMENTAR QUANDO FOR USAR O UNITY \/
                        # s = socket.socket()
                        # HOST = socket.gethostname()
                        # myIP = socket.gethostbyname(HOST)
                        # s.connect((myIP, socket))
                        # 
                        # rounded_x = round(10000*round(x_coordinate, 2), 2)
                        # rounded_y = round(10000*round(y_coordinate, 2), 2)
                        # rounded_z = round(10000*round(z_coordinate, 2), 2)
                        #
                        # s.send((
                        #     str(rounded_x) + "," +
                        #     str(rounded_y) + "," +
                        #     str(rounded_z)).encode())
                        # s.close()
                        
                        print(x_coordinate, y_coordinate, z_coordinate)
                        self.mp_drawing.draw_landmarks(
                            image,
                            hand_landmarks,
                            self.mp_hands.HAND_CONNECTIONS,
                            self.mp_drawing_styles.get_default_hand_landmarks_style(),
                            self.mp_drawing_styles.get_default_hand_connections_style())
               
                # Flip the image horizontally for a selfie-view display.
                window = cv2.imshow('Hand Tracking', cv2.flip(image, 1))
                # win_x = screen_width/2 - window.cols/2
                # win_y = screen_height/2 - image.rows/2 - 30
                cv2.moveWindow(window, 700, 400)
                
                if cv2.waitKey(5) & 0xFF == 27: # Fechar pelo ESC
                    cv2.destroyWindow('Hand Tracking')
                    break
                elif cv2.getWindowProperty('Hand Tracking', cv2.WND_PROP_VISIBLE) < 1: # Fechar pelo X
                    break
        video_capt.release()

# class HandsInterface():
