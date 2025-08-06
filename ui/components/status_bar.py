import customtkinter as ctk

class StatusBar(ctk.CTkLabel):
    def __init__(self, master, **kwargs):
        super().__init__(master, text="สถานะ: ยังไม่ตรวจสอบ", text_color="gray", **kwargs)

    def update_status(self, message, is_error=False):
        """อัปเดตสถานะ"""
        self.configure(
            text=f"สถานะ: {message}",
            text_color="red" if is_error else "green"
        ) 