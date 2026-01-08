"""File Auto-Processing Handler"""
import os
import time
from tkinter import messagebox
from typing import Callable, Dict, Any


class FileProcessHandler:
    """Handles automatic file processing operations"""

    def __init__(
        self,
        file_service: Any,
        db_service: Any,
        file_mgmt_service: Any,
        log_callback: Callable[[str], None]
    ) -> None:
        """
        Initialize File Process Handler

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

    def start_auto_process(self, load_input_folder_callback, column_settings):
        """เริ่มการประมวลผลอัตโนมัติ (ประมวลผลไฟล์)"""
        # ตรวจสอบว่ามีโฟลเดอร์ต้นทางหรือไม่
        input_folder_path = load_input_folder_callback()
        if not input_folder_path or not os.path.isdir(input_folder_path):
            messagebox.showerror(
                "Error",
                f"Invalid source folder: {input_folder_path}\n\nPlease select a source folder first"
            )
            return

        # โหลดการตั้งค่าใหม่ก่อนประมวลผล เพื่อให้แน่ใจว่าใช้การตั้งค่าล่าสุด
        self.file_service.load_settings()

        # ตรวจสอบการเชื่อมต่อฐานข้อมูล
        success, message = self.db_service.check_connection()
        if not success:
            messagebox.showerror(
                "Error",
                f"Cannot connect to database:\n{message}\n\nPlease check database settings first"
            )
            return

        # ตรวจสอบการตั้งค่าประเภทไฟล์
        if not column_settings:
            messagebox.showerror(
                "Error",
                "No file type configuration found\n\nPlease go to Settings tab and add file types first"
            )
            return

        # ยืนยันการทำงาน
        result = messagebox.askyesno(
            "Confirm Auto Processing",
            f"Will perform auto processing in folder:\n{input_folder_path}\n\n"
            "Processing steps:\n"
            "1. Find all data files\n"
            "2. Process and upload all files\n"
            "Do you want to proceed?"
        )

        if not result:
            return

        return input_folder_path  # Return path for further processing

    def run_auto_process(self, folder_path, ui_callbacks):
        """รันการประมวลผลอัตโนมัติใน thread แยก"""
        try:
            # ปิดปุ่มต่างๆ ระหว่างการทำงาน
            ui_callbacks['disable_controls']()

            # รีเซ็ต progress bar และแสดงสถานะเริ่มต้น
            ui_callbacks['reset_progress']()
            ui_callbacks['set_progress_status']("Starting auto processing", "Preparing system...")

            self.log("Starting auto processing")
            self.log(f"Source folder: {folder_path}")

            # === ประมวลผลไฟล์หลัก ===
            self.log("========= Processing files ==========")
            process_stats, total_files = self._auto_process_main_files(folder_path, ui_callbacks)

            self.log("==== Auto processing completed ======")
            ui_callbacks['update_progress'](1.0, "Auto processing completed", "All steps completed successfully")
            messagebox.showinfo("Success", "Auto processing completed successfully")

            return process_stats, total_files

        except Exception as e:
            self.log(f"Error: An error occurred during auto processing: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")
            return None, 0
        finally:
            # เปิดปุ่มกลับมา
            ui_callbacks['enable_controls']()

    def _init_upload_stats(self, start_time: float) -> Dict[str, Any]:
        """สร้าง initial upload statistics structure"""
        return {
            'total_start_time': start_time,
            'by_type': {},
            'errors': [],
            'successful_files': 0,
            'failed_files': 0,
            'processed_file_list': []
        }

    def _init_type_stats(self, files_count: int, start_time: float) -> Dict[str, Any]:
        """สร้าง statistics structure สำหรับแต่ละประเภทไฟล์"""
        return {
            'start_time': start_time,
            'files_count': files_count,
            'successful_files': 0,
            'failed_files': 0,
            'errors': [],
            'individual_processing_time': 0,
            'successful_file_list': [],
            'failed_file_list': []
        }

    def _record_file_error(self, process_stats, logic_type, file_path, error_msg, file_start_time):
        """บันทึก error และเวลาที่ใช้สำหรับไฟล์ที่ล้มเหลว"""
        basename = os.path.basename(file_path)

        process_stats['by_type'][logic_type]['failed_files'] += 1
        process_stats['by_type'][logic_type]['failed_file_list'].append(basename)
        process_stats['by_type'][logic_type]['errors'].append(f"{basename}: {error_msg}")
        process_stats['failed_files'] += 1

        # คำนวณและบันทึกเวลาที่ใช้
        file_processing_time = time.time() - file_start_time
        process_stats['by_type'][logic_type]['individual_processing_time'] += file_processing_time

        self.log(f"Error: {error_msg}")

    def _record_file_success(self, process_stats, logic_type, file_path, file_start_time):
        """บันทึกความสำเร็จและเวลาที่ใช้สำหรับไฟล์"""
        basename = os.path.basename(file_path)

        process_stats['by_type'][logic_type]['successful_files'] += 1
        process_stats['by_type'][logic_type]['successful_file_list'].append(basename)
        process_stats['successful_files'] += 1

        # คำนวณและบันทึกเวลาที่ใช้
        file_processing_time = time.time() - file_start_time
        process_stats['by_type'][logic_type]['individual_processing_time'] += file_processing_time

    def _process_single_file(self, file_path, logic_type, process_stats, ui_callbacks, file_index, total_files):
        """
        ประมวลผลไฟล์เดียว - อ่าน validate และอัปโหลด

        Returns:
            bool: True if successful, False otherwise
        """
        file_start_time = time.time()
        basename = os.path.basename(file_path)

        # อัปเดตความคืบหน้า
        progress = (file_index - 1) / total_files
        ui_callbacks['update_progress'](progress, f"Processing file: {basename}", f"File {file_index} of {total_files}")

        self.log(f"Processing file: {basename}")

        # ตรวจสอบคอลัมน์ก่อน
        success, result, _ = self.file_service.preview_file_columns(file_path, logic_type)
        if not success:
            self._record_file_error(process_stats, logic_type, file_path, f"Column check failed: {result}", file_start_time)
            return False

        # อ่านไฟล์เต็ม
        success, result = self.file_service.read_excel_file(file_path, logic_type)
        if not success:
            self._record_file_error(process_stats, logic_type, file_path, f"Could not read file: {result}", file_start_time)
            return False

        df = result

        # ตรวจสอบว่าข้อมูลไม่ว่าง
        if df.empty:
            self._record_file_error(process_stats, logic_type, file_path, "File has no data", file_start_time)
            return False

        # ดึง required columns
        required_cols = self.file_service.get_required_dtypes(logic_type)
        if not required_cols:
            self._record_file_error(process_stats, logic_type, file_path, f"No data type configuration found for {logic_type}", file_start_time)
            return False

        # อัปโหลดข้อมูล
        self.log(f"Uploading {len(df)} rows for type {logic_type}")
        success, message = self.db_service.upload_data(df, logic_type, required_cols, schema_name=os.getenv('DB_SCHEMA', 'bronze'), log_func=self.log, clear_existing=True)

        if success:
            self.log(f"Upload successful: {message}")
            self._record_file_success(process_stats, logic_type, file_path, file_start_time)

            # ย้ายไฟล์หลังอัปโหลดสำเร็จ
            self._move_uploaded_file(file_path, logic_type)
            return True
        else:
            # จัดการ upload failure
            self._handle_upload_failure(process_stats, logic_type, file_path, message, file_start_time)
            return False

    def _move_uploaded_file(self, file_path, logic_type):
        """ย้ายไฟล์ที่อัปโหลดสำเร็จแล้ว"""
        try:
            move_success, move_result = self.file_service.move_uploaded_files([file_path], [logic_type])
            if move_success:
                for original_path, new_path in move_result:
                    self.log(f"Moved file to: {new_path}")
            else:
                self.log(f"Error: Could not move file: {move_result}")
        except Exception as move_error:
            self.log(f"Error: An error occurred while moving file: {move_error}")

    def _handle_upload_failure(self, process_stats, logic_type, file_path, message, file_start_time):
        """จัดการกรณี upload ล้มเหลว"""
        basename = os.path.basename(file_path)

        if isinstance(message, dict):
            summary = message.get('summary', 'Upload failed')
            validation_issues = message.get('issues', [])
            validation_warnings = message.get('warnings', [])

            error_msg = f"Upload failed: {summary}"
            process_stats['by_type'][logic_type]['validation_details'] = {
                'issues': validation_issues,
                'warnings': validation_warnings
            }
        else:
            error_msg = f"Upload failed: {message}"

        self._record_file_error(process_stats, logic_type, file_path, error_msg, file_start_time)

    def _detect_file_logic_type(self, file_path):
        """ตรวจหา logic_type ของไฟล์"""
        logic_type = self.file_service.detect_file_type(file_path)
        if logic_type:
            return logic_type

        # ลองเดาจากชื่อไฟล์
        filename = os.path.basename(file_path).lower()
        for key in self.file_service.column_settings.keys():
            if key.lower() in filename:
                return key

        return None

    def _auto_process_main_files(self, folder_path, ui_callbacks):
        """ประมวลผลไฟล์หลักอัตโนมัติ (Refactored)"""
        try:
            process_start_time = time.time()

            # ตั้ง search path และค้นหาไฟล์
            self.file_service.set_search_path(folder_path)
            data_files = self.file_service.find_data_files()

            if not data_files:
                self.log("No data files found in source folder")
                return self._init_upload_stats(process_start_time), 0

            self.log(f"Found {len(data_files)} data files, starting processing...")

            total_files = len(data_files)
            process_stats = self._init_upload_stats(process_start_time)

            # ประมวลผลแต่ละไฟล์
            for file_index, file_path in enumerate(data_files, start=1):
                try:
                    # ตรวจหา logic_type
                    logic_type = self._detect_file_logic_type(file_path)
                    if not logic_type:
                        error_msg = f"Could not identify file type: {os.path.basename(file_path)}"
                        self.log(f"Error: {error_msg}")
                        process_stats['failed_files'] += 1
                        process_stats['errors'].append(f"{os.path.basename(file_path)}: {error_msg}")
                        continue

                    # เตรียม stats สำหรับ type นี้ถ้ายังไม่มี
                    if logic_type not in process_stats['by_type']:
                        process_stats['by_type'][logic_type] = self._init_type_stats(0, time.time())

                    process_stats['by_type'][logic_type]['files_count'] += 1
                    self.log(f"Identified file type: {logic_type}")

                    # ประมวลผลไฟล์โดยใช้ helper method
                    self._process_single_file(file_path, logic_type, process_stats, ui_callbacks, file_index, total_files)

                except Exception as e:
                    error_msg = f"An error occurred while processing {os.path.basename(file_path)}: {e}"
                    self.log(f"Error: {error_msg}")
                    if logic_type and logic_type in process_stats['by_type']:
                        process_stats['by_type'][logic_type]['failed_files'] += 1
                        process_stats['by_type'][logic_type]['errors'].append(f"{os.path.basename(file_path)}: {str(e)}")
                    process_stats['failed_files'] += 1

            # ใช้เวลารวมที่คำนวณแยกสำหรับแต่ละประเภท
            for logic_type in process_stats['by_type']:
                if 'individual_processing_time' in process_stats['by_type'][logic_type]:
                    process_stats['by_type'][logic_type]['processing_time'] = process_stats['by_type'][logic_type]['individual_processing_time']

            # คำนวณเวลารวม
            process_stats['total_time'] = time.time() - process_start_time

            # อัปเดต progress เป็น 100% เมื่อเสร็จสิ้น
            successful_uploads = process_stats['successful_files']
            ui_callbacks['update_progress'](1.0, "Processing completed", f"Successfully processed {successful_uploads} of {total_files} files")

            # ล้าง list ไฟล์หลังจากประมวลผลเสร็จ เหมือนการอัปโหลดปกติ
            ui_callbacks['clear_file_list']()
            ui_callbacks['reset_select_all']()

            return process_stats, total_files

        except Exception as e:
            self.log(f"Error: An error occurred while processing files: {e}")
            return self._init_upload_stats(time.time()), 0
