"""Log Tab UI Component"""
import customtkinter as ctk
from tkinter import messagebox


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
        # กล่องข้อความสำหรับแสดง Log
        self.log_textbox = ctk.CTkTextbox(self.parent, width=850, height=600)
        self.log_textbox.pack(pady=10, padx=10, fill="both", expand=True)

        # ปุ่มคัดลอก Log
        copy_btn = ctk.CTkButton(
            self.parent,
            text="คัดลอก Log",
            command=self._copy_log_to_clipboard
        )
        copy_btn.pack(pady=(0, 0))
    
    def _copy_log_to_clipboard(self):
        """คัดลอกข้อความ log ทั้งหมดไปยัง clipboard"""
        log_text = self.log_textbox.get("1.0", "end").strip()
        # Get the root window to access clipboard
        root = self.parent.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(log_text)
        root.update()  # เพื่อให้ clipboard ทำงาน
        messagebox.showinfo("คัดลอกแล้ว", "คัดลอก Log เรียบร้อยแล้ว!")
    
    def add_log(self, message):
        """เพิ่มข้อความลงใน log textbox"""
        self.log_textbox.insert("end", message)
        self.log_textbox.see("end")
