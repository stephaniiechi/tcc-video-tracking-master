import tkinter as tk
import multiprocessing
import time
from tracking import TrackingScheduler
from ar_tracking import AppWithoutLogin
from login_interface import LoginInterface
from main_menu import MainMenu
import xml.etree.ElementTree as ET

FIREBASE_REST_API = "https://identitytoolkit.googleapis.com/v1/accounts"
    
if __name__ == "__main__":
    multiprocessing.freeze_support()

    start_tracking_event = multiprocessing.Event()
    stop_tracking_event = multiprocessing.Event()

    tracking_scheduler_process = multiprocessing.Process(target=TrackingScheduler(start_tracking_event, stop_tracking_event).main)
    tracking_scheduler_process.start()

    tk_root = tk.Tk()

    # Get configs from XML file
    config = ET.parse('config.xml')
    login_option = config.getroot()
    value = login_option.attrib['value']

    if value.lower() == "true":
        LoginInterface(start_tracking_event, stop_tracking_event, tk_root)
    else:
        # start_tracking_event, stop_tracking_event, window, login, db, userId:
        MainMenu(start_tracking_event, stop_tracking_event, tk_root, False, None, None)

    tk_root.mainloop()

    stop_tracking_event.set()
    time.sleep(1)
    tracking_scheduler_process.terminate()