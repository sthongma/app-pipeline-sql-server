"""Main Tab UI Component"""
import customtkinter as ctk
from ui.components.file_list import FileList
from ui.components.progress_bar import ProgressBar
from ui.components.status_bar import StatusBar


class MainTab:
    def __init__(self, parent, callbacks):
        """
        Initialize Main Tab
        
        Args:
            parent: Parent widget
            callbacks: Dictionary of callback functions
        """
        self.parent = parent
        self.callbacks = callbacks
        
        # UI variables
        self.select_all_var = ctk.BooleanVar(value=False)
        
        # Create UI components
        self._create_ui()
    
    def _create_ui(self):
        """สร้างส่วนประกอบ UI ทั้งหมดใน Main Tab"""
        # --- Status Bar ---
        self.status_bar = StatusBar(self.parent)
        self.status_bar.pack(pady=8)
        
        # --- Control Buttons (Import/Upload) ---
        self._create_control_buttons()
        
        # --- File List ---
        self.file_list = FileList(self.parent, width=860, height=360)
        self.file_list.pack(pady=8, padx=10)
        
        # --- Progress Bar ---
        self.progress_bar = ProgressBar(self.parent)
        self.progress_bar.pack(pady=5, fill="x", padx=10)
        
        # --- Log Textbox ---
        self.textbox = ctk.CTkTextbox(self.parent, height=200)
        self.textbox.pack(pady=10, padx=10, fill="x")
    
    def _create_control_buttons(self):
        """สร้างปุ่มควบคุมและปุ่มจัดการโฟลเดอร์ในแถวเดียวกัน"""
        button_frame = ctk.CTkFrame(self.parent)
        button_frame.pack(pady=4)
        
        # ปุ่มเลือก/ยกเลิกการเลือกทั้งหมด
        self.select_all_button = ctk.CTkButton(
            button_frame,
            text="Select all",
            command=self.callbacks.get('toggle_select_all'),
            state="disabled",
        )
        self.select_all_button.pack(side="left", padx=4)

        # ปุ่มเลือกโฟลเดอร์
        self.folder_btn = ctk.CTkButton(
            button_frame,
            text="📁 Choose folder",
            command=self.callbacks.get('browse_excel_path'),
        )
        self.folder_btn.pack(side="left", padx=4)

        # ปุ่มตรวจสอบไฟล์ในโฟลเดอร์
        self.check_btn = ctk.CTkButton(
            button_frame,
            text="🔍 Check files in folder",
            command=self.callbacks.get('run_check_thread'),
            width=160,
        )
        self.check_btn.pack(side="left", padx=4)

        # ปุ่มอัปโหลดไฟล์
        self.upload_button = ctk.CTkButton(
            button_frame,
            text="📤 Upload selected files",
            command=self.callbacks.get('confirm_upload'),
        )
        self.upload_button.pack(side="left", padx=4)

        # ปุ่มประมวลผลอัตโนมัติ
        self.auto_process_button = ctk.CTkButton(
            button_frame,
            text="🤖 Auto process",
            command=self.callbacks.get('start_auto_process'),
            width=160,
        )
        self.auto_process_button.pack(side="left", padx=4)
    
    def enable_controls(self):
        """เปิดการใช้งานปุ่มทั้งหมด"""
        self.select_all_button.configure(state="normal")
        self.upload_button.configure(state="normal")
        self.folder_btn.configure(state="normal")
        self.check_btn.configure(state="normal")
        self.auto_process_button.configure(state="normal")
        self.file_list.enable_all_checkboxes()
    
    def disable_controls(self):
        """ปิดการใช้งานปุ่มทั้งหมด"""
        self.select_all_button.configure(state="disabled")
        self.upload_button.configure(state="disabled")
        self.folder_btn.configure(state="disabled")
        self.check_btn.configure(state="disabled")
        self.auto_process_button.configure(state="disabled")
        self.file_list.disable_all_checkboxes()
    
    def toggle_select_all(self):
        """สลับระหว่างเลือกทั้งหมดและยกเลิกการเลือกทั้งหมด"""
        self.select_all_var.set(not self.select_all_var.get())
        if self.select_all_var.get():
            self.file_list.select_all()
            self.select_all_button.configure(text="Deselect all")
        else:
            self.file_list.deselect_all()
            self.select_all_button.configure(text="Select all")
    
    def reset_select_all(self):
        """รีเซ็ตปุ่มเลือกทั้งหมด"""
        self.select_all_button.configure(state="disabled")
        self.select_all_button.configure(text="Select all")
        self.select_all_var.set(False)
    
    def enable_select_all(self):
        """เปิดการใช้งานปุ่มเลือกทั้งหมดและเลือกทั้งหมดอัตโนมัติ"""
        self.select_all_button.configure(state="normal")
        self.select_all_var.set(True)
        self.file_list.select_all()
        self.select_all_button.configure(text="Deselect all")
