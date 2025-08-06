import customtkinter as ctk

class ProgressBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, width=850, height=10)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)
        
        # Label แสดงความคืบหน้า
        self.progress_label = ctk.CTkLabel(self, text="พร้อมใช้งาน", font=("Arial", 12))
        self.progress_label.pack(pady=2)
        
        # Label แสดงรายละเอียด
        self.detail_label = ctk.CTkLabel(self, text="", font=("Arial", 10), text_color="#888888")
        self.detail_label.pack(pady=1)

    def update(self, progress, status_text="", detail_text=""):
        """อัปเดต Progress Bar พร้อมข้อความสถานะ"""
        self.progress_bar.set(progress)
        
        if status_text:
            self.progress_label.configure(text=status_text)
        
        if detail_text:
            self.detail_label.configure(text=detail_text)
        
        # อัปเดตสีตามความคืบหน้า
        if progress >= 1.0:
            self.progress_label.configure(text_color="#00AA00")  # สีเขียวเมื่อเสร็จสิ้น
        elif progress > 0:
            self.progress_label.configure(text_color="#FF6B35")  # สีส้มเมื่อกำลังทำงาน
        else:
            self.progress_label.configure(text_color="#333333")  # สีเทาเมื่อพร้อม

    def reset(self):
        """รีเซ็ต Progress Bar"""
        self.progress_bar.set(0)
        self.progress_label.configure(text="พร้อมใช้งาน", text_color="#333333")
        self.detail_label.configure(text="")
        
    def set_status(self, status_text, detail_text=""):
        """ตั้งค่าข้อความสถานะโดยไม่เปลี่ยนความคืบหน้า"""
        self.progress_label.configure(text=status_text)
        if detail_text:
            self.detail_label.configure(text=detail_text) 