"""
Main Window - Refactored
Separated UI components and handlers into separate files
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
from services.orchestrators.file_orchestrator import FileOrchestrator
from services.orchestrators.database_orchestrator import DatabaseOrchestrator
from services.file import FileManagementService
from config.database import DatabaseConfig
from constants import AppConstants, DatabaseConstants
from utils.logger import create_gui_log_handler, setup_file_logging


class MainWindow(ctk.CTkToplevel):
    def __init__(self, master=None, preloaded_data=None, ui_progress_callback=None, on_ready_callback=None):
        super().__init__(master)
        
        # ตั้งค่าหน้าต่างแอปพลิเคชัน
        self.title("PIPELINE SQL SERVER")
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
        
        # Log environment variables status for debugging
        self._log_environment_status()

        # สร้างบริการ
        self.file_service = FileOrchestrator(log_callback=logging.info)
        self.db_service = DatabaseOrchestrator()
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
            ui_progress_callback("Building Tab View...")
        
        self._create_ui(ui_progress_callback, on_ready_callback)
        

        # โหลดและเริ่มการบันทึก log ไฟล์ถ้ามีการตั้งค่าไว้
        self.after(50, self._initialize_log_file_if_needed)

        # โหลด output folder ถ้ามีการตั้งค่าไว้
        self.after(60, self._initialize_output_folder_if_needed)

        # ตรวจสอบการเชื่อมต่อ SQL Server หลังสร้าง UI เสร็จ (ทำแบบ async เพื่อลดการค้าง)
        if ui_progress_callback:
            ui_progress_callback("Checking SQL Server connection...")
        self.after(100, self._run_check_sql_connection_async)
    
    def _create_ui(self, ui_progress_callback=None, on_ready_callback=None):
        """Create all UI components"""
        if ui_progress_callback:
            ui_progress_callback("Building Tab View...")
        
        # สร้าง Tab View
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=8, pady=8)
        
        # สร้าง Tab
        main_tab_frame = self.tabview.add("Main")
        log_tab_frame = self.tabview.add("Logs")
        settings_tab_frame = self.tabview.add("Settings")
        
        if ui_progress_callback:
            ui_progress_callback("Building Main Tab...")
        
        # สร้างส่วนประกอบในแต่ละ Tab
        self._create_main_tab(main_tab_frame)
        
        if ui_progress_callback:
            ui_progress_callback("Building Log Tab...")
            
        self._create_log_tab(log_tab_frame)
        
        if ui_progress_callback:
            ui_progress_callback("Building Settings Tab...")
            
        # แบ่งการสร้าง Settings Tab ออกเป็นขั้นตอน
        self.after(10, lambda: self._create_settings_tab_async(settings_tab_frame, ui_progress_callback, on_ready_callback))
        
        # Settings Tab สร้างเสร็จแล้ว UI building ของประเภทไฟล์จะเริ่มแบบ async อัตโนมัติ
    
    
    def _create_main_tab(self, parent):
        """Create components in Main Tab"""
        # Create main tab with callbacks
        callbacks = {
            'toggle_select_all': self._toggle_select_all,
            'browse_excel_path': self._browse_excel_path,
            'run_check_thread': self._run_check_thread,
            'confirm_upload': self._confirm_upload
        }

        self.main_tab_ui = MainTab(parent, callbacks, output_folder_callback=self._on_output_folder_changed)

        # ส่ง reference ของ tabview เพื่อให้ควบคุม tabs ได้
        self.main_tab_ui.parent_tabview = self.tabview

        # เก็บ reference ไปยัง components สำคัญ
        self.status_bar = self.main_tab_ui.status_bar
        self.file_list = self.main_tab_ui.file_list
        self.progress_bar = self.main_tab_ui.progress_bar
        self.textbox = self.main_tab_ui.textbox
    
    def _create_log_tab(self, parent):
        """Create components in Log Tab"""
        self.log_tab_ui = LogTab(parent, log_folder_callback=self._on_log_folder_changed)

        # เก็บ reference ไปยัง log textbox
        self.log_textbox = self.log_tab_ui.log_textbox
    
    def _create_settings_tab_async(self, parent, ui_progress_callback=None, on_ready_callback=None):
        """Create components in Settings Tab asynchronously"""
        if ui_progress_callback:
            ui_progress_callback("Preparing Settings Tab...")
            
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
                ui_progress_callback("Settings Tab completed")
            else:
                ui_progress_callback("No file types — skipping Settings UI; ready immediately")

    def _on_all_ui_built(self, on_ready_callback):
        """Called when SettingsTab finishes building all UI to indicate MainWindow is ready for use"""
        try:
            if callable(on_ready_callback):
                on_ready_callback()
        except Exception:
            pass
    
    def _create_settings_tab(self, parent, ui_progress_callback=None):
        """Create components in Settings Tab (legacy - for fallback)"""
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
        """Save column settings"""
        self.settings_handler.save_column_settings(self.column_settings)
        # รีโหลดการตั้งค่าใน services ทั้งหมด
        self._reload_settings_in_services()
    
    def _save_dtype_settings(self):
        """Save data type settings"""
        self.settings_handler.save_dtype_settings(self.dtype_settings)
        # รีโหลดการตั้งค่าใน services ทั้งหมด
        self._reload_settings_in_services()
    
    def _toggle_select_all(self):
        """Toggle select all files"""
        self.main_tab_ui.toggle_select_all()
    
    def _browse_excel_path(self):
        """Select folder"""
        self.file_handler.browse_excel_path(self.settings_handler.save_last_path)
    
    def _run_check_thread(self):
        """Start file checking"""
        ui_callbacks = self._get_ui_callbacks()
        self.file_handler.run_check_thread(ui_callbacks)
    
    def _confirm_upload(self):
        """Confirm upload"""
        ui_callbacks = self._get_ui_callbacks()
        self.file_handler.confirm_upload(self.file_list.get_selected_files, ui_callbacks)
    

    
    def _reload_settings_in_services(self):
        """Reload settings in all services"""
        try:
            # รีโหลดการตั้งค่าใน file_service
            if hasattr(self.file_service, '_settings_loaded'):
                self.file_service._settings_loaded = False
                self.file_service._load_settings()
                
            # รีโหลดการตั้งค่าใน file_handler (ซึ่งใช้ services ต่างๆ)
            if hasattr(self.file_handler, 'data_processor'):
                if hasattr(self.file_handler.data_processor, '_settings_loaded'):
                    self.file_handler.data_processor._settings_loaded = False
                    self.file_handler.data_processor._load_settings()
                    
            if hasattr(self.file_handler, 'file_reader'):
                if hasattr(self.file_handler.file_reader, '_settings_loaded'):
                    self.file_handler.file_reader._settings_loaded = False
                    self.file_handler.file_reader._load_settings()
                    
            self.log("Settings reloaded in all services")
        except Exception as e:
            self.log(f"Error reloading settings: {e}")
    
    def _get_ui_callbacks(self):
        """Create dictionary of UI callbacks"""
        return {
            'reset_progress': self.progress_bar.reset,
            'set_progress_status': self.progress_bar.set_status,
            'update_progress': self.progress_bar.update,
            'clear_file_list': self.file_list.clear,
            'add_file_to_list': self.file_list.add_file,
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
        """Standard logging from various GUI components: send to logging system"""
        try:
            logging.info(str(message))
        except Exception:
            # fallback: เขียนลง GUI ตรงๆ หาก logging ล้มเหลว
            self._append_log_message(str(message))

    def _append_log_message(self, formatted_message: str) -> None:
        """Add formatted message directly to GUI (called from logging handler)"""
        if not formatted_message.endswith("\n"):
            formatted_message += "\n"
        self.after(0, self._update_textbox, formatted_message)
        self.after(0, self._update_log_textbox, formatted_message)
        
    def _insert_colored_message(self, text_widget, message, emoji_colors):
        """ฟังก์ชันกลางสำหรับแทรกข้อความพร้อมสี emoji (DRY principle)"""
        for char in message:
            if char in emoji_colors:
                text_widget.insert("end", char, emoji_colors[char])
            else:
                text_widget.insert("end", char)

    def _setup_emoji_colors(self, text_widget):
        """กำหนดสีสำหรับ emoji (ใช้ร่วมกันได้ทั้ง Main และ Log tab)"""
        text_widget.tag_config("emoji_success", foreground="#00FF00")    # เขียว
        text_widget.tag_config("emoji_error", foreground="#FF4444")      # แดง
        text_widget.tag_config("emoji_warning", foreground="#FFA500")    # ส้ม
        text_widget.tag_config("emoji_info", foreground="#00BFFF")       # ฟ้า
        text_widget.tag_config("emoji_search", foreground="#888888")     # เทา
        text_widget.tag_config("emoji_highlight", foreground="#FFD700")  # ทอง
        text_widget.tag_config("emoji_phase", foreground="#FF69B4")      # ชมพู
        text_widget.tag_config("emoji_file", foreground="#00CED1")       # ฟ้าเข้ม
        text_widget.tag_config("emoji_time", foreground="#9370DB")       # ม่วง

    def _get_emoji_color_map(self):
        """แมป emoji กับสี (ใช้ร่วมกันได้)"""
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

    def _update_textbox(self, message):
        """Update textbox in main tab with colored emoji"""
        if hasattr(self, 'textbox') and self.textbox:
            text_widget = self.textbox._textbox

            # Setup colors ครั้งแรก
            if not hasattr(self, '_emoji_colors_setup_main'):
                self._setup_emoji_colors(text_widget)
                self._emoji_colors_setup_main = True

            # แทรกข้อความพร้อมสี
            self._insert_colored_message(text_widget, message, self._get_emoji_color_map())
            self.textbox.see("end")
        
    def _update_log_textbox(self, message):
        """Update textbox in Log tab"""
        if hasattr(self, 'log_tab_ui') and self.log_tab_ui:
            # ใช้ add_log() ของ LogTab เพื่อให้มีสี
            self.log_tab_ui.add_log(message)
        elif hasattr(self, 'log_textbox') and self.log_textbox:
            # Fallback: ถ้ายังไม่มี log_tab_ui
            self.log_textbox.insert("end", message)
            self.log_textbox.see("end")


    def _attach_logging_to_gui(self) -> None:
        """Attach logging handler to send system logs to GUI"""
        # Check if structured logging is enabled via environment variable
        structured_logging = os.getenv('STRUCTURED_LOGGING', 'false').lower() == 'true'

        gui_handler = create_gui_log_handler(
            self._append_log_message,
            level=logging.INFO,
            structured=structured_logging
        )
        root_logger = logging.getLogger()
        # ป้องกันซ้ำด้วยการตรวจสอบ class ของ handler
        if not any(h.__class__ is gui_handler.__class__ for h in root_logger.handlers):
            root_logger.addHandler(gui_handler)

        # Store reference to file handler for later updates
        self.current_file_handler = None
    
    def _log_environment_status(self) -> None:
        """Log current environment variables status for debugging"""
        env_vars = ['DB_SERVER', 'DB_NAME', 'DB_USERNAME', 'DB_PASSWORD', 'STRUCTURED_LOGGING']
        logging.info("🔧 Environment Variables Status:")
        
        for var in env_vars:
            value = os.getenv(var)
            if value:
                # Don't log sensitive values, just indicate they're set
                if 'PASSWORD' in var or 'USERNAME' in var:
                    logging.info(f"  {var}: *** (set)")
                else:
                    logging.info(f"  {var}: {value}")
            else:
                logging.info(f"  {var}: (not set)")
    
    # ===== Database Connection =====
    def _run_check_sql_connection_async(self) -> None:
        """Run SQL connection check in background to reduce UI freezing"""
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
                "Error",
                f"Unable to connect to SQL Server:\n{message}\n\nPlease check your connection and try again"
            )
            self.after(2000, self.destroy)

    def _initialize_log_file_if_needed(self) -> None:
        """Initialize log file if user has previously set log folder"""
        try:
            if hasattr(self, 'log_tab_ui') and self.log_tab_ui:
                log_folder_path = self.log_tab_ui.get_log_folder_path()
                if log_folder_path and os.path.exists(log_folder_path):
                    self._on_log_folder_changed(log_folder_path)
        except Exception:
            pass

    def _on_log_folder_changed(self, log_folder_path: str) -> None:
        """Called when user changes log folder setting"""
        try:
            # Remove old file handler if exists
            if self.current_file_handler:
                root_logger = logging.getLogger()
                root_logger.removeHandler(self.current_file_handler)
                self.current_file_handler.close()
                self.current_file_handler = None

            # Setup new file logging with the selected folder
            if log_folder_path and os.path.exists(log_folder_path):
                log_file_path = setup_file_logging(log_folder_path, enable_export=True)
                if log_file_path:
                    # Store reference to the new file handler
                    root_logger = logging.getLogger()
                    for handler in root_logger.handlers:
                        if isinstance(handler, logging.FileHandler):
                            self.current_file_handler = handler
                            break

                    self.log(f"📁 Log file will be saved to: {log_file_path}")
                else:
                    self.log("⚠️ Failed to setup log file")
        except Exception as e:
            self.log(f"❌ Error setting up log file: {e}")

    def _initialize_output_folder_if_needed(self) -> None:
        """Initialize output folder if user has previously set it"""
        try:
            if hasattr(self, 'main_tab_ui') and self.main_tab_ui:
                output_folder_path = self.main_tab_ui.get_output_folder_path()
                if output_folder_path and os.path.exists(output_folder_path):
                    self._on_output_folder_changed(output_folder_path)
        except Exception:
            pass

    def _on_output_folder_changed(self, output_folder_path: str) -> None:
        """Called when user changes output folder setting"""
        try:
            if output_folder_path and os.path.exists(output_folder_path):
                # Update file management service to use new output folder
                if hasattr(self, 'file_mgmt_service'):
                    self.file_mgmt_service.set_output_folder(output_folder_path)
                self.log(f"📂 Output folder updated: {output_folder_path}")
        except Exception as e:
            self.log(f"❌ Error updating output folder: {e}")
