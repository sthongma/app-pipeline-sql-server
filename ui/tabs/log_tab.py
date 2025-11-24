"""Log Tab UI Component"""
import customtkinter as ctk
from tkinter import messagebox, filedialog
import datetime
from config.json_manager import get_log_folder, set_log_folder


class LogTab:
    def __init__(self, parent, callbacks):
        """
        Initialize Log Tab

        Args:
            parent: Parent widget
            callbacks: Dictionary of callback functions
        """
        self.parent = parent
        self.callbacks = callbacks
        self.log_folder_path = None

        # Load saved log folder setting
        self._load_log_folder_setting()

        # Create UI components
        self._create_ui()
    
    def _create_ui(self):
        """Create components in Log Tab"""
        # Toolbar
        toolbar = ctk.CTkFrame(self.parent)
        toolbar.pack(fill="x", padx=10, pady=(8, 0))

        copy_btn = ctk.CTkButton(toolbar, text="Copy log", command=self._copy_log_to_clipboard, width=120)
        copy_btn.pack(side="left")

        # Keep references for double-click prevention
        self.export_btn = ctk.CTkButton(toolbar, text="Export log", command=self._export_log, width=120)
        self.export_btn.pack(side="left", padx=5)

        # Log folder setting button
        self.log_folder_btn = ctk.CTkButton(toolbar, text="Choose log folder", command=self.callbacks.get('choose_log_folder'), width=140)
        self.log_folder_btn.pack(side="left", padx=5)

        # กล่องข้อความสำหรับแสดง Log
        self.log_textbox = ctk.CTkTextbox(self.parent)
        self.log_textbox.pack(pady=8, padx=10, fill="both", expand=True)
    
    def _copy_log_to_clipboard(self):
        """Copy all log text to clipboard"""
        log_text = self.log_textbox.get("1.0", "end").strip()
        # Get the root window to access clipboard
        root = self.parent.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(log_text)
        root.update()  # เพื่อให้ clipboard ทำงาน
        messagebox.showinfo("Copied", "Log copied to clipboard")

    def _export_log(self):
        """Export log content to a file - with double-click protection"""
        # Check if any button is already disabled (using export_btn as indicator)
        if self.export_btn.cget('state') == 'disabled':
            return  # Already processing, ignore this click

        # Disable all controls immediately
        if 'disable_controls' in self.callbacks:
            self.callbacks['disable_controls']()

        try:
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
        finally:
            # Always re-enable all controls
            if 'enable_controls' in self.callbacks:
                self.callbacks['enable_controls']()
    
    def add_log(self, message):
        """เพิ่มข้อความลงใน log textbox"""
        self.log_textbox.insert("end", message)
        self.log_textbox.see("end")

    def _load_log_folder_setting(self):
        """Load saved log folder setting using JSONManager"""
        try:
            self.log_folder_path = get_log_folder()
        except Exception:
            self.log_folder_path = None

    def _save_log_folder_setting(self):
        """Save log folder setting using JSONManager"""
        try:
            success = set_log_folder(self.log_folder_path or "")
            if not success:
                messagebox.showerror("Error", "Failed to save log folder setting")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save log folder setting:\n{str(e)}")

    def get_log_folder_path(self):
        """Get current log folder path"""
        return self.log_folder_path
