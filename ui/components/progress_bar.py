import customtkinter as ctk
from ui import theme


class ProgressBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # ข้อความสถานะหลัก
        self.status_label = ctk.CTkLabel(self, text="สถานะ: -", anchor="w", font=theme.FONT_BODY)
        self.status_label.pack(fill="x", padx=8)

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, height=10)
        self.progress_bar.pack(pady=6, fill="x", padx=8)
        self.progress_bar.set(0)

        # ข้อความรายละเอียดใต้แถบความคืบหน้า
        self.detail_label = ctk.CTkLabel(self, text="", text_color="#7a7a7a", anchor="w", font=theme.FONT_SMALL)
        self.detail_label.pack(fill="x", padx=8)

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