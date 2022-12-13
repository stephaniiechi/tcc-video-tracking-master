import cv2
import mediapipe as mp
import socket
import tkinter as tk
import subprocess

class HandsInterface():
    def __init__(self, start_tracking_event, stop_tracking_event, window, login, db, userId):
        self.start_tracking_event = start_tracking_event
        self.stop_tracking_event = stop_tracking_event
        self.window = window
        self.window.title('Hands Tracking')
        self.login = login
        self.db = db
        self.userId = userId

        width = 300
        height = 130
        pos_x = (window.winfo_screenwidth()/2) - (width/2)
        pos_y = (window.winfo_screenheight()/2) - (height/2)
        window.geometry('%dx%d+%d+%d' % (width, height, pos_x, pos_y))
        window.resizable(0, 0)

        # Create some room around all the internal frames
        window['padx'] = 5
        window['pady'] = 5

        self.menu_bar = tk.Menu(self.window)
        self.menu_bar.add_command(label='Back', command=self.back_to_menu)
        self.window.config(menu=self.menu_bar)

        self.main_frame = tk.Frame(self.window)
        self.main_frame.pack()

        self.socket_frame = tk.Frame(self.main_frame)
        self.socket_frame.grid(row=0, column=0, padx=5, pady=5)
        self.socket_entry_label = tk.Label(self.socket_frame, 
                                           text='Port: ', 
                                           font=('Arial', 11))
        self.socket_entry_label.grid(row=0, column=0, padx=0, pady=5)
        self.socket_entry = tk.Entry(self.socket_frame, width=25)
        self.socket_entry.grid(row=0, column=1, padx=5, pady=5)

        self.start_tracking_button = tk.Button(self.main_frame, 
                                           text='Start Tracking',
                                           font=('Arial', 12),
                                           width=21,
                                           height=1,
                                           command=HandsTracking(socket=self.socket_entry.get()).tracking)
        self.start_tracking_button.grid(row=1, column=0, padx=5, pady=5)

    def back_to_menu(self):
        from main_menu import MainMenu # Fazendo o import aqui pois são classes circulares
        self.window.destroy()
        if (self.login == True):
            MainMenu(self.start_tracking_event, self.stop_tracking_event, tk.Tk(), True, self.db, self.userId)
        else:
            MainMenu(self.start_tracking_event, self.stop_tracking_event, tk.Tk(), False, None, None)

class HandsTracking():
    def __init__(self, socket):
        self.socket = socket
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.mp_hands = mp.solutions.hands

    def tracking(self):
        if (self.process_exists('Unity.exe') == False):
            attention_window = tk.Tk()
            attention_window.title("Error")
            attention_window.grab_set()
            attention_window.resizable(0, 0)
            width = 258
            height = 52
            pos_x = (attention_window.winfo_screenwidth()/2) - (width/2)
            pos_y = (attention_window.winfo_screenheight()/2) - (height/2)
            attention_window.geometry('%dx%d+%d+%d' % (width, height, pos_x, pos_y))
            attention_window.resizable(0, 0)
            # attention_window.eval('tk::PlaceWindow . center')
            message_label = tk.Label(master=attention_window, text='Your application is not running', font=("Arial", 12, 'bold'), fg='red')
            message_label.grid(row=0, column= 0, padx=10, pady=10)

        else:
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

                            # s = socket.socket()
                            # HOST = socket.gethostname()
                            # myIP = socket.gethostbyname(HOST)
                            # s.connect((myIP, socket))
                            
                            # rounded_x = round(10000*round(x_coordinate, 2), 2)
                            # rounded_y = round(10000*round(y_coordinate, 2), 2)
                            # rounded_z = round(10000*round(z_coordinate, 2), 2)
                            
                            # s.send((
                            #     str(rounded_x) + "," +
                            #     str(rounded_y) + "," +
                            #     str(rounded_z)).encode())
                            # s.close()

                            self.mp_drawing.draw_landmarks(
                                image,
                                hand_landmarks,
                                self.mp_hands.HAND_CONNECTIONS,
                                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                                self.mp_drawing_styles.get_default_hand_connections_style())
                
                    # Flip the image horizontally for a selfie-view display.
                    window = cv2.imshow('Hand Tracking', cv2.flip(image, 1))
                    
                    if cv2.waitKey(5) & 0xFF == 27: # Fechar pelo ESC
                        cv2.destroyWindow('Hand Tracking')
                        break
                    elif cv2.getWindowProperty('Hand Tracking', cv2.WND_PROP_VISIBLE) < 1: # Fechar pelo X
                        break
            video_capt.release()

    def process_exists(self, process_name):
        call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
        output = subprocess.check_output(call).decode()
        last_line = output.strip().split('\r\n')[-1]
        return last_line.lower().startswith(process_name.lower())