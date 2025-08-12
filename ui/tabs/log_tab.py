"""Log Tab UI Component"""
import customtkinter as ctk
from tkinter import messagebox, filedialog
import datetime


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

        copy_btn = ctk.CTkButton(toolbar, text="Copy log", command=self._copy_log_to_clipboard, width=120)
        copy_btn.pack(side="left")

        export_btn = ctk.CTkButton(toolbar, text="Export log", command=self._export_log, width=120)
        export_btn.pack(side="left", padx=5)

        # กล่องข้อความสำหรับแสดง Log
        self.log_textbox = ctk.CTkTextbox(self.parent)
        self.log_textbox.pack(pady=8, padx=10, fill="both", expand=True)
    
    def _copy_log_to_clipboard(self):
        """คัดลอกข้อความ log ทั้งหมดไปยัง clipboard"""
        log_text = self.log_textbox.get("1.0", "end").strip()
        # Get the root window to access clipboard
        root = self.parent.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(log_text)
        root.update()  # เพื่อให้ clipboard ทำงาน
        messagebox.showinfo("Copied", "Log copied to clipboard")

    def _export_log(self):
        """Export log content to a file"""
        log_text = self.log_textbox.get("1.0", "end").strip()
        
        if not log_text:
            messagebox.showwarning("Warning", "No log content to export")
            return
        
        # Generate default filename with current datetime
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"log_export_{current_time}.txt"
        
        # Open file dialog to save the log
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=default_filename,
            filetypes=[
                ("Text files", "*.txt"),
                ("Log files", "*.log"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_text)
                messagebox.showinfo("Success", f"Log exported successfully to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export log:\n{str(e)}")
    
    def add_log(self, message):
        """เพิ่มข้อความลงใน log textbox"""
        self.log_textbox.insert("end", message)
        self.log_textbox.see("end")
