"""Log Tab UI Component"""
import customtkinter as ctk
from tkinter import messagebox
from ui import theme


class LogTab:
    def __init__(self, parent):
        """
        Initialize Log Tab
        
        Args:
            parent: Parent widget
        """
        self.parent = parent
        
        # Create UI components
        self._create_ui()
    
    def _create_ui(self):
        """สร้างส่วนประกอบใน Log Tab"""
        # Toolbar
        toolbar = ctk.CTkFrame(self.parent)
        toolbar.pack(fill="x", padx=10, pady=(8, 0))

        copy_btn = ctk.CTkButton(toolbar, text="คัดลอก Log", command=self._copy_log_to_clipboard, width=120, font=theme.FONT_BUTTON)
        copy_btn.pack(side="left")

        clear_btn = ctk.CTkButton(toolbar, text="ล้าง Log", command=self._clear_log, width=120, font=theme.FONT_BUTTON)
        clear_btn.pack(side="left", padx=5)

        # กล่องข้อความสำหรับแสดง Log
        self.log_textbox = ctk.CTkTextbox(self.parent, font=theme.FONT_BODY)
        self.log_textbox.pack(pady=8, padx=10, fill="both", expand=True)
    
    def _copy_log_to_clipboard(self):
        """คัดลอกข้อความ log ทั้งหมดไปยัง clipboard"""
        log_text = self.log_textbox.get("1.0", "end").strip()
        # Get the root window to access clipboard
        root = self.parent.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(log_text)
        root.update()  # เพื่อให้ clipboard ทำงาน
        messagebox.showinfo("คัดลอกแล้ว", "คัดลอก Log เรียบร้อยแล้ว!")

    def _clear_log(self):
        """ล้างข้อความทั้งหมดใน log textbox"""
        self.log_textbox.delete("1.0", "end")
    
    def add_log(self, message):
        """เพิ่มข้อความลงใน log textbox"""
        self.log_textbox.insert("end", message)
        self.log_textbox.see("end")
