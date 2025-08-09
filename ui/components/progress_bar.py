import customtkinter as ctk


class ProgressBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # ข้อความสถานะหลัก
        self.status_label = ctk.CTkLabel(self, text="สถานะ: -", anchor="w")
        self.status_label.pack(fill="x", padx=5)

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, width=850, height=10)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)

        # ข้อความรายละเอียดใต้แถบความคืบหน้า
        self.detail_label = ctk.CTkLabel(self, text="", text_color="#888888", anchor="w")
        self.detail_label.pack(fill="x", padx=5)

    def update(self, progress, status_text="", detail_text=""):
        """อัปเดต Progress Bar และข้อความสถานะ"""
        try:
            if 0.0 <= float(progress) <= 1.0:
                self.progress_bar.set(progress)
        except Exception:
            # หากส่งค่าไม่ถูกต้อง ให้ข้ามการตั้งค่า progress
            pass
        if status_text:
            self.status_label.configure(text=f"สถานะ: {status_text}")
        if detail_text is not None:
            self.detail_label.configure(text=detail_text)

    def reset(self):
        """รีเซ็ต Progress Bar และข้อความ"""
        self.progress_bar.set(0)
        self.status_label.configure(text="สถานะ: -")
        self.detail_label.configure(text="")

    def set_status(self, status_text, detail_text=""):
        """ตั้งค่าเฉพาะข้อความสถานะและรายละเอียด"""
        self.status_label.configure(text=f"สถานะ: {status_text}")
        self.detail_label.configure(text=detail_text or "")