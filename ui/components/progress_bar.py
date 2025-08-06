import customtkinter as ctk

class ProgressBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, width=850, height=10)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)
        
        # Label แสดงความคืบหน้า
        self.progress_label = ctk.CTkLabel(self, text="")
        self.progress_label.pack(pady=2)

    def update(self, progress):
        """อัปเดต Progress Bar"""
        self.progress_bar.set(progress)

    def reset(self):
        """รีเซ็ต Progress Bar"""
        self.progress_bar.set(0) 