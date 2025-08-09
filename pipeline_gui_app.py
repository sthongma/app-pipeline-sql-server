try:
    import customtkinter as ctk
except ImportError as e:
    raise SystemExit(
        "ไม่พบไลบรารี customtkinter จำเป็นต้องติดตั้งก่อนใช้งาน UI.\n"
        "ติดตั้งด้วยคำสั่ง: pip install customtkinter"
    ) from e

from ui.login_window import LoginWindow
import logging
from utils.logger import setup_logging
import os

def main():
    # ตั้ง working directory เป็นที่อยู่ของไฟล์นี้
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # ตั้งค่า appearance mode และ theme
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    
    # ตั้งค่า logging มาตรฐาน
    setup_logging(level=logging.INFO)
    
    # สร้างหน้าต่างล็อกอิน
    login_window = LoginWindow()
    login_window.mainloop()

if __name__ == '__main__':
    main()