from google.oauth2.credentials import Credentials
from google.cloud.firestore import Client
import pyrebase
import json
import requests
import tkinter as tk
from tkinter import LEFT
from PIL import ImageTk, Image
import webbrowser
from app_with_login import AppWithLogin
from main_menu import MainMenu

FIREBASE_REST_API = "https://identitytoolkit.googleapis.com/v1/accounts"

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
                login_bool = True
                MainMenu(self.start_tracking_event, self.stop_tracking_event, self.window, login_bool, db, userId)
                # AppWithLogin(self.start_tracking_event, self.stop_tracking_event, self.window, db, userId)
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
                    AppWithLogin(self.start_tracking_event, self.stop_tracking_event, self.window, db, userId)
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
