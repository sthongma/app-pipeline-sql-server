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
from utils.ui_helpers import get_emoji_color_map, setup_emoji_colors, insert_colored_message
from ui.ui_callbacks import UICallbacks
from typing import Optional, Dict, Any, Callable


class MainWindow(ctk.CTkToplevel):
    def __init__(
        self,
        master: Optional[ctk.CTk] = None,
        preloaded_data: Optional[Dict[str, Any]] = None,
        ui_progress_callback: Optional[Callable[[str], None]] = None,
        on_ready_callback: Optional[Callable[[], None]] = None
    ) -> None:
        super().__init__(master)

        # ตั้งค่าหน้าต่างแอปพลิเคชัน
        self.title("PIPELINE SQL SERVER")
        self.geometry(f"{AppConstants.MAIN_WINDOW_SIZE[0]}x{AppConstants.MAIN_WINDOW_SIZE[1]}")
        self.resizable(False, False)

        # กำหนดประเภทข้อมูลที่รองรับ (SQL Server data types)
        self.supported_dtypes = DatabaseConstants.SUPPORTED_DTYPES

        # เก็บ callback สำหรับรายงานความคืบหน้า
        self._ui_progress_callback = ui_progress_callback
        self._on_ready_callback = on_ready_callback

        # Initialize handlers
        self.settings_file = "config/column_settings.json"
        self.settings_handler = SettingsHandler(self.settings_file, self.log)

        # โหลดการตั้งค่า (ใช้ preloaded data ถ้ามี)
        if preloaded_data:
            self.column_settings = preloaded_data.get('column_settings', {})
            self.dtype_settings = preloaded_data.get('dtype_settings', {})
            # โหลด input_folder_path จาก preloaded data
            preloaded_input_folder = preloaded_data.get('input_folder_path')
        else:
            # fallback: โหลดแบบปกติถ้าไม่มีข้อมูลล่วงหน้า
            self.column_settings = self.settings_handler.load_column_settings()
            self.dtype_settings = self.settings_handler.load_dtype_settings()
            preloaded_input_folder = None

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

        # โหลด input folder ถ้ามี (ใช้ preloaded data ก่อน)
        input_folder_path = preloaded_input_folder if preloaded_input_folder else self.settings_handler.load_input_folder()
        if input_folder_path and os.path.isdir(input_folder_path):
            self.file_service.set_search_path(input_folder_path)

        # เก็บ input_folder_path ไว้ใช้ใน initialization ภายหลัง
        self._input_folder_path = input_folder_path

        # สร้าง UI พร้อมแสดง progress
        if ui_progress_callback:
            ui_progress_callback("Building Tab View...")

        self._create_ui(ui_progress_callback, on_ready_callback)
    
    def _create_ui(self, ui_progress_callback=None, on_ready_callback=None):
        """Create all UI components"""
        if ui_progress_callback:
            ui_progress_callback("Building Tab View...")
        
        # สร้าง Tab View พร้อมกำหนดความกว้างขั้นต่ำของปุ่ม tab
        self.tabview = ctk.CTkTabview(self, segmented_button_fg_color=None, segmented_button_unselected_color=None)
        self.tabview.pack(fill="both", expand=True, padx=8, pady=8)

        # กำหนดความกว้างและความสูงขั้นต่ำให้ปุ่ม tab ไม่ยุบเมื่อ disable
        # ใช้ grid_propagate(False) เพื่อป้องกันการ resize อัตโนมัติ
        self.tabview._segmented_button.configure(width=150, height=20)
        self.tabview._segmented_button.grid_propagate(False)
        
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
            'confirm_upload': self._confirm_upload,
            'choose_output_folder': self._choose_output_folder
        }

        self.main_tab_ui = MainTab(parent, callbacks)

        # ส่ง reference ของ tabview เพื่อให้ควบคุม tabs ได้
        self.main_tab_ui.parent_tabview = self.tabview

        # เก็บ reference ไปยัง components สำคัญ
        self.status_bar = self.main_tab_ui.status_bar
        self.file_list = self.main_tab_ui.file_list
        self.progress_bar = self.main_tab_ui.progress_bar
        self.textbox = self.main_tab_ui.textbox
    
    def _create_log_tab(self, parent):
        """Create components in Log Tab"""
        # Create log tab with callbacks
        callbacks = {
            'choose_log_folder': self._choose_log_folder,
            'disable_controls': lambda: self.main_tab_ui.disable_controls(),
            'enable_controls': lambda: self.main_tab_ui.enable_controls()
        }

        self.log_tab_ui = LogTab(parent, callbacks)

        # เก็บ reference ไปยัง log textbox
        self.log_textbox = self.log_tab_ui.log_textbox
    
    def _create_settings_tab_async(self, parent, ui_progress_callback=None, on_ready_callback=None):
        """Create components in Settings Tab asynchronously"""
        if ui_progress_callback:
            ui_progress_callback("Preparing Settings Tab...")
            
        # Create settings tab with callbacks
        callbacks = {
            'save_column_settings': self._save_column_settings,
            'save_dtype_settings': self._save_dtype_settings,
            'delete_file_type': self._delete_file_type
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
            'save_dtype_settings': self._save_dtype_settings,
            'delete_file_type': self._delete_file_type
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

    def _delete_file_type(self, file_type):
        """Delete file type configuration"""
        from services.settings_manager import settings_manager
        settings_manager.delete_file_type(file_type)
        # รีโหลดการตั้งค่าใน services ทั้งหมด
        self._reload_settings_in_services()

    def _toggle_select_all(self):
        """Toggle select all files"""
        self.main_tab_ui.toggle_select_all()
    
    def _browse_excel_path(self):
        """Select folder - with double-click protection"""
        # Check if any button is already disabled (using folder_btn as indicator)
        if self.main_tab_ui.folder_btn.cget('state') == 'disabled':
            return  # Already processing, ignore this click

        # Disable all controls immediately
        self.main_tab_ui.disable_controls()

        try:
            self.file_handler.browse_excel_path(self.settings_handler.save_input_folder)
        finally:
            # Always re-enable all controls
            self.main_tab_ui.enable_controls()
    
    def _run_check_thread(self):
        """Start file checking"""
        ui_callbacks = self._get_ui_callbacks()
        self.file_handler.run_check_thread(ui_callbacks)
    
    def _confirm_upload(self):
        """Confirm upload"""
        ui_callbacks = self._get_ui_callbacks()
        self.file_handler.confirm_upload(self.file_list.get_selected_files, ui_callbacks)

    def _choose_output_folder(self):
        """Choose output folder - with double-click protection"""
        from tkinter import filedialog

        # Check if any button is already disabled (using output_folder_btn as indicator)
        if self.main_tab_ui.output_folder_btn.cget('state') == 'disabled':
            return  # Already processing, ignore this click

        # Disable all controls immediately
        self.main_tab_ui.disable_controls()

        try:
            # Get current output folder path from MainTab
            current_path = self.main_tab_ui.get_output_folder_path()

            folder_path = filedialog.askdirectory(
                title="Select output folder for uploaded files",
                initialdir=current_path if current_path else os.getcwd()
            )

            if folder_path:
                # Save to MainTab
                self.main_tab_ui.output_folder_path = folder_path
                self.main_tab_ui._save_output_folder_setting()

                # Call the existing handler
                self._on_output_folder_changed(folder_path)

                messagebox.showinfo("Success", f"Output folder set to:\n{folder_path}\n\nUploaded files will be moved to this location.")
        finally:
            # Always re-enable all controls
            self.main_tab_ui.enable_controls()

    def _choose_log_folder(self):
        """Choose log folder - with double-click protection"""
        from tkinter import filedialog

        # Check if any button is already disabled (using log_folder_btn as indicator)
        if self.log_tab_ui.log_folder_btn.cget('state') == 'disabled':
            return  # Already processing, ignore this click

        # Disable all controls immediately
        self.main_tab_ui.disable_controls()

        try:
            # Get current log folder path from LogTab
            current_path = self.log_tab_ui.get_log_folder_path()

            folder_path = filedialog.askdirectory(
                title="Select log folder",
                initialdir=current_path if current_path else os.getcwd()
            )

            if folder_path:
                # Save to LogTab
                self.log_tab_ui.log_folder_path = folder_path
                self.log_tab_ui._save_log_folder_setting()

                # Call the existing handler
                self._on_log_folder_changed(folder_path)

                messagebox.showinfo("Success", f"Log folder set to:\n{folder_path}")
        finally:
            # Always re-enable all controls
            self.main_tab_ui.enable_controls()

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
    
    def _get_ui_callbacks(self) -> Dict[str, Callable]:
        """
        Create UI callbacks (returns both dict and dataclass for backward compatibility)

        Returns:
            Dict with UI callback functions (backward compatible)
        """
        callbacks = UICallbacks(
            reset_progress=self.progress_bar.reset,
            set_progress_status=self.progress_bar.set_status,
            update_progress=self.progress_bar.update,
            clear_file_list=self.file_list.clear,
            add_file_to_list=self.file_list.add_file,
            reset_select_all=self.main_tab_ui.reset_select_all,
            enable_select_all=self.main_tab_ui.enable_select_all,
            update_status=self.status_bar.update_status,
            disable_controls=self.main_tab_ui.disable_controls,
            enable_controls=self.main_tab_ui.enable_controls,
            disable_checkbox=self.file_list.disable_checkbox,
            set_file_uploaded=self.file_list.set_file_uploaded
        )

        # Return dict for backward compatibility with existing code
        return callbacks.to_dict()
    
    # ===== Logging Methods =====
    def log(self, message: str) -> None:
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
        

    def _update_textbox(self, message):
        """Update textbox in main tab with colored emoji"""
        if hasattr(self, 'textbox') and self.textbox:
            text_widget = self.textbox._textbox

            # Setup colors ครั้งแรก
            if not hasattr(self, '_emoji_colors_setup_main'):
                setup_emoji_colors(text_widget)
                self._emoji_colors_setup_main = True

            # แทรกข้อความพร้อมสี
            insert_colored_message(text_widget, message, get_emoji_color_map())
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
        """Log current database configuration that user set"""
        # แสดงเฉพาะข้อมูลสำคัญที่ผู้ใช้ตั้งค่า
        server = os.getenv('DB_SERVER', 'Not set')
        database = os.getenv('DB_NAME', 'Not set')
        schema = os.getenv('DB_SCHEMA', 'bronze')  # default schema

        logging.info("📊 Database Configuration:")
        logging.info(f"  Server: {server}")
        logging.info(f"  Database: {database}")
        logging.info(f"  Schema: {schema}")
    
    # ===== Initialization Tasks =====
    def run_initialization_tasks(self, progress_callback=None) -> bool:
        """
        รัน initialization tasks ทั้งหมดและรายงานความคืบหน้า
        เรียกจาก LoginWindow ก่อนแสดง MainWindow

        Args:
            progress_callback: Callback function(message, step_index=None, mark_done=False)

        Returns:
            bool: True ถ้าทุกอย่างสำเร็จ, False ถ้ามี error
        """
        try:
            # Step indices ตาม loading dialog ใน LoginWindow:
            # 0: "Connect to database"
            # 1: "Check permissions"
            # 2: "Load app/file settings"
            # 3: "Build Tab View"
            # 4: "Build Main Tab"
            # 5: "Build Log Tab"
            # 6: "Build Settings Tab"
            # 7: "Initialize log file"
            # 8: "Initialize input/output folders"
            # 9: "Verify SQL Server connection"

            # 1. Initialize log file (step 7)
            if progress_callback:
                progress_callback("Initializing log file...", 7)
            self._initialize_log_file_if_needed_sync()
            if progress_callback:
                progress_callback("Log file initialized", 7, mark_done=True)

            # 2. Initialize input folder (step 8)
            if progress_callback:
                progress_callback("Initializing input folder...", 8)
            self._initialize_input_folder_if_needed_sync(self._input_folder_path)

            # 3. Initialize output folder (ยัง step 8 เดิม)
            if progress_callback:
                progress_callback("Initializing output folder...", 8)
            self._initialize_output_folder_if_needed_sync()
            if progress_callback:
                progress_callback("Folders initialized", 8, mark_done=True)

            # 4. Check SQL connection (step 9)
            if progress_callback:
                progress_callback("Verifying SQL Server connection...", 9)
            success, message = self.db_service.check_connection(show_warning=False)

            if success:
                # ไม่ต้อง log เพราะตอน login เชื่อมต่อสำเร็จแล้ว
                if progress_callback:
                    progress_callback("SQL Server connected", 9, mark_done=True)
            else:
                self.log("❌ " + message)
                return False

            self.log("🚀 System ready")
            return True

        except Exception as e:
            self.log(f"❌ Initialization error: {str(e)}")
            return False

    # ===== Synchronous Initialization Helpers =====
    def _initialize_log_file_if_needed_sync(self) -> None:
        """Initialize log file if user has previously set log folder (synchronous)"""
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

    def _initialize_input_folder_if_needed_sync(self, input_folder_path: str) -> None:
        """Initialize input folder if user has previously set it (synchronous)"""
        try:
            if input_folder_path and os.path.exists(input_folder_path):
                self.log(f"📁 Input folder updated: {input_folder_path}")
        except Exception:
            pass

    def _initialize_output_folder_if_needed_sync(self) -> None:
        """Initialize output folder if user has previously set it (synchronous)"""
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

                # Also update file_service's file_manager (they need to use the same output folder)
                if hasattr(self, 'file_service') and hasattr(self.file_service, 'file_manager'):
                    self.file_service.file_manager.set_output_folder(output_folder_path)

                self.log(f"📁 Output folder updated: {output_folder_path}")
        except Exception as e:
            self.log(f"❌ Error updating output folder: {e}")
