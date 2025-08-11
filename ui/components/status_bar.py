import customtkinter as ctk

class StatusBar(ctk.CTkLabel):
    def __init__(self, master, **kwargs):
        super().__init__(master, text="Status: Not checked", text_color="#7a7a7a", **kwargs)

    def update_status(self, message, is_error=False):
        """อัปเดตสถานะ"""
        self.configure(
            text=f"Status: {message}",
            text_color=("#d9534f" if is_error else "#46b37d")
        )