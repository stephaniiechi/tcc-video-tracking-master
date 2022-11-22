import tkinter as tk
from PIL import ImageTk, Image
from app_without_login import AppWithoutLogin
from app_with_login import AppWithLogin

class MainMenu():
    def __init__(self, start_tracking_event, stop_tracking_event, window, login, db, userId):
        # para abrir o ar tracking
        self.start_tracking_event = start_tracking_event
        self.stop_tracking_event = stop_tracking_event
        # com login
        self.login = login
        self.db = db
        self.userId = userId

        # pegar algumas imagens/logos
        self.base_img_dir = '../images'
        self.logo = ImageTk.PhotoImage((Image.open("{}/interlab_logo_transparent.png".format(self.base_img_dir))).resize((40, 40)))
        
        self.window = window
        self.window.title('Menu')

        width = 350
        height = 310
        pos_x = (window.winfo_screenwidth()/2) - (width/2)
        pos_y = (window.winfo_screenheight()/2) - (height/2)
        window.geometry('%dx%d+%d+%d' % (width, height, pos_x, pos_y))
        window.resizable(0, 0)

        window['padx'] = 10
        window['pady'] = 10

        # ------------------------------------

        self.tracking_frame = tk.Frame(self.window)
        self.tracking_frame.pack()

        self.title_label = tk.Label(self.tracking_frame, 
                                    text="Método de rastreamento", 
                                    font=('Arial', 18))
        self.title_label.grid(row=0, column=0, padx=2, pady=10)

        # AR TRACKING
        self.artracking_button = tk.Button(self.tracking_frame, 
                                           text='AR Tracking',
                                           font=('Arial', 16),
                                           width=20,
                                           height=2,
                                           command=self.open_artracking_interface)
        self.artracking_button.grid(row=1, column=0, padx=5, pady=5)

        # SERINGA HÁPTICA
        self.haptic_button = tk.Button(self.tracking_frame, 
                                       text='Seringa Háptica',
                                       font=('Arial', 16),
                                       width=20,
                                       height=2,
                                       command=self.open_haptic_interface)
        self.haptic_button.grid(row=2, column=0, padx=5, pady=5)

        # HAND TRACKING
        self.hand_button = tk.Button(self.tracking_frame, 
                                     text='Hand Tracking',
                                     font=('Arial', 16),
                                     width=20,
                                     height=2,
                                     command=self.open_hand_tracking)
        self.hand_button.grid(row=3, column=0, padx=5, pady=5)

    def open_artracking_interface(self):
        self.tracking_frame.pack_forget() # Apaga todas as configurações feitas nessa janela de main menu
        if (self.login == True):
            AppWithLogin(self.start_tracking_event, self.stop_tracking_event, self.window, self.db, self.userId)
        else:
            AppWithoutLogin(self.start_tracking_event, self.stop_tracking_event, self.window)
    
    def open_haptic_interface(self):
        self.tracking_frame.pack_forget() # Apaga todas as configurações feitas nessa janela de main menu
        AppWithoutLogin(self.start_tracking_event, self.stop_tracking_event, self.window)

    def open_hand_tracking(self):
        dir = '../'
        exec(open('../hands.py').read())

    # def showtip(self):
