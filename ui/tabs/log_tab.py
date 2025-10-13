"""Log Tab UI Component"""
import customtkinter as ctk
from tkinter import messagebox
import datetime
import os
import json


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

        export_btn = ctk.CTkButton(toolbar, text="Export log", command=self._export_log, width=120)
        export_btn.pack(side="left", padx=5)

        # Log folder setting button
        log_folder_btn = ctk.CTkButton(toolbar, text="Choose log folder", command=self.callbacks.get('choose_log_folder'), width=140)
        log_folder_btn.pack(side="left", padx=5)

        # กล่องข้อความสำหรับแสดง Log
        self.log_textbox = ctk.CTkTextbox(self.parent)
        self.log_textbox.pack(pady=8, padx=10, fill="both", expand=True)

        # กำหนดสีสำหรับ log ต่างๆ (terminal-like colors)
        self._setup_log_colors()
    
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
    
    def _get_emoji_color_map(self):
        """แมป emoji กับสี (shared with main_window.py)"""
        return {
            '✅': 'emoji_success',
            '❌': 'emoji_error',
            '⚠️': 'emoji_warning',
            '📊': 'emoji_info',
            '📁': 'emoji_info',
            'ℹ️': 'emoji_info',
            '🔍': 'emoji_search',
            '🎉': 'emoji_highlight',
            '📋': 'emoji_phase',
            '⏳': 'emoji_phase',
            '📦': 'emoji_file',
            '📤': 'emoji_file',
            '⏱️': 'emoji_time',
            '🔄': 'emoji_phase',
            '🚀': 'emoji_highlight',
            '💾': 'emoji_info',
            '🧹': 'emoji_search',
            '🏷️': 'emoji_phase',
        }

    def _setup_log_colors(self):
        """กำหนดสีสำหรับ emoji/icon เท่านั้น"""
        text_widget = self.log_textbox._textbox

        # กำหนด tags สำหรับสีต่างๆ (เฉพาะ emoji)
        text_widget.tag_config("emoji_success", foreground="#00FF00")    # เขียว
        text_widget.tag_config("emoji_error", foreground="#FF4444")      # แดง
        text_widget.tag_config("emoji_warning", foreground="#FFA500")    # ส้ม
        text_widget.tag_config("emoji_info", foreground="#00BFFF")       # ฟ้า
        text_widget.tag_config("emoji_search", foreground="#888888")     # เทา
        text_widget.tag_config("emoji_highlight", foreground="#FFD700")  # ทอง
        text_widget.tag_config("emoji_phase", foreground="#FF69B4")      # ชมพู
        text_widget.tag_config("emoji_file", foreground="#00CED1")       # ฟ้าเข้ม
        text_widget.tag_config("emoji_time", foreground="#9370DB")       # ม่วง

    def add_log(self, message):
        """เพิ่มข้อความลงใน log textbox โดยให้เฉพาะ emoji มีสี"""
        text_widget = self.log_textbox._textbox
        emoji_colors = self._get_emoji_color_map()

        # แยกข้อความและระบุสีเฉพาะ emoji
        for char in message:
            if char in emoji_colors:
                text_widget.insert("end", char, emoji_colors[char])
            else:
                text_widget.insert("end", char)

        # เลื่อนไปท้ายสุด
        self.log_textbox.see("end")

    def _load_log_folder_setting(self):
        """Load saved log folder setting from config file"""
        config_file = os.path.join("config", "log_folder_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.log_folder_path = config.get('log_folder_path')
            except Exception:
                self.log_folder_path = None

    def _save_log_folder_setting(self):
        """Save log folder setting to config file"""
        config_file = os.path.join("config", "log_folder_config.json")
        try:
            # Ensure config directory exists
            os.makedirs("config", exist_ok=True)
            config = {'log_folder_path': self.log_folder_path}
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save log folder setting:\n{str(e)}")

    def get_log_folder_path(self):
        """Get current log folder path"""
        return self.log_folder_path
