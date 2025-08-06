try:
    import customtkinter as ctk
except ImportError:
    import tkinter as ctk

from ui.main_window import MainWindow
from ui.login_window import LoginWindow
from services.database_service import DatabaseService
import os

def main():
    # ตั้ง working directory เป็นที่อยู่ของไฟล์นี้
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # ตั้งค่า appearance mode และ theme
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    
    # สร้างหน้าต่างล็อกอิน
    login_window = LoginWindow()
    login_window.mainloop()

if __name__ == '__main__':
    main()