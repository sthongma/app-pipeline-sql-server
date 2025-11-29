"""Custom Input Dialog with app icon support"""
import customtkinter as ctk
from utils.ui_helpers import get_app_icon_path


class InputDialog(ctk.CTkToplevel):
    """Custom input dialog that supports app icon"""
    
    def __init__(
        self,
        parent=None,
        title: str = "Input",
        text: str = "Enter value:",
        placeholder: str = ""
    ):
        super().__init__(parent)
        
        self._result = None
        self._icon_path = get_app_icon_path()
        
        # ตั้งค่าหน้าต่าง
        self.title(title)
        self.geometry("300x170")
        self.resizable(False, False)
        self.grab_set()
        
        # จัดกึ่งกลาง
        self._center_window()
        
        # สร้าง UI
        self._create_ui(text, placeholder)
        
        # ตั้งค่า icon หลังสร้าง UI เสร็จ
        if self._icon_path:
            self.after(200, self._set_icon)
        
        # Focus ที่ entry
        self.entry.focus_set()
        
        # Bind Enter key
        self.entry.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self._on_cancel())
    
    def _set_icon(self):
        """ตั้งค่า icon"""
        try:
            self.iconbitmap(self._icon_path)
        except Exception:
            pass
        
    def _center_window(self):
        """จัดหน้าต่างให้อยู่กึ่งกลางหน้าจอ"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
    def _create_ui(self, text: str, placeholder: str):
        """สร้าง UI"""
        # Label
        label = ctk.CTkLabel(self, text=text)
        label.pack(pady=(20, 10), padx=20)
        
        # Entry
        self.entry = ctk.CTkEntry(self, width=250, placeholder_text=placeholder)
        self.entry.pack(pady=10, padx=20)
        
        # Button frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(10, 20))
        
        ok_btn = ctk.CTkButton(btn_frame, text="Ok", width=80, command=self._on_ok)
        ok_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", width=80, command=self._on_cancel)
        cancel_btn.pack(side="left", padx=5)
        
    def _on_ok(self):
        """เมื่อกด OK"""
        self._result = self.entry.get()
        self.destroy()
        
    def _on_cancel(self):
        """เมื่อกด Cancel"""
        self._result = None
        self.destroy()
        
    def get_input(self) -> str | None:
        """รอผลลัพธ์และคืนค่า"""
        self.wait_window()
        return self._result
