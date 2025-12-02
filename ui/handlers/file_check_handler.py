"""File Checking and Scanning Handler"""
import os
import threading
from tkinter import messagebox, filedialog
from typing import Callable, Any


class FileCheckHandler:
    """Handles file scanning and checking operations"""

    def __init__(
        self,
        file_service: Any,
        log_callback: Callable[[str], None]
    ) -> None:
        """
        Initialize File Check Handler

        Args:
            file_service: File service instance
            log_callback: Function to call for logging
        """
        self.file_service = file_service
        self.log: Callable[[str], None] = log_callback
        self.is_checking: bool = False  # Flag to prevent multiple check operations

    def browse_excel_path(self, save_callback):
        """Select folder for file search"""
        folder = filedialog.askdirectory()
        if folder:
            self.file_service.set_search_path(folder)
            save_callback(folder)
            self.log(f"Input folder updated: {folder}")
            messagebox.showinfo("Success", f"Set search path for Excel files to\n{folder}")

    def run_check_thread(self, ui_callbacks):
        """Start file checking in separate thread"""
        # ป้องกันการกดซ้ำขณะกำลัง check อยู่
        if self.is_checking:
            self.log("Warning: File scan is already in progress, please wait...")
            return

        # ตั้งค่า flag ทันที
        self.is_checking = True

        # ปิดปุ่มทันทีเพื่อป้องกันการกดซ้ำ (ทำใน main thread ก่อน start thread)
        try:
            ui_callbacks['disable_controls']()
        except Exception:
            pass

        thread = threading.Thread(target=self._check_files, args=(ui_callbacks,))
        thread.start()

    def _check_files(self, ui_callbacks):
        """Check files in specified path"""
        try:
            # รีเซ็ต UI
            ui_callbacks['reset_progress']()
            ui_callbacks['set_progress_status']("Starting file scan", "Scanning folders...")

            # โหลดการตั้งค่าใหม่
            self.file_service.load_settings()
            ui_callbacks['clear_file_list']()
            ui_callbacks['reset_select_all']()

            # ค้นหาไฟล์ Excel/CSV
            ui_callbacks['update_progress'](0.2, "Searching for files", "Scanning .xlsx and .csv files...")
            data_files = self.file_service.find_data_files()

            if not data_files:
                ui_callbacks['update_progress'](1.0, "Scan completed", "No .xlsx or .csv files found")
                ui_callbacks['update_status']("No .xlsx or .csv files found in the specified folder", True)
                self.log("Warning: No .xlsx or .csv files found in the specified folder")
                self.log("============  File scan completed ============")
                return

            found_files_count = 0
            total_files = len(data_files)

            for i, file in enumerate(data_files):
                # คำนวณ progress ที่ถูกต้อง (0.2 - 0.8)
                progress = 0.2 + (0.6 * (i / total_files))  # 20% - 80%
                ui_callbacks['update_progress'](progress, f"Checking file: {os.path.basename(file)}", f"File {i+1} of {total_files}")

                logic_type = self.file_service.detect_file_type(file)
                if logic_type:
                    found_files_count += 1
                    self.log(f"Found matching file: {os.path.basename(file)} [{logic_type}]")
                    ui_callbacks['add_file_to_list'](file, logic_type)

            if found_files_count > 0:
                ui_callbacks['update_progress'](1.0, "Scan completed", f"Found {found_files_count} matching files")
                ui_callbacks['update_status'](f"Found {found_files_count} matching files", False)
                ui_callbacks['enable_select_all']()
            else:
                ui_callbacks['update_progress'](1.0, "Scan completed", "No matching files found")
                ui_callbacks['update_status']("No matching files found", True)
                ui_callbacks['reset_select_all']()

            self.log("============  File scan completed ============")

        except Exception as e:
            self.log(f"Error: An error occurred while scanning files: {e}")
        finally:
            # เปิดปุ่มกลับมาเมื่อเสร็จสิ้น
            ui_callbacks['enable_controls']()
            # ปล่อย flag
            self.is_checking = False
