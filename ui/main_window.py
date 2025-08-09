"""
Main Window - รีแฟคเตอร์แล้ว
แยกส่วนประกอบ UI และ handlers ออกเป็นไฟล์แยก
"""
import os
import threading
import logging
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox

# Import UI components
from ui.tabs.main_tab import MainTab
from ui.tabs.log_tab import LogTab
from ui.tabs.settings_tab import SettingsTab

# Import handlers
from ui.handlers.file_handler import FileHandler
from ui.handlers.settings_handler import SettingsHandler

# Import services
from services.file_service import FileService
from services.database_service import DatabaseService
from services.file_management_service import FileManagementService
from config.database import DatabaseConfig
from constants import AppConstants, DatabaseConstants
from utils.logger import create_gui_log_handler


class MainWindow(ctk.CTkToplevel):
    def __init__(self, master=None, preloaded_data=None, ui_progress_callback=None, on_ready_callback=None):
        super().__init__(master)
        
        # ตั้งค่าหน้าต่างแอปพลิเคชัน
        self.title("ตรวจสอบและอัปโหลดไฟล์")
        self.geometry(f"{AppConstants.MAIN_WINDOW_SIZE[0]}x{AppConstants.MAIN_WINDOW_SIZE[1]}")
        self.resizable(False, False)
        
        # กำหนดประเภทข้อมูลที่รองรับ (SQL Server data types)
        self.supported_dtypes = DatabaseConstants.SUPPORTED_DTYPES
        
        # Initialize handlers
        self.settings_file = "config/column_settings.json"
        self.settings_handler = SettingsHandler(self.settings_file, self.log)
        
        # โหลดการตั้งค่า (ใช้ preloaded data ถ้ามี)
        if preloaded_data:
            self.column_settings = preloaded_data.get('column_settings', {})
            self.dtype_settings = preloaded_data.get('dtype_settings', {})
            # โหลด last_path จาก preloaded data
            preloaded_last_path = preloaded_data.get('last_path')
        else:
            # fallback: โหลดแบบปกติถ้าไม่มีข้อมูลล่วงหน้า
            self.column_settings = self.settings_handler.load_column_settings()
            self.dtype_settings = self.settings_handler.load_dtype_settings()
            preloaded_last_path = None
        
        # โหลดการตั้งค่า SQL Server
        self.db_config = DatabaseConfig()
        self.sql_config = self.db_config.config
        
        # ผูก logging เข้ากับ GUI
        self._attach_logging_to_gui()

        # สร้างบริการ
        self.file_service = FileService(log_callback=logging.info)
        self.db_service = DatabaseService()
        self.file_mgmt_service = FileManagementService()
        
        # Initialize file handler
        self.file_handler = FileHandler(
            self.file_service,
            self.db_service,
            self.file_mgmt_service,
            self.log
        )
        
        # โหลด path ล่าสุด ถ้ามี (ใช้ preloaded data ก่อน)
        last_path = preloaded_last_path if preloaded_last_path else self.settings_handler.load_last_path()
        if last_path and os.path.isdir(last_path):
            self.file_service.set_search_path(last_path)
        
        # สร้าง UI พร้อมแสดง progress
        if ui_progress_callback:
            ui_progress_callback("กำลังสร้าง Tab View...")
        
        self._create_ui(ui_progress_callback, on_ready_callback)
        
        # ตรวจสอบการเชื่อมต่อ SQL Server หลังสร้าง UI เสร็จ (ทำแบบ async เพื่อลดการค้าง)
        if ui_progress_callback:
            ui_progress_callback("ตรวจสอบการเชื่อมต่อ SQL Server...")
        self.after(100, self._run_check_sql_connection_async)
    
    def _create_ui(self, ui_progress_callback=None, on_ready_callback=None):
        """สร้างส่วนประกอบ UI ทั้งหมด"""
        if ui_progress_callback:
            ui_progress_callback("กำลังสร้าง Tab View...")
        
        # สร้าง Tab View
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        # สร้าง Tab
        main_tab_frame = self.tabview.add("Main")
        log_tab_frame = self.tabview.add("Log")
        settings_tab_frame = self.tabview.add("Settings")
        
        if ui_progress_callback:
            ui_progress_callback("กำลังสร้าง Main Tab...")
        
        # สร้างส่วนประกอบในแต่ละ Tab
        self._create_main_tab(main_tab_frame)
        
        if ui_progress_callback:
            ui_progress_callback("กำลังสร้าง Log Tab...")
            
        self._create_log_tab(log_tab_frame)
        
        if ui_progress_callback:
            ui_progress_callback("กำลังสร้าง Settings Tab...")
            
        # แบ่งการสร้าง Settings Tab ออกเป็นขั้นตอน
        self.after(10, lambda: self._create_settings_tab_async(settings_tab_frame, ui_progress_callback, on_ready_callback))
        
        # Settings Tab สร้างเสร็จแล้ว UI building ของประเภทไฟล์จะเริ่มแบบ async อัตโนมัติ
    
    
    def _create_main_tab(self, parent):
        """สร้างส่วนประกอบใน Main Tab"""
        # Create main tab with callbacks
        callbacks = {
            'toggle_select_all': self._toggle_select_all,
            'browse_excel_path': self._browse_excel_path,
            'run_check_thread': self._run_check_thread,
            'confirm_upload': self._confirm_upload,
            'start_auto_process': self._start_auto_process
        }
        
        self.main_tab_ui = MainTab(parent, callbacks)
        
        # เก็บ reference ไปยัง components สำคัญ
        self.status_bar = self.main_tab_ui.status_bar
        self.file_list = self.main_tab_ui.file_list
        self.progress_bar = self.main_tab_ui.progress_bar
        self.textbox = self.main_tab_ui.textbox
    
    def _create_log_tab(self, parent):
        """สร้างส่วนประกอบใน Log Tab"""
        self.log_tab_ui = LogTab(parent)
        
        # เก็บ reference ไปยัง log textbox
        self.log_textbox = self.log_tab_ui.log_textbox
    
    def _create_settings_tab_async(self, parent, ui_progress_callback=None, on_ready_callback=None):
        """สร้างส่วนประกอบใน Settings Tab แบบ async"""
        if ui_progress_callback:
            ui_progress_callback("กำลังเตรียม Settings Tab...")
            
        # Create settings tab with callbacks
        callbacks = {
            'save_column_settings': self._save_column_settings,
            'save_dtype_settings': self._save_dtype_settings
        }
        
        self.settings_tab_ui = SettingsTab(
            parent, 
            self.column_settings, 
            self.dtype_settings, 
            self.supported_dtypes, 
            callbacks,
            ui_progress_callback,
            on_all_ui_built=(lambda: self._on_all_ui_built(on_ready_callback)) if on_ready_callback else None
        )
        
        if ui_progress_callback:
            if self.column_settings:
                ui_progress_callback("Settings Tab เสร็จสิ้น")
            else:
                ui_progress_callback("ไม่มีประเภทไฟล์ — ข้ามการสร้าง Settings UI และพร้อมใช้งานทันที")

    def _on_all_ui_built(self, on_ready_callback):
        """ถูกเรียกเมื่อ SettingsTab สร้าง UI ทั้งหมดเสร็จ เพื่อแจ้งว่า MainWindow พร้อมใช้งาน"""
        try:
            if callable(on_ready_callback):
                on_ready_callback()
        except Exception:
            pass
    
    def _create_settings_tab(self, parent, ui_progress_callback=None):
        """สร้างส่วนประกอบใน Settings Tab (เดิม - สำหรับ fallback)"""
        # Create settings tab with callbacks
        callbacks = {
            'save_column_settings': self._save_column_settings,
            'save_dtype_settings': self._save_dtype_settings
        }
        
        self.settings_tab_ui = SettingsTab(
            parent, 
            self.column_settings, 
            self.dtype_settings, 
            self.supported_dtypes, 
            callbacks,
            ui_progress_callback
        )
    
    # ===== Callback Methods สำหรับ UI Components =====
    def _save_column_settings(self):
        """บันทึกการตั้งค่าคอลัมน์"""
        self.settings_handler.save_column_settings(self.column_settings)
    
    def _save_dtype_settings(self):
        """บันทึกการตั้งค่าประเภทข้อมูล"""
        self.settings_handler.save_dtype_settings(self.dtype_settings)
    
    def _toggle_select_all(self):
        """สลับการเลือกไฟล์ทั้งหมด"""
        self.main_tab_ui.toggle_select_all()
    
    def _browse_excel_path(self):
        """เลือกโฟลเดอร์"""
        self.file_handler.browse_excel_path(self.settings_handler.save_last_path)
    
    def _run_check_thread(self):
        """เริ่มการตรวจสอบไฟล์"""
        ui_callbacks = self._get_ui_callbacks()
        self.file_handler.run_check_thread(ui_callbacks)
    
    def _confirm_upload(self):
        """ยืนยันการอัปโหลด"""
        ui_callbacks = self._get_ui_callbacks()
        self.file_handler.confirm_upload(self.file_list.get_selected_files, ui_callbacks)
    
    def _start_auto_process(self):
        """เริ่มการประมวลผลอัตโนมัติ"""
        folder_path = self.file_handler.start_auto_process(
            self.settings_handler.load_last_path, 
            self.column_settings
        )
        
        if folder_path:
            ui_callbacks = self._get_ui_callbacks()
            thread = threading.Thread(
                target=self.file_handler.run_auto_process, 
                args=(folder_path, ui_callbacks), 
                daemon=True
            )
            thread.start()
    
    def _get_ui_callbacks(self):
        """สร้าง dictionary ของ UI callbacks"""
        return {
            'reset_progress': self.progress_bar.reset,
            'set_progress_status': self.progress_bar.set_status,
            'update_progress': self.progress_bar.update,
            'clear_file_list': self.file_list.clear,
            'add_file_to_list': self.file_list.add_file,
            'disable_auto_process': lambda: self.main_tab_ui.auto_process_button.configure(state="disabled"),
            'enable_auto_process': lambda: self.main_tab_ui.auto_process_button.configure(state="normal"),
            'reset_select_all': self.main_tab_ui.reset_select_all,
            'enable_select_all': self.main_tab_ui.enable_select_all,
            'update_status': self.status_bar.update_status,
            'disable_controls': self.main_tab_ui.disable_controls,
            'enable_controls': self.main_tab_ui.enable_controls,
            'disable_checkbox': self.file_list.disable_checkbox,
            'set_file_uploaded': self.file_list.set_file_uploaded
        }
    
    # ===== Logging Methods =====
    def log(self, message):
        """มาตรฐานการ log จากส่วนต่างๆ ของ GUI: ส่งเข้าระบบ logging"""
        try:
            logging.info(str(message))
        except Exception:
            # fallback: เขียนลง GUI ตรงๆ หาก logging ล้มเหลว
            self._append_log_message(str(message))

    def _append_log_message(self, formatted_message: str) -> None:
        """เพิ่มข้อความที่ถูก format แล้วลง GUI โดยตรง (ถูกเรียกจาก logging handler)"""
        if not formatted_message.endswith("\n"):
            formatted_message += "\n"
        self.after(0, self._update_textbox, formatted_message)
        self.after(0, self._update_log_textbox, formatted_message)
        
    def _update_textbox(self, message):
        """อัปเดตกล่องข้อความในแท็บหลัก"""
        if hasattr(self, 'textbox') and self.textbox:
            self.textbox.insert("end", message)
            self.textbox.see("end")
        
    def _update_log_textbox(self, message):
        """อัปเดตกล่องข้อความในแท็บ Log"""
        if hasattr(self, 'log_textbox') and self.log_textbox:
            self.log_textbox.insert("end", message)
            self.log_textbox.see("end")

    def _attach_logging_to_gui(self) -> None:
        """แนบ logging handler ให้ส่ง log ทั้งระบบเข้า GUI"""
        gui_handler = create_gui_log_handler(self._append_log_message, level=logging.INFO)
        root_logger = logging.getLogger()
        # ป้องกันซ้ำด้วยการตรวจสอบ class ของ handler
        if not any(h.__class__ is gui_handler.__class__ for h in root_logger.handlers):
            root_logger.addHandler(gui_handler)
    
    # ===== Database Connection =====
    def _run_check_sql_connection_async(self) -> None:
        """รันตรวจสอบการเชื่อมต่อ SQL แบบ background เพื่อลดการค้าง UI"""
        def worker():
            # ปิด popup warning ใน service ระหว่างเช็คแบบ background
            success, message = self.db_service.check_connection(show_warning=False)
            # ส่งผลลัพธ์กลับมาอัพเดท UI บน main thread
            self.after(0, self._on_sql_connection_checked, success, message)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_sql_connection_checked(self, success: bool, message: str) -> None:
        if success:
            self.log("✅ " + message)
        else:
            self.log("❌ " + message)
            messagebox.showerror(
                "ข้อผิดพลาด",
                f"ไม่สามารถเชื่อมต่อกับ SQL Server ได้:\n{message}\n\nกรุณาตรวจสอบการเชื่อมต่อและลองใหม่อีกครั้ง"
            )
            self.after(2000, self.destroy)
