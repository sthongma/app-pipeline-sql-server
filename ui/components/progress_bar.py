import customtkinter as ctk

class ProgressBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, width=850, height=10)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)

    def update(self, progress, status_text="", detail_text=""):
        """อัปเดต Progress Bar"""
        self.progress_bar.set(progress)

    def reset(self):
        """รีเซ็ต Progress Bar"""
        self.progress_bar.set(0)
        
    def set_status(self, status_text, detail_text=""):
        """ตั้งค่าสถานะ (รักษา method ไว้เพื่อความเข้ากันได้)"""
        pass  # ไม่ทำอะไรเนื่องจากไม่มีข้อความแล้ว 