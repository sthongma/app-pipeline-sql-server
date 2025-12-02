"""File Operations Handler - Main Coordinator
This module acts as a Facade pattern to coordinate all file-related operations.
"""
from typing import Callable, Any
from ui.handlers.file_check_handler import FileCheckHandler
from ui.handlers.file_upload_handler import FileUploadHandler
from ui.handlers.file_process_handler import FileProcessHandler
from ui.handlers.file_report_handler import FileReportHandler


class FileHandler:
    """
    Main coordinator for all file operations.
    Delegates responsibilities to specialized handlers.
    """

    def __init__(
        self,
        file_service: Any,
        db_service: Any,
        file_mgmt_service: Any,
        log_callback: Callable[[str], None]
    ) -> None:
        """
        Initialize File Handler with all sub-handlers

        Args:
            file_service: File service instance
            db_service: Database service instance
            file_mgmt_service: File management service instance
            log_callback: Function to call for logging
        """
        self.file_service = file_service
        self.db_service = db_service
        self.file_mgmt_service = file_mgmt_service
        self.log: Callable[[str], None] = log_callback

        # Initialize report handler first
        self.report_handler = FileReportHandler(log_callback)

        # Initialize specialized handlers with report callback
        self.check_handler = FileCheckHandler(file_service, log_callback)
        self.upload_handler = FileUploadHandler(
            file_service, db_service, file_mgmt_service, log_callback,
            report_callback=self.report_handler.display_upload_summary
        )
        self.process_handler = FileProcessHandler(file_service, db_service, file_mgmt_service, log_callback)

        # Expose flags for backward compatibility
        self.is_checking = False
        self.is_uploading = False

    # === Properties for backward compatibility ===
    @property
    def data_processor(self):
        """Access to data processor service (backward compatibility)"""
        if hasattr(self.file_service, 'data_processor'):
            return self.file_service.data_processor
        return None

    @property
    def file_reader(self):
        """Access to file reader service (backward compatibility)"""
        if hasattr(self.file_service, 'file_reader'):
            return self.file_service.file_reader
        return None

    # === File Checking Operations ===
    def browse_excel_path(self, save_callback):
        """Select folder for file search"""
        return self.check_handler.browse_excel_path(save_callback)

    def run_check_thread(self, ui_callbacks):
        """Start file checking in separate thread"""
        return self.check_handler.run_check_thread(ui_callbacks)

    def _check_files(self, ui_callbacks):
        """Check files in specified path (backward compatibility)"""
        return self.check_handler._check_files(ui_callbacks)

    # === File Upload Operations ===
    def confirm_upload(self, get_selected_files_callback, ui_callbacks):
        """ยืนยันการอัปโหลดไฟล์ที่เลือก"""
        return self.upload_handler.confirm_upload(get_selected_files_callback, ui_callbacks)

    def _upload_selected_files(self, selected_files, ui_callbacks):
        """Upload selected files (backward compatibility)"""
        upload_stats, total_files = self.upload_handler._upload_selected_files(selected_files, ui_callbacks)
        # Display report after upload
        self.report_handler.display_upload_summary(upload_stats, total_files)
        return upload_stats, total_files

    # === Auto Processing Operations ===
    def start_auto_process(self, load_input_folder_callback, column_settings):
        """เริ่มการประมวลผลอัตโนมัติ"""
        return self.process_handler.start_auto_process(load_input_folder_callback, column_settings)

    def run_auto_process(self, folder_path, ui_callbacks):
        """รันการประมวลผลอัตโนมัติใน thread แยก"""
        try:
            ui_callbacks['disable_controls']()
            ui_callbacks['reset_progress']()
            ui_callbacks['set_progress_status']("Starting auto processing", "Preparing system...")

            self.log("Starting auto processing")
            self.log(f"Source folder: {folder_path}")
            self.log("========= Processing files ==========")

            # Run processing
            process_stats, total_files = self.process_handler._auto_process_main_files(folder_path, ui_callbacks)

            # Display report
            if process_stats:
                self.report_handler.display_auto_process_summary(process_stats, total_files)

            self.log("==== Auto processing completed ======")
            ui_callbacks['update_progress'](1.0, "Auto processing completed", "All steps completed successfully")

            from tkinter import messagebox
            messagebox.showinfo("Success", "Auto processing completed successfully")

            return process_stats, total_files

        except Exception as e:
            self.log(f"Error: An error occurred during auto processing: {e}")
            from tkinter import messagebox
            messagebox.showerror("Error", f"An error occurred: {e}")
            return None, 0
        finally:
            ui_callbacks['enable_controls']()

    # === Reporting Operations ===
    def _display_upload_summary(self, upload_stats, total_files):
        """แสดงรายงานสรุปการอัปโหลด (backward compatibility wrapper)"""
        return self.report_handler.display_upload_summary(upload_stats, total_files)

    def _display_auto_process_summary(self, process_stats, total_files):
        """แสดงรายงานสรุปการประมวลผลอัตโนมัติ (backward compatibility wrapper)"""
        return self.report_handler.display_auto_process_summary(process_stats, total_files)

    def _display_processing_summary(self, stats, total_files, operation_type="Upload"):
        """แสดงรายงานสรุปการประมวลผล (backward compatibility wrapper)"""
        return self.report_handler.display_processing_summary(stats, total_files, operation_type)
