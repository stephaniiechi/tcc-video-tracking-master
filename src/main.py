from firebase_admin import firestore
from google.oauth2.credentials import Credentials
from google.cloud.firestore import Client
import pyrebase
import os
import json
import requests
import tkinter as tk
from tkinter import LEFT, messagebox
from tkinter import ttk
import multiprocessing
import time
from tkinter.constants import ACTIVE, DISABLED
from PIL import ImageTk, Image
import socket
import numpy as np
from tracking import TrackingScheduler, TrackingCofig
from video_source_calibration import VideoSourceCalibration, VideoSourceCalibrationConfig
from marker_detection_settings import CUBE_DETECTION, SINGLE_DETECTION, SingleMarkerDetectionSettings, MarkersCubeDetectionSettings, MarkerCubeMapping
import video_device_listing
import webbrowser

FIREBASE_REST_API = "https://identitytoolkit.googleapis.com/v1/accounts"

class App():

    def __init__(self, start_tracking, stop_tracking, window, db, userId):
        self.start_tracking_event = start_tracking
        self.stop_tracking_event = stop_tracking
        self.db = db
        self.userId = userId
        self.saving_error = False
        self.base_video_source_dir = '../assets/camera_calibration_data'
        self.base_cube_dir = '../assets/configs/marker_cubes'
        self.base_img_dir = '../images'

        width = 500
        height = 380
        pos_x = (window.winfo_screenwidth()/2) - (width/2)
        pos_y = (window.winfo_screenheight()/2) - (height/2)
        window.geometry('%dx%d+%d+%d' % (width, height, pos_x, pos_y))
        window.resizable(0, 0)

        # Create some room around all the internal frames
        window['padx'] = 5
        window['pady'] = 5

        window.grid_rowconfigure(1, weight=1)
        window.grid_rowconfigure(2, weight=1)
        window.grid_rowconfigure(3, weight=1)
        window.grid_rowconfigure(4, weight=1)
        window.grid_columnconfigure(1, weight=1)

        self.tabControl = ttk.Notebook(window)
        tab1 = ttk.Frame(self.tabControl)
        tab2 = ttk.Frame(self.tabControl)
        tab3 = ttk.Frame(self.tabControl)

        self.tabControl.add(tab1, text="Camera")
        self.tabControl.add(tab2, text="Tracking Configuration")
        self.tabControl.add(tab3, text="Tracking")
        self.tabControl.pack(fill="both")

        self.video_source_frame = ttk.LabelFrame(
            tab1, text="Video Source")
        self.video_source_frame.place(relx=0.5, rely=0.5, anchor='center')
        self.video_source_frame.grid_columnconfigure(1, weight=1)

        self.refresh_video_sources_button = tk.Button(
            self.video_source_frame, text="Refresh Devices")
        self.refresh_video_sources_button['command'] = self.refresh_video_sources
        self.refresh_video_sources_button.grid(row=1, column=1, pady=5)

        self.video_source = ttk.Combobox(
            self.video_source_frame, state="readonly", height=4, width=40)
        self.video_source.bind('<<ComboboxSelected>>', 
                               self.refresh_calibrations)
        self.video_source.grid(row=2, column=1, padx=5, pady=5)

        self.video_source_calibration_frame = ttk.LabelFrame(
            self.video_source_frame, text="Calibration")
        self.video_source_calibration_frame.grid(
            row=3, column=1, padx=5, pady=5)

        self.calibration_selection_frame = tk.Frame(
            self.video_source_calibration_frame)
        self.calibration_selection_frame.grid(
            row=1, column=1, padx=5, pady=5)
        
        self.author_label = tk.Label(
            self.calibration_selection_frame, text='Author:')
        self.author_label.grid(row=0, column=0)
        self.author = tk.StringVar()
        self.author.trace('w', lambda name, index, mode, var=self.author: self.author_updated())
        self.author_entry = tk.Entry(
            self.calibration_selection_frame, textvariable=self.author, width=55, state=DISABLED)
        self.author_entry.grid(row=0, column=1)

        self.new_calibration_button = tk.Button(
            self.calibration_selection_frame, text="New", command=self.add_calibration, width=6)
        self.new_calibration_button.grid(row=0, column=2, padx=5)
        
        self.calibration_label = tk.Label(
            self.calibration_selection_frame, text='Name:')
        self.calibration_label.grid(row=1, column=0)
        self.calibration_selection = ttk.Combobox(
            self.calibration_selection_frame, state="readonly", height=4, width=52)
        self.calibration_selection.bind('<<ComboboxSelected>>',
                                        self.calibration_selected)
        self.calibration_selection.grid(row=1, column=1)

        self.calibration_config = VideoSourceCalibrationConfig.persisted(self.get_calibration_dir())
        
        self.score_text = tk.StringVar()
        self.score_text.set('Score: {:.2f}'.format(self.calibration_config.score))
        self.score_label = tk.Label(
            self.calibration_selection_frame, textvariable=self.score_text)
        self.score_label.grid(row=1, column=2)

        self.calibration_chessboard_parameters_frame = tk.Frame(
            self.video_source_calibration_frame)
        self.calibration_chessboard_parameters_frame.grid(
            row=2, column=1, padx=5)

        self.chessboard_square_size = tk.DoubleVar()
        self.chessboard_square_size.set(
            self.calibration_config.chessboard_square_size)
        self.chessboard_square_size_label = ttk.Label(
            self.calibration_chessboard_parameters_frame, text="Chessboard square size:")
        self.chessboard_square_size_label.grid(
            row=1, column=1)
        self.chessboard_square_size_entry = ttk.Entry(
            self.calibration_chessboard_parameters_frame, width=5,
            textvariable=self.chessboard_square_size, state=DISABLED)
        self.chessboard_square_size_entry.grid(row=1, column=2)

        self.calibration_buttons_frame = tk.Frame(
            self.video_source_calibration_frame)
        self.calibration_buttons_frame.grid(row=3, column=1, pady=5)

        self.calibrate_button = tk.Button(
            self.calibration_buttons_frame, text="Add calibration to database", command=self.add_calibration_to_database, state=DISABLED)
        self.calibrate_button.grid(row=1, column=1, padx=5)

        self.test_button = tk.Button(
            self.calibration_buttons_frame, text="Test calibration", command=self.enable_chessboard_entry, state=ACTIVE)
        self.test_button.grid(row=1, column=2, padx=5)
        
        self.delete_button = tk.Button(
            self.calibration_buttons_frame, text="Delete", command=self.delete_calibration, state=DISABLED)
        self.delete_button.grid(row=1, column=3, padx=5)

        self.configuration_frame = tk.Frame(tab2)
        self.configuration_frame.pack()

        self.configuration_frame.grid_columnconfigure(1, weight=1)
        self.configuration_frame.grid_columnconfigure(2, weight=1)

        self.tracking_config_frame = tk.Frame(
            self.configuration_frame)
        self.tracking_config_frame.grid(
            row=1, column=1, padx=5)

        self.tracking_config_frame.grid_columnconfigure(1, weight=1)
        self.tracking_config_frame.grid_rowconfigure(1, weight=1)
        self.tracking_config_frame.grid_rowconfigure(2, weight=1)
        self.tracking_config_frame.grid_rowconfigure(3, weight=1)

        self.tracking_config = TrackingCofig.persisted()

        self.detection_mode_frame = tk.LabelFrame(
            self.tracking_config_frame, text="Detection Mode")
        self.detection_mode_frame.grid(row=1, column=1, padx=5, pady=2)

        self.single_marker_frame = ttk.LabelFrame(
            self.detection_mode_frame, text="Single Marker")
        self.single_marker_frame.grid(
            row=1, column=1, padx=5, pady=5)

        self.single_marker_mode = tk.BooleanVar()
        self.single_marker_mode_checkbox = tk.Checkbutton(
            self.single_marker_frame, variable=self.single_marker_mode,
            command=self.single_marker_settings_selection)
        self.single_marker_mode_checkbox.grid(row=1, column=1, pady=5)

        self.single_marker_settings_frame = tk.Frame(
            self.single_marker_frame)
        self.single_marker_settings_frame.grid(
            row=2, column=1, padx=5, pady=5)

        self.single_marker_id = tk.IntVar()
        self.single_marker_id_label = ttk.Label(
            self.single_marker_settings_frame, text="Marker ID:")
        self.single_marker_id_label.grid(
            row=1, column=1, sticky=tk.W + tk.N)
        self.single_marker_id_entry = ttk.Entry(
            self.single_marker_settings_frame, textvariable=self.single_marker_id, width=5)
        self.single_marker_id_entry.grid(row=1, column=2, sticky=tk.W)

        self.single_marker_length = tk.DoubleVar()
        self.single_marker_length_label = ttk.Label(
            self.single_marker_settings_frame, text="Marker length:")
        self.single_marker_length_label.grid(
            row=2, column=1, sticky=tk.W + tk.N)
        self.single_marker_length_entry = ttk.Entry(
            self.single_marker_settings_frame, textvariable=self.single_marker_length, width=5)
        self.single_marker_length_entry.grid(row=2, column=2, sticky=tk.W)

        self.single_marker_buttons_frame = tk.Frame(
            self.single_marker_frame)
        self.single_marker_buttons_frame.grid(
            row=3, column=1, padx=5, pady=5)

        self.single_marker_save_button = tk.Button(
            self.single_marker_buttons_frame, text="Save", command=self.single_marker_save)
        self.single_marker_save_button.grid(row=1, column=1)

        self.marker_cube_frame = ttk.LabelFrame(
            self.detection_mode_frame, text="Marker Cube")
        self.marker_cube_frame.grid(
            row=1, column=2, padx=5, pady=5)

        self.marker_cube_mode = tk.BooleanVar()
        self.marker_cube_mode_checkbox = tk.Checkbutton(
            self.marker_cube_frame, variable=self.marker_cube_mode,
            command=self.marker_cube_settings_selection)
        self.marker_cube_mode_checkbox.grid(row=1, column=1, pady=5)

        self.cube_id_frame = tk.Frame(self.marker_cube_frame)
        self.cube_id_frame.grid(row=2, column=1, padx=5, pady=5)

        self.cube_id_selection = ttk.Combobox(
            self.cube_id_frame, state="normal", height=4, width=15)
        self.cube_id_selection.bind('<<ComboboxSelected>>',
                                    self.cube_id_selected)
        self.cube_id_selection.grid(row=1, column=1)

        self.new_cube_id_button = tk.Button(
            self.cube_id_frame, text="New", command=self.add_cube_id)
        self.new_cube_id_button.grid(row=1, column=2, padx=5)

        self.marker_cube_settings_frame = tk.Frame(
            self.marker_cube_frame)
        self.marker_cube_settings_frame.grid(
            row=3, column=1, padx=5, pady=5)

        self.cube_up_marker_id = tk.IntVar()
        self.cube_up_marker_id_label = ttk.Label(
            self.marker_cube_settings_frame, text="Up Marker ID:")
        self.cube_up_marker_id_label.grid(
            row=1, column=1, sticky=tk.W + tk.N)
        self.cube_up_marker_id_entry = ttk.Entry(
            self.marker_cube_settings_frame, textvariable=self.cube_up_marker_id, width=5, state=DISABLED)
        self.cube_up_marker_id_entry.grid(row=1, column=2, sticky=tk.W)

        self.cube_side_marker_ids_label = ttk.Label(
            self.marker_cube_settings_frame, text="Side Marker IDS:")
        self.cube_side_marker_ids_label.grid(
            row=2, column=1, sticky=tk.W + tk.N)

        self.cube_side_marker_1 = tk.IntVar()
        self.cube_side_marker_1_entry = ttk.Entry(
            self.marker_cube_settings_frame, textvariable=self.cube_side_marker_1, width=5, state=DISABLED)
        self.cube_side_marker_1_entry.grid(row=2, column=2, sticky=tk.W)
        self.cube_side_marker_2 = tk.StringVar()
        self.cube_side_marker_2_entry = ttk.Entry(
            self.marker_cube_settings_frame, textvariable=self.cube_side_marker_2, width=5, state=DISABLED)
        self.cube_side_marker_2_entry.grid(row=2, column=3, sticky=tk.W)
        self.cube_side_marker_3 = tk.StringVar()
        self.cube_side_marker_3_entry = ttk.Entry(
            self.marker_cube_settings_frame, textvariable=self.cube_side_marker_3, width=5, state=DISABLED)
        self.cube_side_marker_3_entry.grid(row=2, column=4, sticky=tk.W)
        self.cube_side_marker_4 = tk.StringVar()
        self.cube_side_marker_4_entry = ttk.Entry(
            self.marker_cube_settings_frame, textvariable=self.cube_side_marker_4, width=5, state=DISABLED)
        self.cube_side_marker_4_entry.grid(row=2, column=5, sticky=tk.W)

        self.cube_down_marker_id = tk.StringVar()
        self.cube_down_marker_id_label = ttk.Label(
            self.marker_cube_settings_frame, text="Down Marker ID:")
        self.cube_down_marker_id_label.grid(
            row=3, column=1, sticky=tk.W + tk.N)
        self.cube_down_marker_id_entry = ttk.Entry(
            self.marker_cube_settings_frame, textvariable=self.cube_down_marker_id, width=5, state=DISABLED)
        self.cube_down_marker_id_entry.grid(row=3, column=2, sticky=tk.W)

        self.cube_markers_length = tk.DoubleVar()
        self.cube_markers_length_label = ttk.Label(
            self.marker_cube_settings_frame, text="Markers length:")
        self.cube_markers_length_label.grid(
            row=4, column=1, pady=5)
        self.cube_markers_length_entry = ttk.Entry(
            self.marker_cube_settings_frame, textvariable=self.cube_markers_length, width=5, state=DISABLED)
        self.cube_markers_length_entry.grid(row=4, column=2, sticky=tk.W)

        self.marker_cube_buttons_frame = tk.Frame(
            self.marker_cube_frame)
        self.marker_cube_buttons_frame.grid(
            row=4, column=1, padx=5, pady=5)

        self.marker_cube_id_map_button = tk.Button(
            self.marker_cube_buttons_frame, text="Map and Save", command=self.marker_cube_map, state=DISABLED)
        self.marker_cube_id_map_button.grid(row=1, column=1, padx=5)

        self.marker_cube_id_delete_button = tk.Button(
            self.marker_cube_buttons_frame, text="Delete", command=self.marker_cube_delete)
        self.marker_cube_id_delete_button.grid(row=1, column=2, padx=5)

        self.single_marker_settings = SingleMarkerDetectionSettings.persisted()
        self.single_marker_settings_set()

        self.marker_cube_settings = MarkersCubeDetectionSettings.persisted(
            self.cube_id_selection.current())
        self.marker_cube_settings_set()

        if self.tracking_config.marker_detection_settings is None or self.tracking_config.marker_detection_settings.identifier == SINGLE_DETECTION:
            self.single_marker_mode.set(True)
            self.single_marker_settings_selection()
        elif self.tracking_config.marker_detection_settings.identifier == CUBE_DETECTION:
            self.marker_cube_mode.set(True)
            self.marker_cube_settings_selection()

        self.translation_offset_frame = ttk.LabelFrame(
            self.tracking_config_frame, text="Translation Offset")
        self.translation_offset_frame.grid(row=2, column=1, pady=5)

        self.translation_offset_x = tk.DoubleVar()
        self.translation_offset_x.set(
            self.tracking_config.translation_offset[0][3])
        self.translation_offset_x_label = ttk.Label(
            self.translation_offset_frame, text="X", foreground="red")
        self.translation_offset_x_label.grid(row=1, column=1, pady=5)
        self.translation_offset_x_entry = ttk.Entry(
            self.translation_offset_frame, textvariable=self.translation_offset_x, width=5)
        self.translation_offset_x_entry.grid(
            row=1, column=2, sticky=tk.W, padx=5)

        self.translation_offset_y = tk.DoubleVar()
        self.translation_offset_y.set(
            self.tracking_config.translation_offset[1][3])
        self.translation_offset_y_label = ttk.Label(
            self.translation_offset_frame, text="Y", foreground="green")
        self.translation_offset_y_label.grid(row=1, column=3, pady=5)
        self.translation_offset_y_entry = ttk.Entry(
            self.translation_offset_frame, textvariable=self.translation_offset_y, width=5)
        self.translation_offset_y_entry.grid(
            row=1, column=4, sticky=tk.W, padx=5)

        self.translation_offset_z = tk.DoubleVar()
        self.translation_offset_z.set(
            self.tracking_config.translation_offset[2][3])
        self.translation_offset_z_label = ttk.Label(
            self.translation_offset_frame, text="Z", foreground="blue")
        self.translation_offset_z_label.grid(row=1, column=5, pady=5)
        self.translation_offset_z_entry = ttk.Entry(
            self.translation_offset_frame, textvariable=self.translation_offset_z, width=5)
        self.translation_offset_z_entry.grid(
            row=1, column=6, sticky=tk.W, padx=5)

        self.publishing_config_frame = tk.Frame(tab3)
        self.publishing_config_frame.place(relx=0.5, rely=0.5, anchor='center')

        self.export_coordinates_frame = ttk.LabelFrame(
            self.publishing_config_frame, text="Coordinates Publish Server UDP")
        self.export_coordinates_frame.grid(row=0, column=1, pady=5)

        self.export_coordinates_input_frame = tk.Frame(
            self.export_coordinates_frame)
        self.export_coordinates_input_frame.grid(
            row=1, column=1, padx=5, pady=5)

        self.server_ip = tk.StringVar()
        self.server_ip.set(self.tracking_config.server_ip)
        self.server_ip_label = ttk.Label(
            self.export_coordinates_input_frame, text="IP Address:")
        self.server_ip_label.grid(row=1, column=1)
        self.server_ip_entry = ttk.Entry(
            self.export_coordinates_input_frame, textvariable=self.server_ip, width=15)
        self.server_ip_entry.grid(row=1, column=2)

        self.server_port = tk.StringVar()
        self.server_port.set(self.tracking_config.server_port)
        self.server_port_label = ttk.Label(
            self.export_coordinates_input_frame, text="Port:")
        self.server_port_label.grid(row=1, column=3)
        self.server_port_entry = ttk.Entry(
            self.export_coordinates_input_frame, textvariable=self.server_port, width=7)
        self.server_port_entry.grid(row=1, column=4)

        self.export_video_frame = ttk.LabelFrame(
            self.publishing_config_frame, text="Video Publish Server UDP")
        self.export_video_frame.grid(row=1, column=1, pady=5)

        self.export_video_input_frame = tk.Frame(
            self.export_video_frame)
        self.export_video_input_frame.grid(
            row=1, column=1, padx=5, pady=5)

        self.video_server_ip = tk.StringVar()
        self.video_server_ip.set(self.tracking_config.video_server_ip)
        self.video_server_ip_label = ttk.Label(
            self.export_video_input_frame, text="IP Address:")
        self.video_server_ip_label.grid(row=1, column=1)
        self.video_server_ip_entry = ttk.Entry(
            self.export_video_input_frame, textvariable=self.video_server_ip, width=15)
        self.video_server_ip_entry.grid(row=1, column=2)

        self.video_server_port = tk.StringVar()
        self.video_server_port.set(self.tracking_config.video_server_port)
        self.video_server_port_label = ttk.Label(
            self.export_video_input_frame, text="Port:")
        self.video_server_port_label.grid(row=1, column=3)
        self.video_server_port_entry = ttk.Entry(
            self.export_video_input_frame, textvariable=self.video_server_port, width=7)
        self.video_server_port_entry.grid(row=1, column=4)

        self.export_coordinates_websocket_frame = ttk.LabelFrame(
            self.publishing_config_frame, text="Coordinates Publish Server Web")
        self.export_coordinates_websocket_frame.grid(row=2, column=1, pady=5)

        self.export_coordinates_input_websocket_frame = tk.Frame(
            self.export_coordinates_websocket_frame)
        self.export_coordinates_input_websocket_frame.grid(
            row=1, column=1, padx=5, pady=5)

        self.websocket_server_ip = tk.StringVar()
        self.websocket_server_ip.set(self.tracking_config.websocket_server_ip)
        self.websocket_server_ip_label = ttk.Label(
            self.export_coordinates_input_websocket_frame, text="IP Address:")
        self.websocket_server_ip_label.grid(row=1, column=1)
        self.websocket_server_ip_entry = ttk.Entry(
            self.export_coordinates_input_websocket_frame, textvariable=self.websocket_server_ip, width=15)
        self.websocket_server_ip_entry.grid(row=1, column=2)

        self.websocket_server_port = tk.StringVar()
        self.websocket_server_port.set(self.tracking_config.websocket_server_port)
        self.websocket_server_port_label = ttk.Label(
            self.export_coordinates_input_websocket_frame, text="Port:")
        self.websocket_server_port_label.grid(row=1, column=3)
        self.websocket_server_port_entry = ttk.Entry(
            self.export_coordinates_input_websocket_frame, textvariable=self.websocket_server_port, width=7)
        self.websocket_server_port_entry.grid(row=1, column=4)

        self.export_video_websocket_frame = ttk.LabelFrame(
            self.publishing_config_frame, text="Video Publish Server Web")
        self.export_video_websocket_frame.grid(row=3, column=1, pady=5)

        self.export_video_input_websocket_frame = tk.Frame(
            self.export_video_websocket_frame)
        self.export_video_input_websocket_frame.grid(
            row=1, column=1, padx=5, pady=5)

        self.websocket_video_server_ip = tk.StringVar()
        self.websocket_video_server_ip.set(self.tracking_config.websocket_video_server_ip)
        self.websocket_video_server_ip_label = ttk.Label(
            self.export_video_input_websocket_frame, text="IP Address:")
        self.websocket_video_server_ip_label.grid(row=1, column=1)
        self.websocket_video_server_ip_entry = ttk.Entry(
            self.export_video_input_websocket_frame, textvariable=self.websocket_video_server_ip, width=15)
        self.websocket_video_server_ip_entry.grid(row=1, column=2)

        self.websocket_video_server_port = tk.StringVar()
        self.websocket_video_server_port.set(self.tracking_config.websocket_video_server_port)
        self.websocket_video_server_port_label = ttk.Label(
            self.export_video_input_websocket_frame, text="Port:")
        self.websocket_video_server_port_label.grid(row=1, column=3)
        self.websocket_video_server_port_entry = ttk.Entry(
            self.export_video_input_websocket_frame, textvariable=self.websocket_video_server_port, width=7)
        self.websocket_video_server_port_entry.grid(row=1, column=4)

        self.show_video = tk.BooleanVar()
        self.show_video.set(self.tracking_config.show_video)
        self.show_video_checkbox = tk.Checkbutton(
            self.publishing_config_frame, text="Show video", variable=self.show_video)
        self.show_video_checkbox.grid(row=4, column=1, pady=0)

        self.flip_video = tk.BooleanVar()
        self.flip_video.set(self.tracking_config.flip_video)
        self.flip_video_checkbox = tk.Checkbutton(
            self.publishing_config_frame, text="Flip Video", variable=self.flip_video
        )
        self.flip_video_checkbox.grid(row=5, column=1)

        self.tracking_button = tk.Button(
            self.publishing_config_frame, text="Start Tracking", command=self.start_tracking)
        self.tracking_button.grid(row=6, column=1, sticky=tk.N, pady=5)

        self.calibration = None
        self.cube_ids = []
        self.cube_ids_init()
        self.video_source_list = []
        self.refresh_video_sources()
        self.video_source.current(self.tracking_config.device_number) #selects the last camera used by the AR Tracking
        self.calibration_selection_init()
        self.icon_img = ImageTk.PhotoImage(Image.open("{}/error_icon.png".format(self.base_img_dir)))
    
    def single_marker_settings_selection(self):
        if self.single_marker_mode.get():
            self.marker_cube_mode.set(False)

            for child in self.single_marker_settings_frame.winfo_children():
                child.configure(state=tk.ACTIVE)

            for child in self.single_marker_buttons_frame.winfo_children():
                child.configure(state=tk.ACTIVE)

            for child in self.marker_cube_settings_frame.winfo_children():
                child.configure(state=tk.DISABLED)

            for child in self.cube_id_frame.winfo_children():
                child.configure(state=tk.DISABLED)

            for child in self.marker_cube_buttons_frame.winfo_children():
                child.configure(state=tk.DISABLED)
        else:
            self.single_marker_mode.set(True)

    def single_marker_settings_set(self):
        self.single_marker_length.set(
            self.single_marker_settings.marker_length)
        self.single_marker_id.set(self.single_marker_settings.marker_id)

    def single_marker_save(self):
        try:
            self.single_marker_settings.marker_length = self.single_marker_length.get()
            self.single_marker_settings.marker_id = self.single_marker_id.get()

            self.single_marker_settings.persist()
            self.saving_error = False
        except tk.TclError:
            self.saving_error = True
            error_window = tk.Toplevel()
            error_window.title("Saving Error")
            error_window.grab_set()
            error_window.resizable(0, 0)

            error_window.columnconfigure([0, 1], minsize=50, weight=1)
            error_window.rowconfigure([0, 1], minsize=50, weight=1)

            geometry_string = self.center_window(error_window, window_height=280, window_width=1100)
            error_window.geometry(geometry_string)
            
            error_title = tk.Label(master=error_window, text="Insufficient data to save marker ID and length", fg="blue", font=("Arial", 18))
            error_title.grid(row=0, column=1, sticky="w")

            icon_label = tk.Label(master=error_window, image=self.icon_img, width=80, height=80)
            icon_label.grid(row=0, column=0)

            self.example_img = ImageTk.PhotoImage(Image.open("{}/saving_marker_example.png".format(self.base_img_dir)))
            example_label = tk.Label(master=error_window, image=self.example_img, width=170, height=170)
            example_label.grid(row=2, column=1)
            
            error_message = tk.Label(master=error_window, text="To save the marker it is necessary to fill in both Marker ID and Marker length slots. \nIn order to solve this problem, fill in the Marker ID slot with the marker ID and fill in the Marker length slot with the marker side length like in the example bellow.",
                                    justify="left", font=("Arial", 11),)
            error_message.grid(row=1, column=1)



    def marker_cube_settings_selection(self):
        if self.marker_cube_mode.get():
            self.single_marker_mode.set(False)

            for child in self.cube_id_frame.winfo_children():
                child.configure(state=tk.ACTIVE)

            self.marker_cube_id_delete_button['state'] = ACTIVE

            for child in self.single_marker_settings_frame.winfo_children():
                child.configure(state=tk.DISABLED)

            for child in self.single_marker_buttons_frame.winfo_children():
                child.configure(state=tk.DISABLED)
        else:
            self.marker_cube_mode.set(True)

    def cube_ids_init(self):
        for cube_id in os.listdir(self.base_cube_dir):
            self.cube_ids.append(cube_id.split(".")[0])

        self.cube_id_selection['values'] = self.cube_ids

        if len(self.cube_ids) > 0:
            self.cube_id_selection.current(self.tracking_config.cube_number) # selects the last marker cube used by the AR Tracking
            self.marker_cube_settings = MarkersCubeDetectionSettings.persisted(
                self.cube_id_selection.get())
            self.marker_cube_settings_set()
        else:
            self.cube_id_selection.set("")

    def cube_id_selected(self, _=None):
        self.marker_cube_settings = MarkersCubeDetectionSettings.persisted(
            self.cube_id_selection.get())
        self.marker_cube_settings_set()
        self.cube_id_selection['state'] = 'readonly'

    def add_cube_id(self):
        if self.cube_ids.__contains__(""):
            self.cube_ids.remove("")

        self.cube_ids.append("")
        self.cube_id_selection['values'] = self.cube_ids
        self.cube_id_selection.current(len(self.cube_ids) - 1)
        self.cube_id_selected()
        self.cube_id_selection['state'] = 'normal'
        self.marker_cube_id_map_button['state'] = ACTIVE
        for child in self.marker_cube_settings_frame.winfo_children():
                child.configure(state=tk.ACTIVE)

    def marker_cube_settings_set(self):
        self.cube_up_marker_id.set(self.marker_cube_settings.up_marker_id)
        self.cube_side_marker_1.set(
            self.marker_cube_settings.side_marker_ids[0])
        self.cube_side_marker_2.set(
            self.marker_cube_settings.side_marker_ids[1])
        self.cube_side_marker_3.set(
            self.marker_cube_settings.side_marker_ids[2])
        self.cube_side_marker_4.set(
            self.marker_cube_settings.side_marker_ids[3])
        self.cube_down_marker_id.set(self.marker_cube_settings.down_marker_id)
        self.cube_markers_length.set(self.marker_cube_settings.markers_length)

    def marker_cube_map(self):
        try:
            detection = MarkerCubeMapping(self.cube_id_selection.get(), self.calibration_selection.get(), self.video_source.current(),
                                        self.cube_markers_length.get(), self.cube_up_marker_id.get(),
                                        [self.cube_side_marker_1.get(), self.cube_side_marker_2.get(
                                        ), self.cube_side_marker_3.get(), self.cube_side_marker_4.get()],
                                        self.cube_down_marker_id.get(), self.database_calibrations)

            detection.map()
            self.marker_cube_settings = MarkersCubeDetectionSettings.persisted(
                self.cube_id_selection.get())
            self.cube_id_selection['state'] = 'readonly'
            self.marker_cube_id_map_button['state'] = DISABLED
            for child in self.marker_cube_settings_frame.winfo_children():
                child.configure(state=tk.DISABLED)

            if not self.cube_ids.__contains__(self.cube_id_selection.get()):
                self.cube_ids.append(self.cube_id_selection.get())

            if self.cube_ids.__contains__(""):
                self.cube_ids.remove("")

            self.cube_id_selection['values'] = sorted(self.cube_ids, key=str.lower)
        except tk.TclError:
            error_window = tk.Toplevel()
            error_window.title("Mapping Error")
            error_window.grab_set()
            error_window.resizable(0, 0)

            error_window.columnconfigure([0, 1], minsize=50, weight=1)
            error_window.rowconfigure([0, 1], minsize=50, weight=1)

            geometry_string = self.center_window(error_window, window_height=350, window_width=1100)
            error_window.geometry(geometry_string)
            
            error_title = tk.Label(master=error_window, text="Insufficient data to start cube mapping", fg="blue", font=("Arial", 18))
            error_title.grid(row=0, column=1, sticky="w")
            
            icon_label = tk.Label(master=error_window, image=self.icon_img, width=80, height=80)
            icon_label.grid(row=0, column=0)
            
            self.example_img = ImageTk.PhotoImage(Image.open("{}/mapping_example.png".format(self.base_img_dir)))
            example_label = tk.Label(master=error_window, image=self.example_img)
            example_label.grid(row=2, column=1)
            
            error_message = tk.Label(master=error_window, text="This problem occurred because it is necessary to fill in at least the Up Marker ID slot, the first Side Marker ID slot and the Markers length slot. \nTo solve the problem, fill in at least these three slots. The first two with markers IDs and the last one with the markers length like in the example bellow.",
                                    justify="left", font=("Arial", 11),)
            error_message.grid(row=1, column=1)

    def marker_cube_delete(self):
        msg_box = tk.messagebox.askquestion('Delete confirmation', 'Are you sure you want to delete ' + self.cube_id_selection.get() + '?')
        if msg_box == 'yes':   
            filename = '../assets/configs/marker_cubes/{}.pkl'.format(
                self.cube_id_selection.get())
            if os.path.isfile(filename):
                os.remove(filename)

            if self.cube_ids.__contains__(self.cube_id_selection.get()):
                self.cube_ids.remove(self.cube_id_selection.get())
                self.cube_id_selection['values'] = self.cube_ids

            if len(self.cube_ids) > 0:
                self.cube_id_selection.current(0)
                self.tracking_config.cube_number = 0
                self.tracking_config.persist()
                self.marker_cube_settings_set()
            else:
                self.cube_id_selection.set("")

            self.cube_id_selected()
        for child in self.marker_cube_settings_frame.winfo_children():
            child.configure(state=tk.DISABLED)

    def refresh_video_sources(self):
        try:
            self.video_source_list = video_device_listing.get_devices()
            self.video_source['values'] = self.video_source_list
            self.video_source.current(0)
        except SystemError:
            pass

    def start_tracking(self):
        try:
            self.save_tracking_config()
            self.single_marker_save()
            self.save_camera_parameters()
            if not self.saving_error:
                self.start_tracking_event.set()

                if not self.tracking_config.show_video:
                    self.tracking_button['text'] = "Stop Tracking"
                    self.tracking_button['command'] = self.stop_tracking
        except socket.error:
            error_window = tk.Toplevel()
            error_window.title("IP Error")
            error_window.grab_set()
            error_window.resizable(0, 0)

            error_window.columnconfigure([0, 1], minsize=50, weight=1)
            error_window.rowconfigure([0, 1], minsize=50, weight=1)

            geometry_string = self.center_window(error_window, window_height=220, window_width=1100)
            error_window.geometry(geometry_string)
            
            error_title = tk.Label(master=error_window, text="IP Address is incorrect", fg="blue", font=("Arial", 18))
            error_title.grid(row=0, column=1, sticky="w")

            icon_label = tk.Label(master=error_window, image=self.icon_img, width=80, height=80)
            icon_label.grid(row=0, column=0)
            
            self.example_img = ImageTk.PhotoImage(Image.open("{}/IP_address_example.png".format(self.base_img_dir)))
            example_label = tk.Label(master=error_window, image=self.example_img, width=200, height=70)
            example_label.grid(row=2, column=1)
            
            error_message = tk.Label(master=error_window, text="This problem occurred because the IP Address slot is blank or contains an address that does not exist. \nIf the slot is empty, fill it in with an existing IP address to solve the problem. \nIf the slot is not blank, AR Tracking was not able to connect to the address you filled in because the address is not available. Check for any spelling mistakes. \nAn example of IP address is given below.",
                                     justify="left", font=("Arial", 11),)
            error_message.grid(row=1, column=1)
        except ValueError:
            error_window = tk.Toplevel()
            error_window.title("Port Error")
            error_window.grab_set()
            error_window.resizable(0, 0)

            error_window.columnconfigure([0, 1], minsize=50, weight=1)
            error_window.rowconfigure([0, 1], minsize=50, weight=1)

            geometry_string = self.center_window(error_window, window_height=180, window_width=700)
            error_window.geometry(geometry_string)
            
            error_title = tk.Label(master=error_window, text="Port is incorrect", fg="blue", font=("Arial", 18))
            error_title.grid(row=0, column=1, sticky="w")

            icon_label = tk.Label(master=error_window, image=self.icon_img, width=80, height=80)
            icon_label.grid(row=0, column=0)
            
            self.example_img = ImageTk.PhotoImage(Image.open("{}/port_example.png".format(self.base_img_dir)))
            example_label = tk.Label(master=error_window, image=self.example_img, width=270, height=80)
            example_label.grid(row=2, column=1)

            error_message = tk.Label(master=error_window, text="This problem occurred because the Port slot is blank or contains letters instead of numbers. \nTo solve this problem, fill in the Port slot with a valid port number like in the example below.",
                                     justify="left", font=("Arial", 11),)
            error_message.grid(row=1, column=1)
        except tk.TclError:
            error_window = tk.Toplevel()
            error_window.title("Tracking Error")
            error_window.grab_set()
            error_window.resizable(0, 0)

            error_window.columnconfigure([0, 1], minsize=50, weight=1)
            error_window.rowconfigure([0, 1], minsize=50, weight=1)

            geometry_string = self.center_window(error_window, window_height=180, window_width=800)
            error_window.geometry(geometry_string)

            error_title = tk.Label(master=error_window, text="Translation Offset slots are blank", fg="blue", font=("Arial", 18))
            error_title.grid(row=0, column=1, sticky="w")

            icon_label = tk.Label(master=error_window, image=self.icon_img, width=80, height=80)
            icon_label.grid(row=0, column=0)
            
            self.example_img = ImageTk.PhotoImage(Image.open("{}/translation_offset_example.png".format(self.base_img_dir)))
            example_label = tk.Label(master=error_window, image=self.example_img, width=200, height=70)
            example_label.grid(row=2, column=1)

            error_message = tk.Label(master=error_window, text="To solve this problem fill in the three slots inside the Translation Offset section with the desired distance offset. \nAn example is given bellow.",
                                     justify="left", font=("Arial", 11),)
            error_message.grid(row=1, column=1)

    def stop_tracking(self):
        self.stop_tracking_event.set()
        self.tracking_button['text'] = "Start Tracking"
        self.tracking_button['command'] = self.start_tracking
    
    def refresh_calibrations(self, _=None):
        self.calibrations_dict_list = []
        self.calibration_selection_list = []
        for calibration in os.listdir(self.base_video_source_dir):
            if calibration.find(self.video_source.get()) != -1:
                self.calibration_config = VideoSourceCalibrationConfig.persisted('{}/{}'.format(self.base_video_source_dir, calibration))
                calibration_dict = {'name': calibration, 'score': self.calibration_config.score}
                self.calibrations_dict_list.append(calibration_dict)
        
        self.database_calibrations = self.db.collection('calibrations').where('camera', '==', self.video_source.get()).order_by('score', direction=firestore.Query.DESCENDING).get()
        for calibration in self.database_calibrations:
            if calibration.to_dict().get('name', "") not in os.listdir(self.base_video_source_dir):
                self.calibrations_dict_list.append(calibration.to_dict())
        
        self.calibrations_dict_list = sorted(self.calibrations_dict_list, key=lambda d: d['score'], reverse=True)
        for calibration in self.calibrations_dict_list:
            self.calibration_selection_list.append(calibration.get('name', ""))
        
        if self.calibration_selection_list.__contains__(""):
            self.calibration_selection_list.remove("")
        
        self.calibration_selection['values'] = self.calibration_selection_list
        if len(self.calibration_selection_list) > 0:
            self.calibration_selection.current(0)
            self.calibration_selected()

    def calibration_selection_init(self):
        self.refresh_calibrations()

        if len(self.calibration_selection_list) > 0:
            self.calibration_selection.current(self.tracking_config.calibration_number) #selects the last calibration used by the AR Tracking
            self.calibration_selected()
        else:
            self.calibration_selection.set("")

    def calibration_selected(self, _=None):
        if self.calibration_selection.get() in os.listdir(self.base_video_source_dir):
            self.calibration_config = VideoSourceCalibrationConfig.persisted(
                self.get_calibration_dir())
            self.chessboard_square_size.set(self.calibration_config.chessboard_square_size)
            self.score_text.set('Score: {:.2f}'.format(self.calibration_config.score))
            self.delete_button['state'] = ACTIVE
            if self.calibration_config.score >= 7:
                self.calibrate_button['state'] = ACTIVE
                for calibration in self.database_calibrations:
                    if self.calibration_selection.get() == calibration.to_dict().get('name', ''):
                        self.calibrate_button['state'] = DISABLED
            else:
                self.calibrate_button['state'] = DISABLED

        elif self.calibration_selection.get() != "":
            for calibration in self.database_calibrations:
                if calibration.to_dict().get('name', '') == self.calibration_selection.get():
                    if calibration.to_dict().get('userId') == self.userId:
                        self.delete_button['state'] = ACTIVE
                    else:
                        self.delete_button['state'] = DISABLED
                    self.chessboard_square_size.set(calibration.to_dict().get('chessboard_square_size'))
                    self.score_text.set('Score: {:.2f}'.format(calibration.to_dict().get('score')))
            self.calibrate_button['state'] = DISABLED
            

    def author_updated(self):
        self.calibration_selection.set('{}-{}-{}'.format(self.video_source.get(), len(self.database_calibrations), self.author.get()))
    
    def add_calibration(self):
        if self.calibration_selection_list.__contains__(""):
            self.calibration_selection_list.remove("")

        self.calibration_selection.set('{}-{}-{}'.format(self.video_source.get(), len(self.database_calibrations), self.author.get()))
        self.author_entry['state'] = 'normal'
        self.chessboard_square_size_entry['state'] = ACTIVE
        self.chessboard_square_size.set("")
        self.calibrate_button.configure(text='Calibrate', command=self.calibrate)
        self.calibrate_button['state'] = ACTIVE
        self.test_button['state'] = DISABLED
        self.delete_button['state'] = ACTIVE
    
    def calibrate(self):
        try:    
            self.calibration = VideoSourceCalibration(
                self.get_calibration_dir(), self.video_source.current(), self.chessboard_square_size.get())

            calibration_score = self.calibration.calibrate()
            self.save_calibration_config(calibration_score)
            self.author_entry['state'] = DISABLED
            self.chessboard_square_size_entry['state'] = DISABLED
            self.calibrate_button.configure(text='Add calibration to database', command=self.add_calibration_to_database)
            self.calibrate_button['state'] = DISABLED
            self.test_button['state'] = ACTIVE

            if not self.calibration_selection_list.__contains__(self.calibration_selection.get()):
                calibration_dict = {'name': self.calibration_selection.get(), 'score': calibration_score}
                self.calibrations_dict_list.append(calibration_dict)
                self.calibrations_dict_list = sorted(self.calibrations_dict_list, key=lambda d: d['score'], reverse=True)
                self.calibration_selection_list = []
                for calibration in self.calibrations_dict_list:
                    self.calibration_selection_list.append(calibration.get('name', ""))

            if self.calibration_selection_list.__contains__(""):
                    self.calibration_selection_list.remove("")
            
            self.calibration_selection['values'] = self.calibration_selection_list
            if calibration_score >= 7:
                self.calibrate_button['state'] = ACTIVE
                msg_box = tk.messagebox.askquestion('Add calibration to database', 'Congratulations!! \nYou have just created a calibration that surpasses the minimum score required to add it to our database. By adding the calibration to the database you help to improve the experience of other users so they don\'t need to create a new calibration. \nWould you like to add the calibration ' + self.calibration_selection.get() + ' to the database?')
                if msg_box == 'yes':
                    self.add_calibration_to_database()
        except tk.TclError:
            error_window = tk.Toplevel()
            error_window.title("Calibration Error")
            error_window.grab_set()
            error_window.resizable(0, 0)
            error_window.columnconfigure([0, 1], minsize=50, weight=1)
            error_window.rowconfigure([0, 1], minsize=50, weight=1)

            geometry_string = self.center_window(error_window, window_height=270, window_width=1100)
            error_window.geometry(geometry_string)

            error_title = tk.Label(master=error_window, text="Chessboard square size is incorrect", fg="blue", font=("Arial", 18))
            error_title.grid(row=0, column=1, sticky="w")

            icon_label = tk.Label(master=error_window, image=self.icon_img, width=80, height=80)
            icon_label.grid(row=0, column=0)
            
            self.example_img = ImageTk.PhotoImage(Image.open("{}/calibration_example.png".format(self.base_img_dir)))
            example_label = tk.Label(master=error_window, image=self.example_img, width=500, height=130)
            example_label.grid(row=2, column=1)

            error_message = tk.Label(master=error_window, text="This problem occurred because the Chessboard Square size slot is blank or contains letters instead of numbers. \nIn order to start the calibration, it is necessary to fill in the Chessboard Square size slot with the chessboard square side length like in the example below.",
                                     justify="left", font=("Arial", 11))
            error_message.grid(row=1, column=1)

    def add_calibration_to_database(self):
        calibration_dir = self.get_calibration_dir()
        if os.path.exists(calibration_dir) and os.path.isfile("{}/cam_mtx.npy".format(calibration_dir)) and os.path.isfile("{}/dist.npy".format(calibration_dir)):
            cam_mtx = np.load(
                "{}/cam_mtx.npy".format(calibration_dir))
            dist = np.load(
                "{}/dist.npy".format(calibration_dir))
        self.calibration_config = VideoSourceCalibrationConfig.persisted(calibration_dir)

        data = {'camera': self.video_source.get(), 
                'camera_matrix': [cam_mtx[0][0], cam_mtx[1][1], cam_mtx[0][2], cam_mtx[1][2]], 
                'chessboard_square_size': self.calibration_config.chessboard_square_size, 
                'distortion_coefficients': [dist[0][0], dist[0][1], dist[0][2], dist[0][3], dist[0][4]], 
                'name': self.calibration_selection.get(), 
                'score': self.calibration_config.score,
                'userId': self.userId}
        self.db.collection('calibrations').add(data)
        self.database_calibrations = self.db.collection('calibrations').where('camera', '==', self.video_source.get()).get()
        self.db.collection('users').document(self.userId).update({'size': firestore.Increment(1)})
        
        self.calibrate_button['state'] = DISABLED
    
    def enable_chessboard_entry(self):
        self.test_button['state'] = DISABLED
        self.chessboard_square_size_entry['state'] = ACTIVE
        self.chessboard_square_size_entry.bind('<Return>', self.test_calibration)
    
    def test_calibration(self, event):
        self.calibration = VideoSourceCalibration(
                self.get_calibration_dir(), self.video_source.current(), self.chessboard_square_size.get())
        self.save_camera_parameters()
        score = self.calibration.test()
        if score != -1:
            result_window = tk.Toplevel()
            result_window.title("Test Result")
            result_window.grab_set()
            result_window.resizable(0, 0)
            score_label = tk.Label(master=result_window, text='Final score: {:.2f}'.format(score), font=("Arial", 18, 'bold'))
            score_label.grid(row=0, column= 0, pady=5)
            calibration_label = tk.Label(master=result_window, text='Attention: we do not reccomend using a calibration that scores lower than 7 for applications that require high precision.', font=('Arial', 11, 'bold'), fg='red')
            calibration_label.grid(row=1, column=0, pady=5)
        self.chessboard_square_size_entry['state'] = DISABLED
        self.chessboard_square_size_entry.unbind('<Return>')
        self.test_button['state'] = ACTIVE
    
    def delete_calibration(self):
        if self.calibration_selection.get() != "":
            folder_name = '../assets/camera_calibration_data/{}'.format(self.calibration_selection.get())
            if os.path.exists(folder_name):
                msg_box = tk.messagebox.askquestion('Delete confirmation', 'Are you sure you want to delete ' + self.calibration_selection.get() + ' from your computer?')
                if msg_box == 'yes':
                    if os.path.isfile('{}/cam_mtx.npy'.format(folder_name)):
                        os.remove('{}/cam_mtx.npy'.format(folder_name))

                    if os.path.isfile('{}/dist.npy'.format(folder_name)):
                        os.remove('{}/dist.npy'.format(folder_name))

                    if os.path.isfile('{}/calibration_config_data.pkl'.format(folder_name)):
                        os.remove('{}/calibration_config_data.pkl'.format(folder_name))

                    os.rmdir(folder_name)

                    if self.calibration_selection_list.__contains__(self.calibration_selection.get()):
                        self.calibrations_dict_list = [dict for dict in self.calibrations_dict_list if not (dict['name'] == self.calibration_selection.get())]
                        self.calibration_selection_list.remove(self.calibration_selection.get())
                        if self.calibration_selection_list.__contains__(""):
                            self.calibration_selection_list.remove("")
                        self.calibration_selection['values'] = self.calibration_selection_list

                    if len(self.calibration_selection_list) > 0:
                        self.calibration_selection.current(0)
                        self.tracking_config.calibration_number = 0
                        self.tracking_config.persist()
                    else:
                        self.calibration_selection.set("")

                    self.calibration_selected()
            else:
                msg_box = tk.messagebox.askquestion('Delete confirmation', 'Are you sure you want to delete ' + self.calibration_selection.get() + ' from the database?')
                if msg_box == 'yes':
                    for calibration in self.database_calibrations:
                        if calibration.to_dict().get('name', '') == self.calibration_selection.get():
                            self.db.collection('calibrations').document(calibration.id).delete()
                            self.db.collection('users').document(self.userId).update({'size':firestore.Increment(-1)})
                    
                    if self.calibration_selection_list.__contains__(self.calibration_selection.get()):
                        self.calibrations_dict_list = [dict for dict in self.calibrations_dict_list if not (dict['name'] == self.calibration_selection.get())]
                        self.calibration_selection_list.remove(self.calibration_selection.get())
                        if self.calibration_selection_list.__contains__(""):
                            self.calibration_selection_list.remove("")
                        self.calibration_selection['values'] = self.calibration_selection_list

                    if len(self.calibration_selection_list) > 0:
                        self.calibration_selection.current(0)
                        self.tracking_config.calibration_number = 0
                        self.tracking_config.persist()
                    else:
                        self.calibration_selection.set("")

                    self.calibration_selected()

        self.author_entry['state'] = DISABLED
        self.chessboard_square_size_entry['state'] = DISABLED
        self.calibrate_button.configure(text='Add calibration to database', command=self.add_calibration_to_database)
        self.test_button['state'] = ACTIVE


    def save_camera_parameters(self):
        calibration_dir = self.get_calibration_dir()
        if os.path.exists(calibration_dir) and os.path.isfile("{}/cam_mtx.npy".format(calibration_dir)) and os.path.isfile("{}/dist.npy".format(calibration_dir)):
            cam_mtx = np.load(
                "{}/cam_mtx.npy".format(calibration_dir))
            dist = np.load(
                "{}/dist.npy".format(calibration_dir))
            
            np.save('../assets/configs/selected_cam_mtx.npy', cam_mtx)
            np.save('../assets/configs/selected_dist.npy', dist)
        else:
            for calibration in self.database_calibrations:
                if calibration.to_dict().get('name', '') == self.calibration_selection.get():
                    calibration_dict = calibration.to_dict()
                    cam_mtx = np.array([[calibration_dict['camera_matrix'][0], 0                              ,  calibration_dict['camera_matrix'][2]],
                                        [0                              , calibration_dict['camera_matrix'][1],  calibration_dict['camera_matrix'][3]],
                                        [0                              , 0                              , 1                               ]])
                    dist = np.array([calibration_dict['distortion_coefficients']])

                    np.save('../assets/configs/selected_cam_mtx.npy', cam_mtx)
                    np.save('../assets/configs/selected_dist.npy', dist)

    def get_video_source_dir(self):
        camera_identification = self.video_source.get().replace(" ", "_")
        return '{}/{}'.format(self.base_video_source_dir, camera_identification)

    def get_calibration_dir(self):
        calibration_identification = self.calibration_selection.get()
        return '{}/{}'.format(self.base_video_source_dir, calibration_identification)

    def save_tracking_config(self):
        self.tracking_config.device_number = self.video_source.current()
        self.tracking_config.device_calibration_dir = self.get_calibration_dir()
        self.tracking_config.calibration_number = self.calibration_selection.current()
        self.tracking_config.cube_number = self.cube_id_selection.current()
        self.tracking_config.show_video = self.show_video.get()
        self.tracking_config.flip_video = self.flip_video.get()
        if self.server_ip.get() != "localhost":
            socket.inet_aton(self.server_ip.get())
        self.tracking_config.server_ip = self.server_ip.get()
        int(self.server_port.get())
        self.tracking_config.server_port = self.server_port.get()
        if self.video_server_ip.get() != "localhost":
            socket.inet_aton(self.video_server_ip.get())
        self.tracking_config.video_server_ip = self.video_server_ip.get()
        int(self.video_server_port.get())
        self.tracking_config.video_server_port = self.video_server_port.get()
        if self.websocket_server_ip.get() != "localhost":
            socket.inet_aton(self.websocket_server_ip.get())
        self.tracking_config.websocket_server_ip = self.websocket_server_ip.get()
        int(self.websocket_server_port.get())
        self.tracking_config.websocket_server_port = self.websocket_server_port.get()
        if self.websocket_video_server_ip.get() != "localhost":
            socket.inet_aton(self.websocket_video_server_ip.get())
        self.tracking_config.websocket_video_server_ip = self.websocket_video_server_ip.get()
        int(self.websocket_video_server_port.get())
        self.tracking_config.websocket_video_server_port = self.websocket_video_server_port.get()

        marker_detection_settings = None
        if self.single_marker_mode.get():
            marker_detection_settings = self.single_marker_settings
        elif self.marker_cube_mode.get():
            marker_detection_settings = self.marker_cube_settings

        self.tracking_config.marker_detection_settings = marker_detection_settings

        offset_matrix = np.zeros(shape=(4, 4))
        offset_matrix[0][0] = 1
        offset_matrix[1][1] = 1
        offset_matrix[2][2] = 1
        offset_matrix[0][3] = self.translation_offset_x.get()
        offset_matrix[1][3] = self.translation_offset_y.get()
        offset_matrix[2][3] = self.translation_offset_z.get()
        offset_matrix[3][3] = 1
        self.tracking_config.translation_offset = offset_matrix

        self.tracking_config.persist()

    def save_calibration_config(self, calibration_score):
        self.calibration_config.chessboard_square_size = self.chessboard_square_size.get()
        self.calibration_config.persist(self.get_calibration_dir(), calibration_score)

    def center_window(self, window, window_height, window_width):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        x_cordinate = int((screen_width/2) - (window_width/2))
        y_cordinate = int((screen_height/2) - (window_height/2))

        return "{}x{}+{}+{}".format(window_width, window_height, x_cordinate, y_cordinate)

class LoginInterface():

    def __init__(self, start_tracking, stop_tracking, window):
        self.start_tracking_event = start_tracking
        self.stop_tracking_event = stop_tracking
        self.window = window
        self.base_img_dir = '../images'
        self.logo = ImageTk.PhotoImage(Image.open("{}/interlab_logo_transparent.png".format(self.base_img_dir)))
        self.visible_icon = ImageTk.PhotoImage(Image.open("{}/visible.png".format(self.base_img_dir)))
        self.invisible_icon = ImageTk.PhotoImage(Image.open("{}/invisible.png".format(self.base_img_dir)))

        firebase_config={
                'apiKey': "AIzaSyCJar67v1udral1xBr40o3JcfJK_Po-ohE",
                'authDomain': "ar-tracking-database-479f3.firebaseapp.com",
                'databaseURL': '',
                'projectId': "ar-tracking-database-479f3",
                'storageBucket': "ar-tracking-database-479f3.appspot.com",
                'messagingSenderId': "772321532641",
                'appId': "1:772321532641:web:a53d5fa42dda057af2b5a0"
            }
        firebase=pyrebase.initialize_app(firebase_config)
        self.auth = firebase.auth()

        self.window.title('AR Tracking Interface')

        width = 300
        height = 390
        pos_x = (window.winfo_screenwidth()/2) - (width/2)
        pos_y = (window.winfo_screenheight()/2) - (height/2)
        window.geometry('%dx%d+%d+%d' % (width, height, pos_x, pos_y))
        window.resizable(0, 0)

        # Create some room around all the internal frames
        window['padx'] = 5
        window['pady'] = 5

        window.grid_rowconfigure(1, weight=1)
        window.grid_rowconfigure(2, weight=1)
        window.grid_rowconfigure(3, weight=1)
        window.grid_rowconfigure(4, weight=1)
        window.grid_columnconfigure(1, weight=1)

        self.login_frame = tk.Frame(self.window)
        self.login_frame.pack()

        self.login_title = tk.Label(self.login_frame, text="Login", font=('Arial', 18))
        self.login_title.grid(row=0, column=0)
        
        self.login_logo = tk.Label(master=self.login_frame, image=self.logo, width=80, height=80)
        self.login_logo.grid(row=1, column=0)

        self.login_username_label = tk.Label(
            self.login_frame, text='Email', font=('Arial', 14))
        self.login_username_label.grid(row=2, column=0, sticky='w', pady=2.5) 
        self.login_username_entry = tk.Entry(
            self.login_frame, width=40)
        self.login_username_entry.grid(row=3, column=0, sticky='we', pady=2.5)

        self.login_password_frame = tk.Frame(self.login_frame)
        self.login_password_frame.grid(row=4, column=0, pady=2.5, sticky='we')

        self.login_password_label = tk.Label(
            self.login_password_frame, text='Password', font=('Arial', 14))
        self.login_password_label.grid(row=0, column=0, sticky='w', pady=2.5)
        self.login_password_entry = tk.Entry(
            self.login_password_frame, width=40, show='*')
        self.login_password_entry.grid(row=1, column=0, sticky='w', pady=2.5)
        self.login_showpass_button = tk.Button(
            self.login_password_frame, image=self.visible_icon, command=lambda: self.show_password(self.login_password_entry, self.login_showpass_button))
        self.login_showpass_button.grid(row=1, column=1, sticky='e')

        self.other_options_frame = tk.Frame(self.login_frame)  # mudar o nome desse frame para um nome melhor
        self.other_options_frame.rowconfigure(0, weight=1)
        self.other_options_frame.columnconfigure(0, weight=1)
        self.other_options_frame.columnconfigure(1, weight=1)

        self.other_options_frame.grid(row=6, column=0, sticky='we', pady=2.5)

        #self.remember_me_checkbox = tk.Checkbutton(
        #    self.other_options_frame, text='Remember me')
        #self.remember_me_checkbox.grid(row=0, column=0, sticky='w', pady=2.5)
        self.forgot_password_button = tk.Button(
            self.other_options_frame, text='Forgot Password?', command=self.open_reset_password_window)
        self.forgot_password_button.grid(row=0, column=1, sticky='e', pady=2.5)

        self.login_button = tk.Button(
            self.login_frame, text='Login', command=self.login)
        self.login_button.grid(row=7, column=0, pady=2.5)

        self.error_frame = tk.Label(self.login_frame)
        self.error_message = tk.Label(
            self.error_frame, text='', fg='red')
        self.error_message.pack(side=LEFT)
        self.error_button = tk.Button(
                    self.error_frame, text='Verify your email', fg='red')
        
        self.register_question_frame = tk.Frame(self.login_frame)
        self.register_question_frame.grid(row=9, column=0, pady=5)

        self.register_label = tk.Label(
            self.register_question_frame, text='Don\'t have an account yet?')
        self.register_label.grid(row=0, column=0, sticky='e')
        self.register_button = tk.Button(
            self.register_question_frame, text='Register', command=self.change_to_register)
        self.register_button.grid(row=0, column=1, sticky='w')

        self.register_frame = tk.Frame(self.window)

        self.register_title = tk.Label(self.register_frame, text='Sign up', font=('Arial', 18))
        self.register_title.grid(row=0, column=0)

        self.register_logo = tk.Label(master=self.register_frame, image=self.logo, width=80, height=80)
        self.register_logo.grid(row=1, column=0)

        self.register_username_label = tk.Label(
            self.register_frame, text='Email', font=('Arial', 14))
        self.register_username_label.grid(row=2, column=0, sticky='w', pady=2.5)
        self.register_username_entry = tk.Entry(
            self.register_frame, width=40)
        self.register_username_entry.grid(row=3, column=0, sticky='we', pady=2.5)

        self.register_password_frame = tk.Frame(self.register_frame)
        self.register_password_frame.grid(row=4, column=0, pady=2.5)
        
        self.register_password_label = tk.Label(
            self.register_password_frame, text='Password', font=('Arial', 14))
        self.register_password_label.grid(row=0, column=0, sticky='w', pady=2.5)
        self.register_password_entry = tk.Entry(
            self.register_password_frame, width=40, show='*')
        self.register_password_entry.grid(row=1, column=0, sticky='we', pady=2.5)
        self.register_showpass_button = tk.Button(
            self.register_password_frame, image=self.visible_icon, command=lambda: self.show_password(self.register_password_entry, self.register_showpass_button))
        self.register_showpass_button.grid(row=1, column=1, sticky='e')

        self.register_confirmpass_label = tk.Label(
            self.register_password_frame, text='Confirm Password', font=('Arial', 14))
        self.register_confirmpass_label.grid(row=2, column=0, sticky='w', pady=2.5)
        self.register_confirmpass_entry = tk.Entry(
            self.register_password_frame, width=40, show='*')
        self.register_confirmpass_entry.grid(row=3, column=0, sticky='we', pady=2.5)
        self.register_showconfirmpass_button = tk.Button(
            self.register_password_frame, image=self.visible_icon, command=lambda: self.show_password(self.register_confirmpass_entry, self.register_showconfirmpass_button))
        self.register_showconfirmpass_button.grid(row=3, column=1, sticky='e')

        self.create_account_button = tk.Button(
            self.register_frame, text='Create account', command=self.register)
        self.create_account_button.grid(row=8, column=0, pady=10)

        self.error_email_exists = tk.Label(
            self.register_frame, text='Email is already in use.', fg='red')

        self.menu_bar = tk.Menu(window)
        self.menu_help = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_help.add_command(label='Manual', command=self.open_manual)
        self.menu_help.add_command(label="About", command=self.create_about_window)
        self.menu_bar.add_cascade(label="Help", menu=self.menu_help)

        window.config(menu=self.menu_bar)

    def login(self):
        try:
            response = self.sign_in_with_email_and_password("AIzaSyCJar67v1udral1xBr40o3JcfJK_Po-ohE", self.login_username_entry.get(), self.login_password_entry.get())

            #print(response)        
            email_verified = self.auth.get_account_info(response.get('idToken')).get('users')[0].get('emailVerified')
            if email_verified:
                creds = Credentials(response['idToken'], response['refreshToken'])
                    
                db = Client('ar-tracking-database-479f3', creds)

                userId = self.auth.get_account_info(response.get('idToken')).get('users')[0].get("localId")
                if not db.collection('users').document(userId).get().exists:
                    data = {'size': 0}
                    db.collection('users').document(userId).set(data)

                self.login_frame.pack_forget()
                App(self.start_tracking_event, self.stop_tracking_event, self.window, db, userId)
            else:
                self.error_message.configure(text='Unverified email.')
                self.error_button.configure(command=lambda: self.send_email_verification_link(response))
                self.error_button.pack(side=LEFT)
                self.error_frame.grid(row=8, column=0)
        except:
            self.error_button.pack_forget()
            self.error_message.configure(text='Invalid email and/or password.')
            self.error_frame.grid(row=8, column=0)

    def register(self):
        try:
            if self.register_confirmpass_entry.get() == self.register_password_entry.get():
                new_user = self.auth.create_user_with_email_and_password(self.register_username_entry.get(), self.register_password_entry.get())
                    
                self.error_email_exists.grid_forget()
                self.send_email_verification_link(new_user)

                email_verified = self.auth.get_account_info(new_user.get('idToken')).get('users')[0].get('emailVerified')
                if email_verified:
                    response = self.sign_in_with_email_and_password("AIzaSyCJar67v1udral1xBr40o3JcfJK_Po-ohE", self.register_username_entry.get(), self.register_password_entry.get())
                    creds = Credentials(response['idToken'], response['refreshToken'])

                    db = Client('ar-tracking-database-479f3', creds)
                        
                    userId = self.auth.get_account_info(response.get('idToken')).get('users')[0].get("localId")
                    if not db.collection('users').document(userId).get().exists:
                        data = {'size': 0}
                        db.collection('users').document(userId).set(data)

                    self.login_frame.pack_forget()
                    self.register_frame.pack_forget()
                    App(self.start_tracking_event, self.stop_tracking_event, self.window, db, userId)
                else:
                    self.register_frame.pack_forget()
                    self.login_frame.pack()
        except:
            self.error_email_exists.grid(row=9, column=0)


    def change_to_register(self):
        self.login_frame.pack_forget()
        self.register_frame.pack()

    def show_password(self, password_entry, button):
        password_entry['show'] = ''
        button.configure(image=self.invisible_icon, command=lambda: self.hide_password(password_entry, button))

    def hide_password(self, password_entry, button):
        password_entry['show'] = '*'
        button.configure(image=self.visible_icon, command=lambda: self.show_password(password_entry, button))

    def sign_in_with_email_and_password(self, api_key, email, password):
        request_url = "%s:signInWithPassword?key=%s" % (FIREBASE_REST_API, api_key)
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
        
        resp = requests.post(request_url, headers=headers, data=data)
            
        return resp.json()
    
    def send_email_verification_link(self, user):
        payload = json.dumps({'requestType': 'VERIFY_EMAIL', 'idToken': user.get('idToken')})
        r = requests.post("https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode", 
                      params={'key': 'AIzaSyCJar67v1udral1xBr40o3JcfJK_Po-ohE'},
                      data=payload)

        tk.messagebox.showwarning("Verify your email", "In order to use AR Tracking you need to verify your account. \nAn email was sent to " + self.register_username_entry.get() + " containing the instructions to verify your account.")

    def open_reset_password_window(self):
        forgot_pass_window = tk.Toplevel()
        forgot_pass_window.title("Reset your password")
        forgot_pass_window.grab_set()
        forgot_pass_window.resizable(0,0)

        self.title = tk.Label(
            forgot_pass_window, text='Forgot your password?', font=('Arial', 18, 'bold'))
        self.title.grid(row=0, column=0, sticky='w', pady=5)
        self.message = tk.Label(
            forgot_pass_window, text='Insert your email in the field below to reset your password. \nAfter pressing the button, you will receive an email containing a link allowing you to reset your password.', font=('Arial', 11), justify=LEFT)
        self.message.grid(row=1, column=0, sticky='w', pady=5)

        self.email_frame = tk.Frame(forgot_pass_window)
        self.email_frame.grid(row=2, column=0, pady=5)
        self.email_entry = tk.Entry(
            self.email_frame, width=80)
        self.email_entry.grid(row=0, column=0, padx=5)
        email_button = tk.Button(
            self.email_frame, text='Send email', command=self.send_reset_password_link)
        email_button.grid(row=0, column=1, padx=5)

    def send_reset_password_link(self):
        payload = json.dumps({'requestType': 'PASSWORD_RESET', 'email': self.email_entry.get()})
        r = requests.post("https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?", 
                      params={'key': 'AIzaSyCJar67v1udral1xBr40o3JcfJK_Po-ohE'},
                      data=payload)
        
        self.title.configure(text='Email sent successfully')
        self.message.configure(text='An email containing instructions to reset your password was sent to the informed email.')
        self.email_frame.grid_forget()

    def open_manual(self):
        webbrowser.open_new('https://docs.google.com/document/d/183dZg2_0UBD8IP1P4XLX4uSmWgOMQhZjNsOYzaSrt_M/edit')

    def create_about_window(self):
        about_window = tk.Toplevel()
        about_window.title("About")
        about_window.grab_set()
        about_window.resizable(0, 0)
        version_label = tk.Label(master=about_window, text='Version: 0.00.0')
        version_label.grid(sticky='nw')
        credits_label = tk.Label(master=about_window, text='Credits: Igor Ortega\n              Lucca Catalan de Freitas Reis Viana\n              Vitor Santos', justify='left')
        credits_label.grid(sticky='nw')

        window_height = 80
        window_width = 250

        screen_width = about_window.winfo_screenwidth()
        screen_height = about_window.winfo_screenheight()

        x_cordinate = int((screen_width/2) - (window_width/2))
        y_cordinate = int((screen_height/2) - (window_height/2))

        about_window.geometry("{}x{}+{}+{}".format(window_width, window_height, x_cordinate, y_cordinate))


    
if __name__ == "__main__":
    multiprocessing.freeze_support()

    start_tracking_event = multiprocessing.Event()
    stop_tracking_event = multiprocessing.Event()

    tracking_scheduler_process = multiprocessing.Process(
        target=TrackingScheduler(start_tracking_event, stop_tracking_event).main)
    tracking_scheduler_process.start()

    tk_root = tk.Tk()
    LoginInterface(start_tracking_event, stop_tracking_event, tk_root)
    tk_root.mainloop()

    stop_tracking_event.set()
    time.sleep(1)
    tracking_scheduler_process.terminate()