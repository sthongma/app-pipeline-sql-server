import customtkinter as ctk
from ui import theme

class StatusBar(ctk.CTkLabel):
    def __init__(self, master, **kwargs):
        super().__init__(master, text="สถานะ: ยังไม่ตรวจสอบ", text_color="#7a7a7a", font=theme.FONT_SMALL, **kwargs)

    def update_status(self, message, is_error=False):
        """อัปเดตสถานะ"""
        self.configure(
            text=f"สถานะ: {message}",
            text_color=("#d9534f" if is_error else "#46b37d")
        )