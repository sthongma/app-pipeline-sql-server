try:
    import customtkinter as ctk
except ImportError as e:
    raise SystemExit(
        "ไม่พบไลบรารี customtkinter จำเป็นต้องติดตั้งก่อนใช้งาน UI.\n"
        "ติดตั้งด้วยคำสั่ง: pip install customtkinter"
    ) from e

from ui.login_window import LoginWindow
from ui import theme
import logging
from utils.logger import setup_logging
import os

def main():
    # ตั้ง working directory เป็นที่อยู่ของไฟล์นี้
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # ตั้งค่า appearance mode และ theme (โทนมินิมอล)
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("dark-blue")
    # ปรับสเกลเริ่มต้นให้สมดุล
    try:
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)
    except Exception:
        pass
    
    # ตั้งค่า logging มาตรฐาน
    setup_logging(level=logging.INFO)
    
    # สร้างหน้าต่างล็อกอิน
    login_window = LoginWindow()
    
    # ตั้งค่า font ส่วนกลาง (Kanit > Segoe UI > Arial) หลังสร้าง window แล้ว
    try:
        theme.init_fonts()
        # บังคับใช้ฟอนต์กับ login window
        theme.apply_fonts(login_window)
    except Exception:
        pass
    login_window.mainloop()

if __name__ == '__main__':
    main()