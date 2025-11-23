"""Main Tab UI Component"""
import customtkinter as ctk
from tkinter import messagebox
from ui.components.file_list import FileList
from ui.components.progress_bar import ProgressBar
from ui.components.status_bar import StatusBar
from config.json_manager import get_output_folder, set_output_folder
from ui.icon_manager import get_icon


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
        self.output_folder_path = None

        # UI variables
        self.select_all_var = ctk.BooleanVar(value=False)

        # Load saved output folder setting
        self._load_output_folder_setting()

        # Create UI components
        self._create_ui()
    
    def _create_ui(self):
        """Create all UI components in Main Tab"""
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
        """Create control buttons and folder management buttons in the same row"""
        button_frame = ctk.CTkFrame(self.parent)
        button_frame.pack(pady=4)

        # ปุ่มเลือก/ยกเลิกการเลือกทั้งหมด
        self.select_all_button = ctk.CTkButton(
            button_frame,
            text="Select all",
            command=self.callbacks.get('toggle_select_all'),
            state="disabled",
            width=160,
        )
        self.select_all_button.pack(side="left", padx=4)

        # ปุ่มตรวจสอบไฟล์ในโฟลเดอร์
        self.check_btn = ctk.CTkButton(
            button_frame,
            text="Check Files",
            image=get_icon('search', size=18),
            compound="left",
            command=self.callbacks.get('run_check_thread'),
            width=160,
        )
        self.check_btn.pack(side="left", padx=4)

        # ปุ่มอัปโหลดไฟล์
        self.upload_button = ctk.CTkButton(
            button_frame,
            text="Upload Files",
            image=get_icon('upload', size=18),
            compound="left",
            command=self.callbacks.get('confirm_upload'),
            width=160,
        )
        self.upload_button.pack(side="left", padx=4)

        # ปุ่มเลือกโฟลเดอร์ input
        self.folder_btn = ctk.CTkButton(
            button_frame,
            text="Input Folder",
            image=get_icon('folder_input', size=18),
            compound="left",
            command=self.callbacks.get('browse_excel_path'),
            width=160,
        )
        self.folder_btn.pack(side="left", padx=4)

        # ปุ่มเลือกโฟลเดอร์ output
        self.output_folder_btn = ctk.CTkButton(
            button_frame,
            text="Output Folder",
            image=get_icon('folder', size=18),
            compound="left",
            command=self.callbacks.get('choose_output_folder'),
            width=170,
        )
        self.output_folder_btn.pack(side="left", padx=4)


    
    def enable_controls(self):
        """เปิดการใช้งานปุ่มทั้งหมด"""
        self.select_all_button.configure(state="normal")
        self.upload_button.configure(state="normal")
        self.folder_btn.configure(state="normal")
        self.check_btn.configure(state="normal")
        self.file_list.enable_all_checkboxes()
        
        # เปิด Settings tab ระหว่างไม่อัปโหลด
        if hasattr(self, 'parent_tabview'):
            self.parent_tabview.configure(state="normal")
    
    def disable_controls(self):
        """ปิดการใช้งานปุ่มทั้งหมด"""
        self.select_all_button.configure(state="disabled")
        self.upload_button.configure(state="disabled")
        self.folder_btn.configure(state="disabled")
        self.check_btn.configure(state="disabled")
        self.file_list.disable_all_checkboxes()

        # ปิด Settings tab ระหว่างอัปโหลด เพื่อป้องกันการเปลี่ยนแปลงการตั้งค่า
        if hasattr(self, 'parent_tabview'):
            try:
                # บังคับให้อยู่ที่ Main tab และปิดการเปลี่ยน tab
                current_tab = self.parent_tabview.get()
                if current_tab != "Main":
                    self.parent_tabview.set("Main")
                self.parent_tabview.configure(state="disabled")
            except Exception:
                # ถ้าเกิด error ให้ข้ามไป (widget อาจถูก destroy แล้ว)
                pass
    
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

    def _load_output_folder_setting(self):
        """Load saved output folder setting using JSONManager"""
        try:
            self.output_folder_path = get_output_folder()
        except Exception:
            self.output_folder_path = None

    def _save_output_folder_setting(self):
        """Save output folder setting using JSONManager"""
        try:
            success = set_output_folder(self.output_folder_path or "")
            if not success:
                messagebox.showerror("Error", "Failed to save output folder setting")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save output folder setting:\n{str(e)}")

    def get_output_folder_path(self):
        """Get current output folder path"""
        return self.output_folder_path
